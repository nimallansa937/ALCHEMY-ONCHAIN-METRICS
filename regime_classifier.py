"""
Strategic regime classification based on Dune Analytics data.

Classifies market into regimes that inform risk budget adjustments:
- STABLE: Normal operation (risk multiplier 1.0)
- RECOVERY: Opportunity for increased risk (1.2x)
- TRANSITIONAL: Uncertain, reduce risk (0.8x)
- FRAGILE: High leverage + low liquidity (0.5x)
- STRESS: Active deleveraging event (0.3x)
"""
from typing import Dict, Any, Optional, List
import logging

from .config import (
    REGIME_RISK_MULTIPLIERS,
    REGIME_THRESHOLDS,
    LIQUIDITY_THRESHOLDS,
    LEVERAGE_CYCLE_ACTIONS
)

logger = logging.getLogger(__name__)


def classify_market_regime(query_results: Dict[str, Any]) -> str:
    """
    Classify market regime based on on-chain metrics.
    
    Thresholds derived from backtesting against 2021-2025 data.
    
    Args:
        query_results: Dict containing:
            - avg_funding: 7-day average funding rate
            - oi_growth_pct_7d: Open interest growth percentage
            - total_liquidations_7d: Total liquidation volume in USD
            
    Returns:
        Regime string: STABLE, RECOVERY, TRANSITIONAL, FRAGILE, or STRESS
    """
    avg_funding = float(query_results.get('avg_funding', 0.05))
    oi_growth = float(query_results.get('oi_growth_pct_7d', 0))
    liquidations = float(query_results.get('total_liquidations_7d', 0))
    
    th = REGIME_THRESHOLDS
    
    # FRAGILE: High leverage building, elevated funding, recent liquidations
    if (oi_growth > th['fragile']['oi_growth_min'] and 
        avg_funding > th['fragile']['funding_avg_min'] and 
        liquidations > th['fragile']['liquidations_min']):
        logger.info(f"Regime: FRAGILE (OI={oi_growth:.1f}%, funding={avg_funding:.4f}, liq=${liquidations:,.0f})")
        return 'FRAGILE'
    
    # STRESS: Active deleveraging, extreme conditions
    if (oi_growth < th['stress']['oi_growth_max'] and 
        liquidations > th['stress']['liquidations_min']):
        logger.info(f"Regime: STRESS (OI={oi_growth:.1f}%, liq=${liquidations:,.0f})")
        return 'STRESS'
    
    # RECOVERY: Deleveraging complete, funding normalizing
    if (th['recovery']['oi_growth_min'] <= oi_growth <= th['recovery']['oi_growth_max'] and
        th['recovery']['funding_avg_min'] <= avg_funding <= th['recovery']['funding_avg_max'] and
        liquidations < th['recovery']['liquidations_max']):
        logger.info(f"Regime: RECOVERY (OI={oi_growth:.1f}%, funding={avg_funding:.4f})")
        return 'RECOVERY'
    
    # STABLE: Low leverage growth, normal funding, minimal liquidations
    if (th['stable']['oi_growth_min'] <= oi_growth <= th['stable']['oi_growth_max'] and
        th['stable']['funding_avg_min'] <= avg_funding <= th['stable']['funding_avg_max'] and
        liquidations < th['stable']['liquidations_max']):
        logger.info(f"Regime: STABLE (OI={oi_growth:.1f}%, funding={avg_funding:.4f})")
        return 'STABLE'
    
    # Default: TRANSITIONAL
    logger.info(f"Regime: TRANSITIONAL (OI={oi_growth:.1f}%, funding={avg_funding:.4f})")
    return 'TRANSITIONAL'


