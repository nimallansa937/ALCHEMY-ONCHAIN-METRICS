#!/usr/bin/env python3
"""
dune_regime_check.py - Batch job for regime detection.

Run via cron/systemd timer every 6 hours:
    0 */6 * * * /path/to/python dune_regime_check.py

Or manually with dry-run:
    python dune_regime_check.py --dry-run
"""
import sys
import os
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dune_analytics.dune_client import DuneClient
from dune_analytics.regime_classifier import (
    classify_market_regime,
    assess_liquidity_health,
    get_risk_multiplier
)
from dune_analytics.alerts import (
    send_regime_change_alert,
    propose_parameter_change,
    send_error_alert
)
from dune_analytics.config import (
    QUERY_IDS,
    REGIME_RISK_MULTIPLIERS,
    SAFE_DEFAULTS,
    POSTGRES_URL
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get PostgreSQL database connection."""
    try:
        import psycopg2
        return psycopg2.connect(POSTGRES_URL)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


def get_previous_regime(db) -> Optional[str]:
    """Get the most recent regime from database."""
    if db is None:
        return None
    
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT regime FROM dune_regime_history
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Failed to get previous regime: {e}")
        return None


def store_regime_data(
    db, 
    regime: str, 
    metrics: Dict[str, Any]
) -> bool:
    """Log regime classification and raw data to database."""
    if db is None:
        logger.warning("No database connection, skipping store")
        return False
    
    try:
        import json
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO dune_regime_history 
                (timestamp, regime, oi_growth, funding_avg, liquidity_ratio, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                datetime.utcnow(),
                regime,
                metrics.get('oi_growth_pct_7d', 0),
                metrics.get('avg_funding', 0),
                metrics.get('liquidity_ratio', 1.0),
                json.dumps(metrics)
            ))
            db.commit()
        logger.info(f"Stored regime data: {regime}")
        return True
    except Exception as e:
        logger.error(f"Failed to store regime data: {e}")
        db.rollback()
        return False


def update_strategy_params(
    db,
    regime: str,
    liquidity_health: str,
    approved_by: str = 'AUTO'
) -> bool:
    """Update the strategy parameters table."""
    if db is None:
        return False
    
    risk_mult = get_risk_multiplier(regime)
    
    # Calculate new position sizes based on regime
    base_position = 0.5  # Base max position in BTC
    max_position = base_position * risk_mult
    
    # Leverage limits based on regime
    leverage_limits = {
        'STABLE': 2.5,
        'RECOVERY': 3.0,
        'TRANSITIONAL': 2.0,
        'FRAGILE': 1.5,
        'STRESS': 1.0
    }
    leverage_limit = leverage_limits.get(regime, 2.0)
    
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO himari_strategy_params 
                (updated_at, regime, max_position_size_btc, leverage_limit, 
                 risk_budget_multiplier, liquidity_health, approved_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                datetime.utcnow(),
                regime,
                max_position,
                leverage_limit,
                risk_mult,
                liquidity_health,
                approved_by
            ))
            db.commit()
        logger.info(f"Updated strategy params: regime={regime}, max_pos={max_position:.2f}")
        return True
    except Exception as e:
        logger.error(f"Failed to update strategy params: {e}")
        db.rollback()
        return False


def main(dry_run: bool = False):
    """Execute regime detection queries and update strategy parameters."""
    logger.info("=" * 60)
    logger.info("HIMARI Dune Regime Check Starting")
    logger.info("=" * 60)
    
    try:
        # Initialize clients
        dune = DuneClient()
        db = None if dry_run else get_db_connection()
        
        # Get previous regime for comparison
        previous_regime = get_previous_regime(db) if db else None
        
        # Execute regime detection query
        logger.info("Fetching regime metrics from Dune...")
        
        # For now, use mock data if query hasn't been created
        # In production, replace with actual query execution
        regime_data = dune.get_latest_results(QUERY_IDS['regime_detection'])
        
        if regime_data and len(regime_data) > 0:
            metrics = regime_data[0]
        else:
            # Use mock data for testing
            logger.warning("No Dune data available, using mock metrics for testing")
            metrics = {
                'avg_funding': 0.05,
                'oi_growth_pct_7d': 5.0,
                'total_liquidations_7d': 15_000_000
            }
        
        # Classify regime
        regime = classify_market_regime(metrics)
        logger.info(f"Classified regime: {regime}")
        
        # Fetch liquidity data
        liquidity_data = dune.get_latest_results(QUERY_IDS['liquidity_assessment'])
        if liquidity_data and len(liquidity_data) > 0:
            liquidity_metrics = liquidity_data[0]
        else:
            liquidity_metrics = {'tvl_today': None, 'tvl_30d_avg': None}
        
        liquidity = assess_liquidity_health(liquidity_metrics)
        liquidity_health = liquidity.get('health', 'UNKNOWN')
        
        if dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN - No changes will be made")
            logger.info(f"  Detected Regime: {regime}")
            logger.info(f"  Risk Multiplier: {get_risk_multiplier(regime)}x")
            logger.info(f"  Liquidity Health: {liquidity_health}")
            logger.info(f"  Previous Regime: {previous_regime}")
            logger.info("=" * 60)
            return
        
        # Store results
        metrics['liquidity_ratio'] = liquidity.get('deviation_pct', 0) / 100 + 1
        store_regime_data(db, regime, metrics)
        
        # Update strategy params
        update_strategy_params(db, regime, liquidity_health)
        
        # Send alert if regime changed
        if previous_regime and regime != previous_regime:
            logger.info(f"Regime changed: {previous_regime} -> {regime}")
            send_regime_change_alert(previous_regime, regime, metrics)
        
        logger.info(f"Regime analysis complete: {regime}")
        
        if db:
            db.close()
        
    except Exception as e:
        logger.error(f"Regime check failed: {e}")
        send_error_alert(str(e), 'dune_regime_check')
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HIMARI Dune Regime Detection')
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Run without making database changes or sending alerts'
    )
    args = parser.parse_args()
    
    main(dry_run=args.dry_run)
