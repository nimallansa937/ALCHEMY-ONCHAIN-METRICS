"""
Allium API client wrapper for blockchain analytics.

Allium provides SQL-based blockchain data analytics similar to Dune,
but with better free tier and lower pricing.
"""
import time
import logging
import requests
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlliumClient:
    """
    Synchronous Allium Analytics API client.
    
    Designed for batch jobs and backtesting, not real-time operations.
    API docs: https://docs.allium.so/
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the Allium client.
        
        Args:
            api_key: Allium API key
        """
        self.api_key = api_key
        self.base_url = "https://api.allium.so/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        })
    
    def execute_query(
        self, 
        query_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        max_wait_seconds: int = 300,
        poll_interval: int = 5
    ) -> Optional[List[Dict]]:
        """
        Execute an Allium saved query and wait for results.
        
        This is a blocking call - appropriate for batch jobs.
        
        Args:
            query_id: The Allium query ID
            parameters: Query parameters (optional)
            max_wait_seconds: Maximum time to wait for completion
            poll_interval: Seconds between status checks
            
        Returns:
            List of result rows, or None if query failed
        """
        try:
            # Start query execution
            execution_id = self._start_execution(query_id, parameters)
            if not execution_id:
                return None
            
            # Poll for completion
            start_time = time.time()
            while time.time() - start_time < max_wait_seconds:
                status = self._get_execution_status(execution_id)
                
                if status == 'completed':
                    return self._get_results(execution_id)
                elif status in ['failed', 'cancelled']:
                    logger.error(f"Query {query_id} failed with status: {status}")
                    return None
                
                # Still pending
                logger.debug(f"Query {query_id} status: {status}, waiting...")
                time.sleep(poll_interval)
            
            logger.error(f"Query {query_id} timed out after {max_wait_seconds}s")
            return None
            
        except Exception as e:
            logger.error(f"Error executing query {query_id}: {e}")
            return None
    
    def _start_execution(
        self, 
        query_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Start a query execution and return the execution ID."""
        url = f"{self.base_url}/queries/{query_id}/run"
        
        payload = {}
        if parameters:
            payload['parameters'] = parameters
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            execution_id = data.get('execution_id') or data.get('id')
            logger.info(f"Started query {query_id}, execution_id: {execution_id}")
            return execution_id
        except requests.RequestException as e:
            logger.error(f"Failed to start query {query_id}: {e}")
            return None
    
    def _get_execution_status(self, execution_id: str) -> str:
        """Get the status of a query execution."""
        url = f"{self.base_url}/executions/{execution_id}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get('status', 'unknown').lower()
        except requests.RequestException as e:
            logger.error(f"Failed to get status for {execution_id}: {e}")
            return 'unknown'
    
    def _get_results(self, execution_id: str) -> Optional[List[Dict]]:
        """Get the results of a completed query execution."""
        url = f"{self.base_url}/executions/{execution_id}/results"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Allium returns results in 'data' field
            rows = data.get('data', [])
            
            logger.info(f"Got {len(rows)} rows from execution {execution_id}")
            return rows
            
        except requests.RequestException as e:
            logger.error(f"Failed to get results for {execution_id}: {e}")
            return None
    
    def get_latest_results(self, query_id: str) -> Optional[List[Dict]]:
        """
        Get the latest cached results for a query without re-executing.
        
        Useful for checking if fresh data is available.
        """
        url = f"{self.base_url}/queries/{query_id}/latest"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            rows = data.get('data', [])
            return rows
            
        except requests.RequestException as e:
            logger.error(f"Failed to get latest results for {query_id}: {e}")
            return None
    
    def run_adhoc_query(self, sql: str, chain: str = "ethereum") -> Optional[List[Dict]]:
        """
        Run an ad-hoc SQL query (for backtesting).
        
        Args:
            sql: SQL query string
            chain: Blockchain to query (ethereum, polygon, etc.)
            
        Returns:
            Query results or None
        """
        url = f"{self.base_url}/queries/adhoc"
        
        payload = {
            "sql": sql,
            "chain": chain
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Get execution ID and poll for results
            execution_id = data.get('execution_id')
            if execution_id:
                time.sleep(2)  # Wait a bit before polling
                return self._get_results(execution_id)
            
            return None
        except requests.RequestException as e:
            logger.error(f"Failed to run ad-hoc query: {e}")
            return None
    
    def get_whale_transfers(
        self,
        chain: str = "ethereum",
        token_address: Optional[str] = None,
        min_value_usd: float = 1_000_000,
        limit: int = 50
    ) -> Optional[List[Dict]]:
        """
        Get large token transfers (whale movements) in real-time.
        
        Args:
            chain: Blockchain to monitor
            token_address: Specific token contract (None = all tokens)
            min_value_usd: Minimum transfer value in USD
            limit: Max results
            
        Returns:
            List of large transfers
        """
        sql = f"""
        SELECT 
            block_number,
            transaction_hash,
            from_address,
            to_address,
            token_address,
            value,
            value_usd,
            block_timestamp
        FROM {chain}.token_transfers
        WHERE value_usd >= {min_value_usd}
        ORDER BY block_timestamp DESC
        LIMIT {limit}
        """
        
        if token_address:
            sql = sql.replace(
                f"WHERE value_usd",
                f"WHERE token_address = '{token_address}' AND value_usd"
            )
        
        return self.run_adhoc_query(sql, chain=chain)
    
    def get_dex_swaps(
        self,
        chain: str = "ethereum",
        protocol: Optional[str] = None,
        min_value_usd: float = 100_000,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        Get large DEX swaps in real-time.
        
        Args:
            chain: Blockchain to monitor
            protocol: DEX protocol (uniswap, curve, etc.) or None for all
            min_value_usd: Minimum swap value
            limit: Max results
            
        Returns:
            List of DEX swaps
        """
        sql = f"""
        SELECT 
            block_number,
            transaction_hash,
            protocol_name,
            token_in_address,
            token_out_address,
            amount_in,
            amount_out,
            amount_usd,
            trader_address,
            block_timestamp
        FROM {chain}.dex_swaps
        WHERE amount_usd >= {min_value_usd}
        """
        
        if protocol:
            sql += f" AND LOWER(protocol_name) = '{protocol.lower()}'"
        
        sql += f" ORDER BY block_timestamp DESC LIMIT {limit}"
        
        return self.run_adhoc_query(sql, chain=chain)
    
    def get_liquidations(
        self,
        chain: str = "ethereum",
        protocol: Optional[str] = None,
        hours_ago: int = 1,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        Get recent liquidation events in real-time.
        
        Args:
            chain: Blockchain to monitor
            protocol: Lending protocol (aave, compound, etc.)
            hours_ago: Look back period in hours
            limit: Max results
            
        Returns:
            List of liquidation events
        """
        sql = f"""
        SELECT 
            block_number,
            transaction_hash,
            protocol_name,
            borrower,
            liquidator,
            collateral_asset,
            debt_asset,
            collateral_amount,
            debt_amount,
            liquidation_value_usd,
            block_timestamp
        FROM {chain}.lending_liquidations
        WHERE block_timestamp >= NOW() - INTERVAL '{hours_ago} hours'
        """
        
        if protocol:
            sql += f" AND LOWER(protocol_name) = '{protocol.lower()}'"
        
        sql += f" ORDER BY liquidation_value_usd DESC LIMIT {limit}"
        
        return self.run_adhoc_query(sql, chain=chain)

