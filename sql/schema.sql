-- PostgreSQL Schema for HIMARI Dune Analytics Strategic Intelligence Layer
-- Run this against your PostgreSQL database before starting the system
-- Strategy Parameters Table
-- Stores the current strategic parameters derived from Dune analytics
CREATE TABLE IF NOT EXISTS himari_strategy_params (
    id SERIAL PRIMARY KEY,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    regime VARCHAR(50) NOT NULL,
    -- STABLE, FRAGILE, STRESS, etc.
    max_position_size_btc DECIMAL(10, 4),
    -- Maximum position size in BTC
    leverage_limit DECIMAL(3, 1),
    -- Maximum leverage allowed
    risk_budget_multiplier DECIMAL(3, 2),
    -- Risk adjustment factor (0.3 - 1.2)
    liquidity_health VARCHAR(20),
    -- Liquidity status
    protocol_alerts TEXT [],
    -- Array of alert strings
    approved_by VARCHAR(100),
    -- 'AUTO' or operator username
    source_data JSONB -- Raw Dune query results for audit
);
-- Index for fast reads by trading system
CREATE INDEX IF NOT EXISTS idx_strategy_params_latest ON himari_strategy_params(updated_at DESC);
-- Regime History Table
-- Stores all regime classifications for backtesting and analysis
CREATE TABLE IF NOT EXISTS dune_regime_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    regime VARCHAR(50),
    oi_growth DECIMAL(10, 2),
    -- Open interest growth %
    funding_avg DECIMAL(10, 6),
    -- Average funding rate
    liquidity_ratio DECIMAL(5, 2),
    -- TVL ratio to baseline
    raw_data JSONB -- Full query results
);
-- Index for time-series queries
CREATE INDEX IF NOT EXISTS idx_regime_history_time ON dune_regime_history(timestamp DESC);
-- Index for filtering by regime
CREATE INDEX IF NOT EXISTS idx_regime_history_regime ON dune_regime_history(regime);
-- Liquidity Assessment History
CREATE TABLE IF NOT EXISTS dune_liquidity_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tvl_today DECIMAL(20, 2),
    tvl_7d_avg DECIMAL(20, 2),
    tvl_30d_avg DECIMAL(20, 2),
    deviation_pct DECIMAL(10, 2),
    health_classification VARCHAR(20),
    raw_data JSONB
);
CREATE INDEX IF NOT EXISTS idx_liquidity_history_time ON dune_liquidity_history(timestamp DESC);
-- Protocol Health Alerts Log
CREATE TABLE IF NOT EXISTS dune_protocol_alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    protocol VARCHAR(50),
    asset VARCHAR(20),
    alert_type VARCHAR(50),
    -- 'HIGH_UTILIZATION', 'LOW_HEALTH_FACTOR'
    severity VARCHAR(20),
    -- 'WARNING', 'CRITICAL'
    utilization_ratio DECIMAL(5, 4),
    health_factor DECIMAL(5, 2),
    message TEXT
);
CREATE INDEX IF NOT EXISTS idx_protocol_alerts_time ON dune_protocol_alerts(timestamp DESC);
-- View for latest parameters (convenience)
CREATE OR REPLACE VIEW v_current_strategy_params AS
SELECT *
FROM himari_strategy_params
ORDER BY updated_at DESC
LIMIT 1;
-- View for regime transition analysis
CREATE OR REPLACE VIEW v_regime_transitions AS
SELECT timestamp,
    regime,
    LAG(regime) OVER (
        ORDER BY timestamp
    ) as previous_regime,
    CASE
        WHEN regime != LAG(regime) OVER (
            ORDER BY timestamp
        ) THEN true
        ELSE false
    END as is_transition,
    oi_growth,
    funding_avg,
    liquidity_ratio
FROM dune_regime_history
ORDER BY timestamp DESC;
-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO himari_readonly;
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO himari_admin;