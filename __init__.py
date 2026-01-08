"""
HIMARI Dune Analytics Strategic Intelligence Layer

This module provides batch-oriented blockchain analytics for strategic
decision-making. NOT a real-time signal feed - operates on 6-24 hour timeframes.

Supports both Dune and Allium as analytics providers.

Components:
- AnalyticsClient: Unified client (auto-selects Dune or Allium)
- DuneClient: Dune-specific API wrapper
- AlliumClient: Allium-specific API wrapper
- RegimeClassifier: Market regime classification
- StrategyParameterLoader: Integration with HIMARI trading system
- Alerts: Slack notification system
"""

from .analytics_client import AnalyticsClient
from .dune_client import DuneClient
from .allium_client import AlliumClient
from .regime_classifier import (
    classify_market_regime,
    assess_liquidity_health,
    REGIME_RISK_MULTIPLIERS
)
from .strategy_params import StrategyParameterLoader
from .config import SAFE_DEFAULTS, ANALYTICS_PROVIDER

__version__ = "1.1.0"
__all__ = [
    "AnalyticsClient",
    "DuneClient",
    "AlliumClient",
    "classify_market_regime",
    "assess_liquidity_health",
    "REGIME_RISK_MULTIPLIERS",
    "StrategyParameterLoader",
    "SAFE_DEFAULTS",
    "ANALYTICS_PROVIDER"
]
