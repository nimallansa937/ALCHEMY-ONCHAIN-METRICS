"""
Unit tests for regime classification logic.
"""
import pytest
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regime_classifier import (
    classify_market_regime,
    assess_liquidity_health,
    classify_leverage_cycle,
    check_protocol_health,
    get_risk_multiplier
)


class TestClassifyMarketRegime:
    """Tests for classify_market_regime function."""
    
    def test_fragile_regime(self):
        """High OI growth + elevated funding + high liquidations = FRAGILE."""
        metrics = {
            'oi_growth_pct_7d': 30,  # > 25
            'avg_funding': 0.12,     # > 0.10
            'total_liquidations_7d': 60_000_000  # > 50M
        }
        assert classify_market_regime(metrics) == 'FRAGILE'
    
    def test_stress_regime(self):
        """Negative OI growth + extreme liquidations = STRESS."""
        metrics = {
            'oi_growth_pct_7d': -20,  # < -15
            'avg_funding': 0.08,
            'total_liquidations_7d': 150_000_000  # > 100M
        }
        assert classify_market_regime(metrics) == 'STRESS'
    
    def test_recovery_regime(self):
        """Deleveraging complete, funding normalizing = RECOVERY."""
        metrics = {
            'oi_growth_pct_7d': -5,    # -15 to 0
            'avg_funding': 0.05,       # 0.03 to 0.08
            'total_liquidations_7d': 10_000_000  # < 20M
        }
        assert classify_market_regime(metrics) == 'RECOVERY'
    
    def test_stable_regime(self):
        """Normal conditions = STABLE."""
        metrics = {
            'oi_growth_pct_7d': 5,     # -10 to 15
            'avg_funding': 0.04,       # 0.01 to 0.06
            'total_liquidations_7d': 15_000_000  # < 30M
        }
        assert classify_market_regime(metrics) == 'STABLE'
    
    def test_transitional_default(self):
        """When conditions don't match any category = TRANSITIONAL."""
        metrics = {
            'oi_growth_pct_7d': 20,    # Above stable range
            'avg_funding': 0.07,       # At upper edge
            'total_liquidations_7d': 40_000_000  # Above stable, below fragile
        }
        assert classify_market_regime(metrics) == 'TRANSITIONAL'
    
    def test_missing_values_uses_defaults(self):
        """Missing values should use defaults and not crash."""
        metrics = {}
        result = classify_market_regime(metrics)
        assert result in ['STABLE', 'TRANSITIONAL', 'FRAGILE', 'STRESS', 'RECOVERY']


class TestAssessLiquidityHealth:
    """Tests for assess_liquidity_health function."""
    
    def test_critical_liquidity(self):
        """Deviation < -30% = CRITICAL."""
        metrics = {
            'tvl_today': 700_000_000,
            'tvl_30d_avg': 1_000_000_000,
            'deviation_from_30d_pct': -35
        }
        result = assess_liquidity_health(metrics)
        assert result['health'] == 'CRITICAL'
        assert result['position_size_adjustment'] == -0.4
    
    def test_poor_liquidity(self):
        """Deviation < -15% = POOR."""
        metrics = {
            'tvl_today': 800_000_000,
            'tvl_30d_avg': 1_000_000_000,
            'deviation_from_30d_pct': -20
        }
        result = assess_liquidity_health(metrics)
        assert result['health'] == 'POOR'
        assert result['position_size_adjustment'] == -0.2
    
    def test_normal_liquidity(self):
        """Deviation between -5% and 20% = NORMAL."""
        metrics = {
            'tvl_today': 980_000_000,
            'tvl_30d_avg': 1_000_000_000,
            'deviation_from_30d_pct': -2
        }
        result = assess_liquidity_health(metrics)
        assert result['health'] == 'NORMAL'
        assert result['position_size_adjustment'] == 0.0
    
    def test_excellent_liquidity(self):
        """Deviation > 20% = EXCELLENT."""
        metrics = {
            'tvl_today': 1_300_000_000,
            'tvl_30d_avg': 1_000_000_000,
            'deviation_from_30d_pct': 30
        }
        result = assess_liquidity_health(metrics)
        assert result['health'] == 'EXCELLENT'
        assert result['position_size_adjustment'] == 0.1
    
    def test_unknown_when_missing_data(self):
        """Missing TVL data = UNKNOWN."""
        metrics = {'tvl_today': None, 'tvl_30d_avg': None}
        result = assess_liquidity_health(metrics)
        assert result['health'] == 'UNKNOWN'
        assert result['adjustment'] == 0


class TestClassifyLeverageCycle:
    """Tests for classify_leverage_cycle function."""
    
    def test_late_cycle(self):
        """High elevated funding + long consecutive run = LATE_CYCLE."""
        metrics = {
            'pct_elevated_funding': 75,
            'max_consecutive_high': 25
        }
        result = classify_leverage_cycle(metrics)
        assert result['phase'] == 'LATE_CYCLE'
        assert result['leverage_limit'] == 1.5
        assert result['position_size_mult'] == 0.6
    
    def test_early_cycle(self):
        """Low elevated funding = EARLY_CYCLE."""
        metrics = {
            'pct_elevated_funding': 20,
            'max_consecutive_high': 5
        }
        result = classify_leverage_cycle(metrics)
        assert result['phase'] == 'EARLY_CYCLE'
        assert result['leverage_limit'] == 3.0
        assert result['position_size_mult'] == 1.2


class TestCheckProtocolHealth:
    """Tests for check_protocol_health function."""
    
    def test_high_utilization_critical(self):
        """Utilization > 90% triggers CRITICAL alert."""
        data = [{
            'protocol': 'AAVE',
            'asset': 'WBTC',
            'utilization_ratio': 0.95,
            'avg_health_factor': 1.5
        }]
        alerts = check_protocol_health(data)
        assert len(alerts) == 1
        assert 'CRITICAL' in alerts[0]
        assert '95.0%' in alerts[0]
    
    def test_low_health_factor_critical(self):
        """Health factor < 1.3 triggers CRITICAL alert."""
        data = [{
            'protocol': 'AAVE',
            'asset': 'WETH',
            'utilization_ratio': 0.70,
            'avg_health_factor': 1.1
        }]
        alerts = check_protocol_health(data)
        assert len(alerts) == 1
        assert 'health factor' in alerts[0].lower()
    
    def test_no_alerts_for_healthy_protocol(self):
        """Normal conditions should not generate alerts."""
        data = [{
            'protocol': 'COMPOUND',
            'asset': 'USDC',
            'utilization_ratio': 0.65,
            'avg_health_factor': 2.0
        }]
        alerts = check_protocol_health(data)
        assert len(alerts) == 0


class TestGetRiskMultiplier:
    """Tests for get_risk_multiplier function."""
    
    def test_known_regimes(self):
        """Known regimes return expected multipliers."""
        assert get_risk_multiplier('STABLE') == 1.0
        assert get_risk_multiplier('RECOVERY') == 1.2
        assert get_risk_multiplier('TRANSITIONAL') == 0.8
        assert get_risk_multiplier('FRAGILE') == 0.5
        assert get_risk_multiplier('STRESS') == 0.3
    
    def test_unknown_regime_fallback(self):
        """Unknown regime returns conservative default."""
        assert get_risk_multiplier('UNKNOWN') == 0.8
        assert get_risk_multiplier('INVALID') == 0.8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