def assess_liquidity_health(query_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine if DEX liquidity is in a deterioration trend.
    
    Args:
        query_results: Dict containing:
            - tvl_today: Current total value locked
            - tvl_30d_avg: 30-day average TVL
            - deviation_from_30d_pct: Current deviation percentage
            
    Returns:
        Dict with health classification and recommended adjustment
    """
    tvl_today = query_results.get('tvl_today')
    tvl_30d_avg = query_results.get('tvl_30d_avg')
    deviation_pct = query_results.get('deviation_from_30d_pct', 0)
    
    if tvl_today is None or tvl_30d_avg is None:
        return {
            'health': 'UNKNOWN',
            'adjustment': 0,
            'tvl_today': None,
            'tvl_30d_avg': None,
            'deviation_pct': None
        }
    
    th = LIQUIDITY_THRESHOLDS
    
    # Classify health
    if deviation_pct < th['CRITICAL']:
        health = 'CRITICAL'
        adjustment = -0.4  # Reduce max position size by 40%
    elif deviation_pct < th['POOR']:
        health = 'POOR'
        adjustment = -0.2
    elif deviation_pct < th['BELOW_AVERAGE']:
        health = 'BELOW_AVERAGE'
        adjustment = -0.1
    elif deviation_pct > th['EXCELLENT']:
        health = 'EXCELLENT'
        adjustment = 0.1  # Can increase risk slightly
    else:
        health = 'NORMAL'
        adjustment = 0.0
    
    logger.info(f"Liquidity health: {health} (deviation={deviation_pct:.1f}%, adj={adjustment:.1%})")
    
    return {
        'health': health,
        'tvl_today': tvl_today,
        'tvl_30d_avg': tvl_30d_avg,
        'deviation_pct': deviation_pct,
        'position_size_adjustment': adjustment
    }


def classify_leverage_cycle(query_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Track the crypto leverage cycle to avoid late-stage blow-off tops.
    
    Args:
        query_results: Dict containing:
            - pct_elevated_funding: Percentage of periods with funding > 0.10
            - max_consecutive_high: Maximum consecutive high funding periods
            
    Returns:
        Dict with cycle phase and recommended actions
    """
    pct_elevated = query_results.get('pct_elevated_funding', 0)
    max_consecutive = query_results.get('max_consecutive_high', 0)
    
    if pct_elevated > 70 and max_consecutive > 20:
        phase = 'LATE_CYCLE'
    elif pct_elevated > 50 and max_consecutive > 10:
        phase = 'MID_CYCLE'
    elif pct_elevated < 30:
        phase = 'EARLY_CYCLE'
    else:
        phase = 'TRANSITIONAL'
    
    actions = LEVERAGE_CYCLE_ACTIONS.get(phase, LEVERAGE_CYCLE_ACTIONS['TRANSITIONAL'])
    
    logger.info(f"Leverage cycle: {phase} (elevated={pct_elevated:.1f}%, consec={max_consecutive})")
    
    return {
        'phase': phase,
        **actions,
        'pct_elevated_funding': pct_elevated,
        'max_consecutive_high': max_consecutive
    }


def check_protocol_health(query_results: List[Dict]) -> List[str]:
    """
    Generate alerts for protocol stress conditions (Aave, Compound).
    
    Args:
        query_results: List of dicts with protocol metrics:
            - protocol: Protocol name
            - asset: Asset symbol
            - utilization_ratio: Current utilization
            - avg_health_factor: Average health factor (Aave only)
            
    Returns:
        List of human-readable alert strings
    """
    alerts = []
    
    for row in query_results:
        protocol = row.get('protocol', 'UNKNOWN')
        asset = row.get('asset', 'UNKNOWN')
        utilization = row.get('utilization_ratio', 0)
        health_factor = row.get('avg_health_factor')
        
        # High utilization indicates potential liquidation cascade risk
        if utilization > 0.90:
            alerts.append(
                f"🔴 CRITICAL: {protocol} {asset} utilization at {utilization:.1%} "
                f"(threshold: 90%). Liquidation cascade risk elevated."
            )
        elif utilization > 0.80:
            alerts.append(
                f"🟡 WARNING: {protocol} {asset} utilization at {utilization:.1%} "
                f"(threshold: 80%). Monitor for deleveraging."
            )
        
        # Low health factors indicate overleveraged positions
        if health_factor and health_factor < 1.3:
            alerts.append(
                f"🔴 CRITICAL: {protocol} {asset} avg health factor {health_factor:.2f} "
                f"(threshold: 1.3). Liquidations likely imminent."
            )
    
    return alerts


def get_risk_multiplier(regime: str) -> float:
    """Get the risk budget multiplier for a given regime."""
    return REGIME_RISK_MULTIPLIERS.get(regime, REGIME_RISK_MULTIPLIERS['UNKNOWN'])
