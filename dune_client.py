"""
Simple synchronous Dune API client wrapper.

This is intentionally simple - for batch jobs running every 6+ hours,
we don't need async complexity. Blocking calls are appropriate.
"""
import time
import logging
import requests
from typing import Dict, Any, Optional, List

from .config import DUNE_API_KEY, DUNE_BASE_URL

logger = logging.getLogger(__name__)


class DuneClient:
    """
    Synchronous Dune Analytics API client.
    
    Designed for batch jobs, not real-time operations.
    Uses blocking HTTP calls with retry logic.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Dune client.
        
        Args:
            api_key: Dune API key. Falls back to DUNE_API_KEY env var.
        """
        self.api_key = api_key or DUNE_API_KEY
        self.base_url = DUNE_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'X-Dune-API-Key': self.api_key,
            'Content-Type': 'application/json'
        })
    
    def execute_query(
        self, 
        query_id: int, 
        parameters: Optional[Dict[str, Any]] = None,
        max_wait_seconds: int = 300,
        poll_interval: int = 5
    ) -> Optional[List[Dict]]:
        """
        Execute a Dune query and wait for results.
        
        This is a blocking call - appropriate for batch jobs.
        
        Args:
            query_id: The Dune query ID to execute
            parameters: Query parameters (optional)
            max_wait_seconds: Maximum time to wait for query completion
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
                
                if status == 'QUERY_STATE_COMPLETED':
                    return self._get_results(execution_id)
                elif status in ['QUERY_STATE_FAILED', 'QUERY_STATE_CANCELLED']:
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
        query_id: int, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Start a query execution and return the execution ID."""
        url = f"{self.base_url}/query/{query_id}/execute"
        
        payload = {}
        if parameters:
            payload['query_parameters'] = parameters
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            execution_id = data.get('execution_id')
            logger.info(f"Started query {query_id}, execution_id: {execution_id}")
            return execution_id
        except requests.RequestException as e:
            logger.error(f"Failed to start query {query_id}: {e}")
            return None
    
    def _get_execution_status(self, execution_id: str) -> str:
        """Get the status of a query execution."""
        url = f"{self.base_url}/execution/{execution_id}/status"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get('state', 'UNKNOWN')
        except requests.RequestException as e:
            logger.error(f"Failed to get status for {execution_id}: {e}")
            return 'UNKNOWN'
    
    def _get_results(self, execution_id: str) -> Optional[List[Dict]]:
        """Get the results of a completed query execution."""
        url = f"{self.base_url}/execution/{execution_id}/results"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Extract rows from result
            result = data.get('result', {})
            rows = result.get('rows', [])
            
            logger.info(f"Got {len(rows)} rows from execution {execution_id}")
            return rows
            
        except requests.RequestException as e:
            logger.error(f"Failed to get results for {execution_id}: {e}")
            return None
    
    def get_latest_results(self, query_id: int) -> Optional[List[Dict]]:
        """
        Get the latest cached results for a query without re-executing.
        
        Useful for checking if fresh data is available.
        """
        url = f"{self.base_url}/query/{query_id}/results"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            result = data.get('result', {})
            rows = result.get('rows', [])
            
            return rows
            
        except requests.RequestException as e:
            logger.error(f"Failed to get latest results for {query_id}: {e}")
            return None
