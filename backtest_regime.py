"""
Backtest regime-based position sizing strategy.

Validates whether Dune-derived regime signals improve risk-adjusted returns
compared to a baseline strategy.
"""
import sys
import os
import json
import logging
from typing import Dict, List, Any
import numpy as np

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dune_analytics.config import REGIME_RISK_MULTIPLIERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_regime_history(filepath: str) -> List[Dict[str, Any]]:
    """Load historical regime data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def load_price_history(filepath: str) -> List[Dict[str, Any]]:
    """
    Load historical price data.
    
    Expected format:
    [
        {"date": "2024-01-01", "close": 45000, "returns": 0.02},
        ...
    ]
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def calculate_returns(prices: List[float]) -> np.ndarray:
    """Calculate log returns from price series."""
    prices_arr = np.array(prices)
    returns = np.diff(np.log(prices_arr))
    return returns


def backtest_regime_strategy(
    regime_history: List[Dict[str, Any]],
    price_history: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Test if regime-based position sizing improves Sharpe vs baseline.
    
    Args:
        regime_history: List with [{date, regime, ...}, ...]
        price_history: List with [{date, close, returns}, ...]
        
    Returns:
        Dict with performance metrics
    """
    # Create a mapping of date -> regime
    regime_map = {item['date']: item['regime'] for item in regime_history}
    
    # Merge regime and price data
    baseline_returns = []
    regime_adjusted_returns = []
    
    for price_point in price_history:
        date = price_point['date']
        daily_return = price_point.get('returns', 0)
        
        # Baseline strategy: always full position
        baseline_returns.append(daily_return)
        
        # Regime-adjusted strategy: scale position by regime multiplier
        regime = regime_map.get(date, 'UNKNOWN')
        multiplier = REGIME_RISK_MULTIPLIERS.get(regime, 0.8)
        regime_adjusted_returns.append(daily_return * multiplier)
    
    # Convert to numpy arrays
    baseline_returns = np.array(baseline_returns)
    regime_adjusted_returns = np.array(regime_adjusted_returns)
    
    # Calculate Sharpe ratios (annualized, assuming 365 days)
    baseline_sharpe = (
        baseline_returns.mean() / baseline_returns.std() * np.sqrt(365)
        if baseline_returns.std() > 0 else 0
    )
    
    regime_sharpe = (
        regime_adjusted_returns.mean() / regime_adjusted_returns.std() * np.sqrt(365)
        if regime_adjusted_returns.std() > 0 else 0
    )
    
    # Calculate max drawdown
    baseline_cumulative = np.cumprod(1 + baseline_returns)
    regime_cumulative = np.cumprod(1 + regime_adjusted_returns)
    
    baseline_dd = (
        (baseline_cumulative / np.maximum.accumulate(baseline_cumulative) - 1).min()
    )
    regime_dd = (
        (regime_cumulative / np.maximum.accumulate(regime_cumulative) - 1).min()
    )
    
    # Total returns
    baseline_total = baseline_cumulative[-1] - 1
    regime_total = regime_cumulative[-1] - 1
    
    results = {
        'baseline_sharpe': baseline_sharpe,
        'regime_sharpe': regime_sharpe,
        'sharpe_improvement': regime_sharpe - baseline_sharpe,
        'baseline_max_dd': baseline_dd,
        'regime_max_dd': regime_dd,
        'dd_improvement': regime_dd - baseline_dd,  # Negative is better
        'baseline_total_return': baseline_total,
        'regime_total_return': regime_total,
        'return_improvement': regime_total - baseline_total
    }
    
    return results


def print_backtest_results(results: Dict[str, float]):
    """Print formatted backtest results."""
    print("\n" + "="*60)
    print("BACKTEST RESULTS - Regime-Based Position Sizing")
    print("="*60)
    
    print(f"\n📊 Sharpe Ratio:")
    print(f"   Baseline:     {results['baseline_sharpe']:.3f}")
    print(f"   Regime-Based: {results['regime_sharpe']:.3f}")
    print(f"   Improvement:  {results['sharpe_improvement']:+.3f}")
    
    print(f"\n📉 Maximum Drawdown:")
    print(f"   Baseline:     {results['baseline_max_dd']:.2%}")
    print(f"   Regime-Based: {results['regime_max_dd']:.2%}")
    print(f"   Improvement:  {results['dd_improvement']:+.2%}")
    
    print(f"\n💰 Total Return:")
    print(f"   Baseline:     {results['baseline_total_return']:.2%}")
    print(f"   Regime-Based: {results['regime_total_return']:.2%}")
    print(f"   Improvement:  {results['return_improvement']:+.2%}")
    
    print("\n" + "="*60)
    
    # Verdict
    if results['sharpe_improvement'] > 0.2:
        print("✅ PASS: Regime signals provide meaningful improvement (>0.2)")
        print("   → Deploy to production")
    elif results['sharpe_improvement'] > 0:
        print("⚠️  MARGINAL: Small improvement detected")
        print("   → Consider longer backtest or parameter tuning")
    else:
        print("❌ FAIL: Regime signals do not improve performance")
        print("   → Do not deploy, revisit classification logic")
    
    print("="*60 + "\n")


def generate_mock_price_data(days: int = 365) -> List[Dict[str, Any]]:
    """Generate mock price data for testing."""
    from datetime import datetime, timedelta
    
    np.random.seed(42)
    
    # Simulate daily returns
    returns = np.random.normal(0.001, 0.02, days)  # 0.1% daily mean, 2% std
    
    # Generate price series
    price = 45000  # Starting BTC price
    prices = [price]
    for ret in returns:
        price = price * (1 + ret)
        prices.append(price)
    
    # Create date series
    start_date = datetime.now() - timedelta(days=days)
    
    data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'close': prices[i],
            'returns': returns[i]
        })
    
    return data


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backtest regime strategy')
    parser.add_argument(
        '--regime-file',
        type=str,
        default='historical_regime_data.json',
        help='Path to regime history JSON file'
    )
    parser.add_argument(
        '--price-file',
        type=str,
        help='Path to price history JSON file'
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock price data for testing'
    )
    
    args = parser.parse_args()
    
    # Load regime history
    try:
        regime_history = load_regime_history(args.regime_file)
        logger.info(f"Loaded {len(regime_history)} regime data points")
    except FileNotFoundError:
        logger.error(f"Regime file not found: {args.regime_file}")
        logger.info("Run backfill_history.py first to collect regime data")
        sys.exit(1)
    
    # Load or generate price history
    if args.mock:
        logger.info("Generating mock price data...")
        price_history = generate_mock_price_data(len(regime_history))
    elif args.price_file:
        price_history = load_price_history(args.price_file)
        logger.info(f"Loaded {len(price_history)} price data points")
    else:
        logger.error("Either --price-file or --mock required")
        sys.exit(1)
    
    # Run backtest
    results = backtest_regime_strategy(regime_history, price_history)
    
    # Print results
    print_backtest_results(results)
