"""
Historical data collection for backtesting Dune-derived regime signals.

This script collects historical regime classifications to validate
that regime-based position sizing improves risk-adjusted returns.
"""
import sys
import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dune_analytics.dune_client import DuneClient
from dune_analytics.regime_classifier import classify_market_regime
from dune_analytics.config import QUERY_IDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backfill_regime_data(
    start_date: str,
    end_date: str,
    output_file: str = 'historical_regime_data.json'
) -> List[Dict[str, Any]]:
    """
    Execute regime queries for each day in historical period.
    
    WARNING: This consumes significant credits. For 365 days, assuming
    10 credits per query = 3,650 credits (~$183 on Premium tier).
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        output_file: Path to save results
        
    Returns:
        List of regime classifications with timestamps
    """
    import pandas as pd
    
    dune = DuneClient()
    dates = pd.date_range(start_date, end_date, freq='D')
    results = []
    
    logger.info(f"Collecting data for {len(dates)} days from {start_date} to {end_date}")
    logger.info(f"Estimated credit cost: {len(dates) * 10} credits")
    
    for i, date in enumerate(dates):
        logger.info(f"[{i+1}/{len(dates)}] Fetching regime data for {date.date()}")
        
        # Execute query with historical date parameter
        # Note: This requires your Dune query to accept a date parameter
        data = dune.execute_query(
            query_id=QUERY_IDS['regime_detection'],
            parameters={'as_of_date': date.strftime('%Y-%m-%d')}
        )
        
        if data and len(data) > 0:
            metrics = data[0]
            regime = classify_market_regime(metrics)
            
            result = {
                'date': date.strftime('%Y-%m-%d'),
                'regime': regime,
                **metrics
            }
            results.append(result)
            logger.info(f"  → Regime: {regime}")
        else:
            logger.warning(f"  → No data returned for {date.date()}")
        
        # Rate limiting - don't overwhelm Dune API
        if i < len(dates) - 1:
            time.sleep(12)  # 5 queries per minute max
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Saved {len(results)} regime classifications to {output_file}")
    return results


def quick_backfill(days: int = 30) -> List[Dict[str, Any]]:
    """
    Quick backfill for recent history using cached query results.
    
    This is cheaper - uses get_latest_results() which doesn't consume
    execution credits, but only works if queries have been run recently.
    """
    import pandas as pd
    
    dune = DuneClient()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    results = []
    
    logger.info(f"Quick backfill for last {days} days (using cached results)")
    
    # Since we can't get historical data from cached results,
    # we'll just sample the current regime classification
    # In production, you'd query a database of stored regime history
    
    data = dune.get_latest_results(QUERY_IDS['regime_detection'])
    
    if data and len(data) > 0:
        metrics = data[0]
        regime = classify_market_regime(metrics)
        
        # Simulate historical data by copying current metrics
        # (This is a placeholder - real implementation would query historical DB)
        for i in range(days):
            date = start_date + timedelta(days=i)
            results.append({
                'date': date.strftime('%Y-%m-%d'),
                'regime': regime,
                **metrics
            })
    
    return results


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill historical regime data')
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to backfill (default: 30)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD) for full backfill'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD) for full backfill'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Use quick backfill (cached results only)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='historical_regime_data.json',
        help='Output file path'
    )
    
    args = parser.parse_args()
    
    if args.quick or (not args.start_date and not args.end_date):
        # Quick backfill
        results = quick_backfill(args.days)
    else:
        # Full backfill
        if not args.start_date or not args.end_date:
            logger.error("--start-date and --end-date required for full backfill")
            sys.exit(1)
        
        results = backfill_regime_data(args.start_date, args.end_date, args.output)
    
    logger.info(f"Collected {len(results)} regime data points")
