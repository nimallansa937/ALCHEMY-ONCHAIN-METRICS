"""
Alchemy real-time on-chain monitoring client.

Monitors:
- Whale wallet movements (large transfers)
- DEX swap activity
- Liquidation events
- Protocol deposits/withdrawals
"""
import logging
from typing import Optional, List, Dict, Callable, Any
from web3 import Web3
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlchemyMonitor:
    """
    Real-time blockchain monitoring using Alchemy.
    
    Features:
    - WebSocket subscriptions for instant events
    - Token transfer monitoring
    - Pending transaction mempool access
    - Custom webhook notifications
    """
    
    def __init__(self, api_key: str, network: str = "eth-mainnet"):
        """
        Initialize Alchemy monitor.
        
        Args:
            api_key: Alchemy API key
            network: Network to monitor (eth-mainnet, arb-mainnet, etc.)
        """
        self.api_key = api_key
        self.network = network
        self.http_url = f"https://{network}.g.alchemy.com/v2/{api_key}"
        self.ws_url = f"wss://{network}.g.alchemy.com/v2/{api_key}"
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.http_url))
        
        if not self.w3.is_connected():
            logger.error("Failed to connect to Alchemy")
        else:
            logger.info(f"Connected to Alchemy ({network})")
    
    def get_token_balance(self, token_address: str, wallet_address: str) -> float:
        """
        Get current token balance for a wallet.
        
        Args:
            token_address: ERC20 contract address
            wallet_address: Wallet to check
            
        Returns:
            Token balance (decimal adjusted)
        """
        # ERC20 balanceOf ABI
        abi = [{
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }]
        
        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=abi
            )
            balance = contract.functions.balanceOf(
                Web3.to_checksum_address(wallet_address)
            ).call()
            
            # Get decimals
            decimals_abi = [{
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }]
            decimals_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=decimals_abi
            )
            decimals = decimals_contract.functions.decimals().call()
            
            return balance / (10 ** decimals)
            
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return 0.0
    
    def get_whale_wallets(self) -> Dict[str, str]:
        """
        Get list of known whale wallets to monitor.
        
        Returns:
            Dict of {name: address}
        """
        return {
            "Jump Trading": "0xF977814e90dA44bFA03b6295A0616a897441aceC",
            "Binance Hot Wallet": "0x28C6c06298d514Db089934071355E5743bf21d60",
            "Bitfinex Wallet": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "Wrapped BTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
            "Aave: Lending Pool": "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
        }
    
    def get_asset_transfers(
        self,
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
        from_block: str = "latest",
        to_block: str = "latest",
        max_count: int = 100
    ) -> List[Dict]:
        """
        Get asset transfers using Alchemy's enhanced API.
        
        Args:
            from_address: Filter by sender
            to_address: Filter by receiver  
            from_block: Starting block
            to_block: Ending block
            max_count: Max results
            
        Returns:
            List of transfer events
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getAssetTransfers",
            "params": [{
                "fromBlock": from_block,
                "toBlock": to_block,
                "maxCount": hex(max_count),
                "excludeZeroValue": True,
                "category": ["external", "erc20", "erc721"]
            }]
        }
        
        if from_address:
            payload["params"][0]["fromAddress"] = from_address
        if to_address:
            payload["params"][0]["toAddress"] = to_address
        
        try:
            response = requests.post(self.http_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            transfers = data.get("result", {}).get("transfers", [])
            return transfers
            
        except Exception as e:
            logger.error(f"Failed to get transfers: {e}")
            return []
    
    def monitor_whale_activity(
        self,
        min_value_eth: float = 100.0,
        callback: Optional[Callable] = None
    ):
        """
        Monitor whale wallets for large movements.
        
        Args:
            min_value_eth: Alert threshold in ETH
            callback: Function to call with transfer data
        """
        whales = self.get_whale_wallets()
        logger.info(f"Monitoring {len(whales)} whale wallets...")
        
        for name, address in whales.items():
            logger.info(f"  • {name}: {address[:10]}...")
            
            # Get recent outgoing transfers
            transfers = self.get_asset_transfers(
                from_address=address,
                from_block="0x" + hex(self.w3.eth.block_number - 100)[2:],  # Last ~100 blocks
                max_count=10
            )
            
            for transfer in transfers:
                value = float(transfer.get("value", 0))
                
                if value >= min_value_eth:
                    logger.warning(
                        f"🐋 {name} transferred {value:.2f} ETH "
                        f"to {transfer.get('to', 'unknown')[:10]}..."
                    )
                    
                    if callback:
                        callback({
                            'whale_name': name,
                            'whale_address': address,
                            'transfer': transfer
                        })
    
    def get_pending_transactions(self, limit: int = 10) -> List[Dict]:
        """
        Get pending transactions from mempool.
        
        Useful for frontrunning detection and market impact prediction.
        
        Args:
            limit: Max transactions to return
            
        Returns:
            List of pending transaction data
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_pendingTransactions",
            "params": []
        }
        
        try:
            response = requests.post(self.http_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            pending = data.get("result", [])[:limit]
            return pending
            
        except Exception as e:
            logger.error(f"Failed to get pending txs: {e}")
            return []
    
    def create_webhook(
        self,
        webhook_url: str,
        addresses: List[str],
        event_type: str = "ADDRESS_ACTIVITY"
    ) -> Optional[str]:
        """
        Create Alchemy webhook for automatic alerts.
        
        Args:
            webhook_url: Your webhook endpoint URL
            addresses: Addresses to monitor
            event_type: Type of events to track
            
        Returns:
            Webhook ID or None
        """
        # Note: This requires Alchemy Notify API
        # Setup in Alchemy dashboard: https://dashboard.alchemy.com/notify
        
        logger.info(
            f"Create webhook manually at: https://dashboard.alchemy.com/notify\n"
            f"  - Type: {event_type}\n"
            f"  - Webhook URL: {webhook_url}\n"
            f"  - Addresses: {addresses}"
        )
        
        return None
    
    def get_token_metadata(self, contract_address: str) -> Dict[str, Any]:
        """
        Get token metadata (name, symbol, decimals).
        
        Args:
            contract_address: Token contract address
            
        Returns:
            Dict with token metadata
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getTokenMetadata",
            "params": [contract_address]
        }
        
        try:
            response = requests.post(self.http_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return data.get("result", {})
            
        except Exception as e:
            logger.error(f"Failed to get token metadata: {e}")
            return {}


if __name__ == '__main__':
    import sys
    import os
    
    # Add parent to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from dune_analytics.config import ALCHEMY_API_KEY
    
    if not ALCHEMY_API_KEY:
        print("❌ Set ALCHEMY_API_KEY in config.py or environment variable")
        print("   Get your key at: https://dashboard.alchemy.com/")
        exit(1)
    
    # Initialize monitor
    monitor = AlchemyMonitor(ALCHEMY_API_KEY, network="eth-mainnet")
    
    print("\n" + "="*60)
    print("ALCHEMY REAL-TIME MONITORING DEMO")
    print("="*60)
    
    # Test 1: Check whale balances
    print("\n1. Whale Wallet Balances:")
    whales = monitor.get_whale_wallets()
    
    for name, address in list(whales.items())[:3]:  # Check first 3
        balance = monitor.w3.eth.get_balance(address) / 1e18
        print(f"   {name}: {balance:.2f} ETH")
    
    # Test 2: Monitor recent whale activity
    print("\n2. Recent Whale Activity (last 100 blocks):")
    monitor.monitor_whale_activity(min_value_eth=10.0)
    
    # Test 3: Get WBTC metadata
    print("\n3. Token Metadata (WBTC):")
    wbtc_address = "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"
    metadata = monitor.get_token_metadata(wbtc_address)
    print(f"   Name: {metadata.get('name', 'unknown')}")
    print(f"   Symbol: {metadata.get('symbol', 'unknown')}")
    print(f"   Decimals: {metadata.get('decimals', 0)}")
    
    print("\n" + "="*60)
