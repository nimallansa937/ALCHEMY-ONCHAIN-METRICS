"""
Strategy Parameter Loader - Integration with HIMARI trading system.

Loads Dune-derived strategic parameters from database and provides them
to the position sizing and risk management modules.
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .config import SAFE_DEFAULTS, STALENESS_HOURS, POSTGRES_URL

logger = logging.getLogger(__name__)


class StrategyParameterLoader:
    """
    Loads strategic parameters from database into HIMARI.
    
    Called at system startup and every 30 minutes to pick up changes.
    Falls back to safe conservative defaults if database unavailable.
    """
    
    def __init__(self, db_connection=None, reload_interval_seconds: int = 1800):
        """
        Initialize the parameter loader.
        
        Args:
            db_connection: psycopg2 connection or None to create one
            reload_interval_seconds: How often to reload (default 30 min)
        """
        self.db = db_connection
        self.reload_interval = reload_interval_seconds
        self.params = SAFE_DEFAULTS.copy()
        self.last_load = 0
        self._connect_if_needed()
        self.load_latest()
    
    def _connect_if_needed(self):
        """Connect to database if not already connected."""
        if self.db is None:
            try:
                import psycopg2
                self.db = psycopg2.connect(POSTGRES_URL)
                logger.info("Connected to PostgreSQL database")
            except Exception as e:
                logger.warning(f"Could not connect to database: {e}")
                self.db = None
    
    def load_latest(self) -> Dict[str, Any]:
        """
        Fetch most recent approved parameters from database.
        
        Returns:
            Dict with strategic parameters
        """
        if self.db is None:
            logger.warning("No database connection, using safe defaults")
            return SAFE_DEFAULTS.copy()
        
        try:
            with self.db.cursor() as cur:
                cur.execute("""
                    SELECT 
                        regime,
                        max_position_size_btc,
                        leverage_limit,
                        risk_budget_multiplier,
                        liquidity_health,
                        protocol_alerts,
                        updated_at
                    FROM himari_strategy_params
                    ORDER BY updated_at DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
            
            if not row:
                logger.info("No parameters in database, using safe defaults")
                return SAFE_DEFAULTS.copy()
            
            self.params = {
                'regime': row[0],
                'max_position_size_btc': float(row[1]) if row[1] else SAFE_DEFAULTS['max_position_size_btc'],
                'leverage_limit': float(row[2]) if row[2] else SAFE_DEFAULTS['leverage_limit'],
                'risk_budget_multiplier': float(row[3]) if row[3] else SAFE_DEFAULTS['risk_budget_multiplier'],
                'liquidity_health': row[4] or 'UNKNOWN',
                'protocol_alerts': row[5] or [],
                'updated_at': row[6]
            }
            
            self.last_load = time.time()
            logger.info(f"Loaded parameters: regime={self.params['regime']}")
            
            return self.params
            
        except Exception as e:
            logger.error(f"Failed to load parameters from database: {e}")
            return SAFE_DEFAULTS.copy()
    
    def maybe_reload(self):
        """Check if parameters should be reloaded, reload if so."""
        if time.time() - self.last_load > self.reload_interval:
            old_params = self.params.copy()
            new_params = self.load_latest()
            
            # Check staleness
            if self._is_stale(new_params):
                logger.warning(f"Parameters are stale (>{STALENESS_HOURS}h), using safe defaults")
                self.params = SAFE_DEFAULTS.copy()
                self.params['_stale'] = True
            
            # Log if regime changed
            if old_params.get('regime') != new_params.get('regime'):
                logger.info(f"Regime changed: {old_params.get('regime')} -> {new_params.get('regime')}")
    
    def _is_stale(self, params: Dict[str, Any]) -> bool:
        """Check if parameters are older than staleness threshold."""
        updated_at = params.get('updated_at')
        if updated_at is None:
            return True
        
        age = datetime.utcnow() - updated_at
        return age > timedelta(hours=STALENESS_HOURS)
    
    def get_max_position_size(self) -> float:
        """Get current max position size for risk management."""
        self.maybe_reload()
        return self.params.get('max_position_size_btc', SAFE_DEFAULTS['max_position_size_btc'])
    
    def get_leverage_limit(self) -> float:
        """Get current leverage limit."""
        self.maybe_reload()
        return self.params.get('leverage_limit', SAFE_DEFAULTS['leverage_limit'])
    
    def get_risk_multiplier(self) -> float:
        """Get current risk budget multiplier."""
        self.maybe_reload()
        return self.params.get('risk_budget_multiplier', SAFE_DEFAULTS['risk_budget_multiplier'])
    
    def get_regime(self) -> str:
        """Get current market regime."""
        self.maybe_reload()
        return self.params.get('regime', 'UNKNOWN')
    
    def get_liquidity_health(self) -> str:
        """Get current liquidity health status."""
        self.maybe_reload()
        return self.params.get('liquidity_health', 'UNKNOWN')
    
    def is_stale(self) -> bool:
        """Check if current parameters are stale."""
        return self.params.get('_stale', False)


class PositionSizer:
    """
    Calculate position sizes incorporating strategic constraints.
    
    Integrates with HIMARI's Layer 3 Position Sizing Engine.
    """
    
    def __init__(self, strategy_params: StrategyParameterLoader):
        self.strategy_params = strategy_params
    
    def calculate_position_size(
        self, 
        signal_strength: float, 
        account_balance: float,
        base_risk_pct: float = 0.02
    ) -> float:
        """
        Calculate position size incorporating strategic constraints.
        
        Args:
            signal_strength: From signal layer, range [-1, 1]
            account_balance: Current account balance in BTC
            base_risk_pct: Base risk per trade (default 2%)
        
        Returns:
            Position size in BTC
        """
        # Base calculation from signal strength
        base_size = abs(signal_strength) * account_balance * base_risk_pct
        
        # Apply strategic limit from Dune-derived regime
        max_size = self.strategy_params.get_max_position_size()
        constrained_size = min(base_size, max_size)
        
        # Apply risk budget multiplier
        risk_mult = self.strategy_params.get_risk_multiplier()
        final_size = constrained_size * risk_mult
        
        logger.debug(
            f"Position sizing: signal={signal_strength:.2f}, "
            f"base={base_size:.4f}, max={max_size:.4f}, "
            f"risk_mult={risk_mult:.2f}, final={final_size:.4f}"
        )
        
        return final_size
