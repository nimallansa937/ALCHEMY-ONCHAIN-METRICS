"""
Real-time on-chain event monitor using Allium API.

This provides tactical signals (seconds-to-minutes timeframe)
complementing the strategic signals from batch analytics.
"""
import sys
import os
import logging
import time
from typing import Optional, List, Dict, Callable
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dune_analytics.allium_client import AlliumClient
from dune_analytics.config import ALLIUM_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealtimeMonitor:
    """
    Monitor on-chain events in real-time using Allium.
    
    Examples:
    - Whale wallet movements (> $1M transfers)
    - Large DEX swaps (market impact signals)
    - Liquidation cascades
    - Protocol deposit/withdrawal spikes
    """
    
    def __init__(self, chain: str = "ethereum"):
        """
        Initialize real-time monitor.
        
        Args:
            chain: Blockchain to monitor (ethereum, arbitrum, polygon, etc.)
        """
        self.client = AlliumClient(ALLIUM_API_KEY)
        self.chain = chain
        self.last_block_seen = {}
    
    def monitor_whale_transfers(
        self,
        min_value_usd: float = 1_000_000,
        callback: Optional[Callable] = None,
        interval_seconds: int = 10
    ):
        """
        Continuously monitor for large token transfers.
        
        Args:
            min_value_usd: Alert threshold in USD
            callback: Function to call with transfer data
            interval_seconds: Polling interval
        """
        logger.info(f"Monitoring whale transfers (>${min_value_usd:,.0f} USD)")
        
        while True:
            try:
                transfers = self.client.get_whale_transfers(
                    chain=self.chain,
                    min_value_usd=min_value_usd,
                    limit=10
                )
                
                if transfers:
                    for transfer in transfers:
                        tx_hash = transfer.get('transaction_hash')
                        
                        # Skip if already seen
                        if tx_hash in self.last_block_seen:
                            continue
                        
                        self.last_block_seen[tx_hash] = True
                        
                        # Log the transfer
                        logger.info(
                            f"🐋 Whale Transfer: "
                            f"${transfer.get('value_usd', 0):,.0f} "
                            f"from {transfer.get('from_address', 'unknown')[:10]}..."
                        )
                        
                        # Call callback if provided
                        if callback:
                            callback(transfer)
                
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Stopping whale transfer monitor")
                break
            except Exception as e:
                logger.error(f"Error monitoring transfers: {e}")
                time.sleep(interval_seconds)
    
    def monitor_liquidations(
        self,
        callback: Optional[Callable] = None,
        interval_seconds: int = 30
    ):
        """
        Continuously monitor for liquidation events.
        
        Args:
            callback: Function to call with liquidation data
            interval_seconds: Polling interval
        """
        logger.info("Monitoring liquidations for cascade risk")
        
        while True:
            try:
                liquidations = self.client.get_liquidations(
                    chain=self.chain,
                    hours_ago=1,
                    limit=20
                )
                
                if liquidations:
                    total_value = sum(
                        liq.get('liquidation_value_usd', 0) 
                        for liq in liquidations
                    )
                    
                    if total_value > 10_000_000:  # $10M threshold
                        logger.warning(
                            f"⚠️  High liquidation activity: "
                            f"${total_value:,.0f} in last hour"
                        )
                    
                    if callback:
                        callback(liquidations)
                
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Stopping liquidation monitor")
                break
            except Exception as e:
                logger.error(f"Error monitoring liquidations: {e}")
                time.sleep(interval_seconds)
    
    def monitor_dex_swaps(
        self,
        min_value_usd: float = 500_000,
        callback: Optional[Callable] = None,
        interval_seconds: int = 15
    ):
        """
        Continuously monitor for large DEX swaps.
        
        Args:
            min_value_usd: Alert threshold
            callback: Function to call with swap data
            interval_seconds: Polling interval
        """
        logger.info(f"Monitoring large DEX swaps (>${min_value_usd:,.0f} USD)")
        
        while True:
            try:
                swaps = self.client.get_dex_swaps(
                    chain=self.chain,
                    min_value_usd=min_value_usd,
                    limit=10
                )
                
                if swaps:
                    for swap in swaps:
                        tx_hash = swap.get('transaction_hash')
                        
                        if tx_hash in self.last_block_seen:
                            continue
                        
                        self.last_block_seen[tx_hash] = True
                        
                        logger.info(
                            f"💱 Large Swap: "
                            f"${swap.get('amount_usd', 0):,.0f} "
                            f"on {swap.get('protocol_name', 'unknown')}"
                        )
                        
                        if callback:
                            callback(swap)
                
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Stopping DEX swap monitor")
                break
            except Exception as e:
                logger.error(f"Error monitoring swaps: {e}")
                time.sleep(interval_seconds)
    
    def get_snapshot(self) -> Dict[str, any]:
        """
        Get current snapshot of market activity.
        
        Returns:
            Dict with whale transfers, liquidations, and large swaps from last hour
        """
        return {
            'whale_transfers': self.client.get_whale_transfers(
                chain=self.chain,
                min_value_usd=1_000_000,
                limit=20
            ),
            'liquidations': self.client.get_liquidations(
                chain=self.chain,
                hours_ago=1,
                limit=50
            ),
            'large_swaps': self.client.get_dex_swaps(
                chain=self.chain,
                min_value_usd=500_000,
                limit=20
            )
        }


if __name__ == '__main__':
    # Test real-time monitoring
    monitor = RealtimeMonitor(chain='ethereum')
    
    # Get snapshot
    snapshot = monitor.get_snapshot()
    
    print("\n" + "="*60)
    print("REAL-TIME MARKET SNAPSHOT")
    print("="*60)
    
    print(f"\n🐋 Whale Transfers (last hour):")
    if snapshot['whale_transfers']:
        for t in snapshot['whale_transfers'][:5]:
            print(f"  ${t.get('value_usd', 0):,.0f}")
    else:
        print("  None detected")
    
    print(f"\n⚠️  Liquidations (last hour):")
    if snapshot['liquidations']:
        total = sum(l.get('liquidation_value_usd', 0) for l in snapshot['liquidations'])
        print(f"  Total: ${total:,.0f}")
        print(f"  Count: {len(snapshot['liquidations'])}")
    else:
        print("  None detected")
    
    print(f"\n💱 Large DEX Swaps (last hour):")
    if snapshot['large_swaps']:
        for s in snapshot['large_swaps'][:5]:
            print(f"  ${s.get('amount_usd', 0):,.0f} on {s.get('protocol_name', 'unknown')}")
    else:
        print("  None detected")
    
    print("\n" + "="*60)
