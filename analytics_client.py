"""
Unified analytics client that works with both Dune and Allium.

This provides a common interface so you can switch providers easily.
"""
import logging
from typing import Dict, Any, Optional, List

from .config import ANALYTICS_PROVIDER, DUNE_API_KEY, ALLIUM_API_KEY
from .dune_client import DuneClient
from .allium_client import AlliumClient

logger = logging.getLogger(__name__)


class AnalyticsClient:
    """
    Unified client for blockchain analytics.
    
    Automatically uses either Dune or Allium based on config.
    """
    
    def __init__(self, provider: Optional[str] = None):
        """
        Initialize analytics client.
        
        Args:
            provider: 'DUNE' or 'ALLIUM'. If None, uses ANALYTICS_PROVIDER from config
        """
        self.provider = (provider or ANALYTICS_PROVIDER).upper()
        
        if self.provider == 'DUNE':
            self.client = DuneClient(DUNE_API_KEY)
            logger.info("Using Dune Analytics")
        elif self.provider == 'ALLIUM':
            if not ALLIUM_API_KEY:
                raise ValueError("ALLIUM_API_KEY not configured")
            self.client = AlliumClient(ALLIUM_API_KEY)
            logger.info("Using Allium Analytics")
        else:
            raise ValueError(f"Unknown provider: {self.provider}. Use 'DUNE' or 'ALLIUM'")
    
    def execute_query(
        self,
        query_id: int,
        parameters: Optional[Dict[str, Any]] = None,
        max_wait_seconds: int = 300
    ) -> Optional[List[Dict]]:
        """Execute a saved query and return results."""
        # Convert int to string for Allium
        query_id_str = str(query_id)
        return self.client.execute_query(query_id_str, parameters, max_wait_seconds)
    
    def get_latest_results(self, query_id: int) -> Optional[List[Dict]]:
        """Get latest cached results without re-executing."""
        query_id_str = str(query_id)
        return self.client.get_latest_results(query_id_str)
    
    def run_sql(self, sql: str, **kwargs) -> Optional[List[Dict]]:
        """
        Run ad-hoc SQL query (Allium only).
        
        Useful for backtesting historical periods without creating saved queries.
        """
        if self.provider == 'ALLIUM':
            return self.client.run_adhoc_query(sql, **kwargs)
        else:
            logger.warning("Ad-hoc SQL queries only supported on Allium")
            return None
