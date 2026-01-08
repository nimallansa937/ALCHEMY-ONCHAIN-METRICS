"""
Configuration constants for Dune Analytics Strategic Intelligence Layer.
"""
import os

# Analytics Provider Selection
ANALYTICS_PROVIDER = os.getenv('ANALYTICS_PROVIDER', 'ALLIUM')  # Options: DUNE, ALLIUM

# Dune API Configuration
DUNE_API_KEY = os.getenv('DUNE_API_KEY', 'wAFcJTgh1a6mlJT7dZlz7TeBXkidKa15')
DUNE_BASE_URL = "https://api.dune.com/api/v1"

# Allium API Configuration
ALLIUM_API_KEY = os.getenv('ALLIUM_API_KEY', 'b9WB83VXgnmEMZ3W3mG6MrzpUtZhSljg1e8CCnjx-Ma3mRySf4xAyEOCrTSRX_sE6EApSsZ0dNHJ7VcL13XB1w')
ALLIUM_BASE_URL = "https://api.allium.so/api/v1"
ALLIUM_REALTIME_URL = "https://api.allium.so/api/v1/explorer"

# Alchemy API Configuration (Real-Time On-Chain Monitoring)
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY', 'GNZdKJS_y1iDFX-_zovyh')
ALCHEMY_NETWORK = os.getenv('ALCHEMY_NETWORK', 'eth-mainnet')  # eth-mainnet, arb-mainnet, etc.

# Query IDs (create these in Dune UI first)
QUERY_IDS = {
    'regime_detection': 6489102,      # 7-Day Leverage and Sentiment
    'liquidity_assessment': 4100002,  # DEX TVL Trends (placeholder)
    'leverage_cycle': 4100003,        # Funding Rate Persistence (placeholder)
    'protocol_health': 4100004        # Lending Protocol Utilization (placeholder)
}

# Regime Risk Multipliers - adjust position sizing based on regime
REGIME_RISK_MULTIPLIERS = {
    'STABLE': 1.0,        # Normal operation
    'RECOVERY': 1.2,      # Opportunity to increase risk
    'TRANSITIONAL': 0.8,  # Reduce risk modestly
    'FRAGILE': 0.5,       # Significant risk reduction
    'STRESS': 0.3,        # Defensive posture
    'UNKNOWN': 0.8        # Conservative default
}

# Leverage Cycle Actions
LEVERAGE_CYCLE_ACTIONS = {
    'EARLY_CYCLE': {
        'leverage_limit': 3.0,
        'position_size_mult': 1.2,
        'note': 'Favorable leverage environment, can take larger positions'
    },
    'MID_CYCLE': {
        'leverage_limit': 2.0,
        'position_size_mult': 1.0,
        'note': 'Normal operations'
    },
    'LATE_CYCLE': {
        'leverage_limit': 1.5,
        'position_size_mult': 0.6,
        'note': 'Leverage saturation detected, reduce exposure'
    },
    'TRANSITIONAL': {
        'leverage_limit': 2.0,
        'position_size_mult': 0.9,
        'note': 'Uncertain cycle position, slight caution'
    }
}

# Safe defaults when analytics unavailable
SAFE_DEFAULTS = {
    'regime': 'UNKNOWN',
    'max_position_size_btc': 0.3,   # Conservative
    'leverage_limit': 1.5,           # Low leverage
    'risk_budget_multiplier': 0.7,   # Reduced risk
    'liquidity_health': 'UNKNOWN',
    'protocol_alerts': []
}

# Thresholds for regime classification
REGIME_THRESHOLDS = {
    'fragile': {
        'oi_growth_min': 25,
        'funding_avg_min': 0.10,
        'liquidations_min': 50_000_000
    },
    'stress': {
        'oi_growth_max': -15,
        'liquidations_min': 100_000_000
    },
    'recovery': {
        'oi_growth_min': -15,
        'oi_growth_max': 0,
        'funding_avg_min': 0.03,
        'funding_avg_max': 0.08,
        'liquidations_max': 20_000_000
    },
    'stable': {
        'oi_growth_min': -10,
        'oi_growth_max': 15,
        'funding_avg_min': 0.01,
        'funding_avg_max': 0.06,
        'liquidations_max': 30_000_000
    }
}

# Liquidity health thresholds
LIQUIDITY_THRESHOLDS = {
    'CRITICAL': -30,      # TVL deviation < -30%
    'POOR': -15,          # TVL deviation < -15%
    'BELOW_AVERAGE': -5,  # TVL deviation < -5%
    'EXCELLENT': 20       # TVL deviation > 20%
}

# Parameter change thresholds
AUTO_APPLY_THRESHOLD = 10  # Auto-apply changes < 10%
STALENESS_HOURS = 24       # Alert if data older than 24h

# Database configuration
POSTGRES_URL = os.getenv('POSTGRES_URL', 'postgresql://localhost:5432/himari')

# Slack configuration
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
