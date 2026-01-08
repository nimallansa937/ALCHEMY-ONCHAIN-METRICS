"""
Exchange Reserves Tracker - Monitor crypto flowing in/out of exchanges.

Uses Alchemy API to track exchange wallet balances and net flows.
Generates trading signals based on exchange reserves changes.

Signal Logic:
  - Net OUTFLOW (coins leaving) → BULLISH → signal > 0
  - Net INFLOW (coins entering) → BEARISH → signal < 0
"""
import sys
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alchemy_monitor import AlchemyMonitor
from config import ALCHEMY_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FlowData:
    """Data class for exchange flow metrics"""
    exchange: str
    inflow_eth: float
    outflow_eth: float
    net_flow_eth: float  # Negative = outflow (bullish)
    transfer_count: int


# Known exchange wallet addresses (from https://gist.github.com/f13end)
EXCHANGE_WALLETS = {
    # Binance
    "Binance_1": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
    "Binance_2": "0xd551234ae421e3bcba99a0da6d736074f22192ff",
    "Binance_3": "0x564286362092d8e7936f0549571a803b203aaced",
    "Binance_4": "0x0681d8db095565fe8a346fa0277bffde9c0edbbf",
    "Binance_5": "0xfe9e8709d3215310075d67e3ed32a380ccf451c8",
    "Binance_Hot": "0x28C6c06298d514Db089934071355E5743bf21d60",
    
    # Bitfinex
    "Bitfinex_3": "0x4fdd5eb2fb260149a3903859043e962ab89d8ed4",
    "Bitfinex_4": "0x876eabf441b2ee5b5b0554fd502a8e0600950cfa",
    "Bitfinex_5": "0x742d35cc6634c0532925a3b844bc454e4438f44e",
    
    # Kraken
    "Kraken_1": "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",
    "Kraken_2": "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13",
    "Kraken_3": "0xe853c56864a2ebe4576a807d26fdc4a0ada51919",
    "Kraken_4": "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0",
    
    # Huobi
    "Huobi_6": "0xdc76cd25977e0a5ae17155770273ad58648900d3",
    
    # Bittrex
    "Bittrex_1": "0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98",
    
    # OKEx
    "OKEx_1": "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",
    
    # Gemini
    "Gemini_1": "0xd24400ae8bfebb18ca49be86258a3c749cf46853",
    
    # Gate.io
    "Gate_1": "0x0d0707963952f2fba59dd06f2b425ace40b492fe",
    "Gate_3": "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c",
    
    # Poloniex
    "Poloniex_1": "0x32be343b94f860124dc4fee278fdcbd38c102d88",
    
    # Coinbase
    "Coinbase_1": "0x71660c4005ba85c37ccec55d0c4493e66fe775d3",
    "Coinbase_2": "0x503828976D22510aad0201ac7EC88293211D23Da",
    "Coinbase_3": "0xddfAbCdc4D8FfC6d5beaf154f18B778f892A0740",
}

# WBTC contract for tracking BTC reserves
WBTC_CONTRACT = "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"


class ExchangeReservesTracker:
    """
    Track exchange reserves and generate trading signals.
    
    Uses Alchemy for real-time balance queries and transfer tracking.
    """
    
    def __init__(self, api_key: Optional[str] = None, network: str = "eth-mainnet"):
        """
        Initialize tracker.
        
        Args:
            api_key: Alchemy API key (uses config if None)
            network: Network to monitor
        """
        self.api_key = api_key or ALCHEMY_API_KEY
        self.alchemy = AlchemyMonitor(self.api_key, network)
        self.exchange_wallets = EXCHANGE_WALLETS
        self.cached_reserves = {}
        self.last_update = None
    
    def get_total_reserves(self) -> Dict[str, float]:
        """
        Get current ETH/WBTC reserves on all exchanges.
        
        Returns:
            Dict with total reserves per exchange and overall totals
        """
        reserves = {
            'per_exchange': {},
            'total_eth': 0.0,
            'total_wbtc': 0.0,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("Fetching exchange reserves...")
        
        for name, address in self.exchange_wallets.items():
            exchange = name.split('_')[0]  # Get exchange name without number
            
            try:
                # Get ETH balance
                eth_balance = self.alchemy.w3.eth.get_balance(address) / 1e18
                
                # Get WBTC balance
                wbtc_balance = self.alchemy.get_token_balance(WBTC_CONTRACT, address)
                
                # Initialize exchange if not exists
                if exchange not in reserves['per_exchange']:
                    reserves['per_exchange'][exchange] = {
                        'eth': 0.0,
                        'wbtc': 0.0,
                        'wallets': []
                    }
                
                reserves['per_exchange'][exchange]['eth'] += eth_balance
                reserves['per_exchange'][exchange]['wbtc'] += wbtc_balance
                reserves['per_exchange'][exchange]['wallets'].append({
                    'name': name,
                    'address': address,
                    'eth': eth_balance,
                    'wbtc': wbtc_balance
                })
                
                reserves['total_eth'] += eth_balance
                reserves['total_wbtc'] += wbtc_balance
                
            except Exception as e:
                logger.warning(f"Failed to get balance for {name}: {e}")
        
        self.cached_reserves = reserves
        self.last_update = datetime.utcnow()
        
        logger.info(f"Total reserves: {reserves['total_eth']:.2f} ETH, {reserves['total_wbtc']:.4f} WBTC")
        
        return reserves
    
    def get_net_flow_24h(self, wallet_address: Optional[str] = None) -> Dict[str, FlowData]:
        """
        Calculate ETH flowing in/out of exchanges over last 24 hours.
        
        Args:
            wallet_address: Specific wallet to check, or None for all
            
        Returns:
            Dict of exchange -> FlowData
        """
        flows = {}
        
        wallets_to_check = self.exchange_wallets
        if wallet_address:
            # Find matching wallet
            wallets_to_check = {
                k: v for k, v in self.exchange_wallets.items() 
                if v.lower() == wallet_address.lower()
            }
        
        # Get current block
        current_block = self.alchemy.w3.eth.block_number
        blocks_per_day = 7200  # ~12 second blocks
        from_block = hex(current_block - blocks_per_day)
        
        logger.info(f"Calculating 24h flows from block {current_block - blocks_per_day} to {current_block}")
        
        for name, address in wallets_to_check.items():
            exchange = name.split('_')[0]
            
            try:
                # Get incoming transfers
                incoming = self.alchemy.get_asset_transfers(
                    to_address=address,
                    from_block=from_block,
                    max_count=100
                )
                
                # Get outgoing transfers
                outgoing = self.alchemy.get_asset_transfers(
                    from_address=address,
                    from_block=from_block,
                    max_count=100
                )
                
                # Calculate totals
                inflow = sum(float(t.get('value', 0)) for t in incoming if t.get('asset') == 'ETH')
                outflow = sum(float(t.get('value', 0)) for t in outgoing if t.get('asset') == 'ETH')
                
                if exchange not in flows:
                    flows[exchange] = FlowData(
                        exchange=exchange,
                        inflow_eth=0.0,
                        outflow_eth=0.0,
                        net_flow_eth=0.0,
                        transfer_count=0
                    )
                
                flows[exchange].inflow_eth += inflow
                flows[exchange].outflow_eth += outflow
                flows[exchange].net_flow_eth = flows[exchange].inflow_eth - flows[exchange].outflow_eth
                flows[exchange].transfer_count += len(incoming) + len(outgoing)
                
            except Exception as e:
                logger.warning(f"Failed to get flows for {name}: {e}")
        
        return flows
    
    def get_signal(self) -> Tuple[float, str]:
        """
        Generate trading signal based on exchange flow.
        
        Net outflow (coins leaving exchanges) is typically BULLISH
        Net inflow (coins entering exchanges) is typically BEARISH
        
        Returns:
            Tuple of (signal: -1 to +1, reasoning: str)
        """
        flows = self.get_net_flow_24h()
        
        if not flows:
            return 0.0, "No flow data available"
        
        # Calculate total net flow
        total_inflow = sum(f.inflow_eth for f in flows.values())
        total_outflow = sum(f.outflow_eth for f in flows.values())
        net_flow = total_inflow - total_outflow  # Positive = coins entering exchanges
        
        # Normalize to signal (-1 to +1)
        # Typical daily flow is ~10,000-100,000 ETH
        # > 50,000 ETH net inflow = strong bearish (-1)
        # > 50,000 ETH net outflow = strong bullish (+1)
        
        flow_threshold = 50000  # ETH
        
        if net_flow > 0:
            # Net inflow -> Bearish (negative signal)
            signal = -min(net_flow / flow_threshold, 1.0)
            direction = "BEARISH"
        else:
            # Net outflow -> Bullish (positive signal)
            signal = min(abs(net_flow) / flow_threshold, 1.0)
            direction = "BULLISH"
        
        reasoning = (
            f"24h Net Flow: {net_flow:+,.0f} ETH "
            f"(In: {total_inflow:,.0f}, Out: {total_outflow:,.0f}) -> {direction}"
        )
        
        return signal, reasoning
    
    def get_summary(self) -> Dict:
        """Get complete summary of exchange reserves and flows."""
        reserves = self.get_total_reserves()
        flows = self.get_net_flow_24h()
        signal, reasoning = self.get_signal()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'reserves': {
                'total_eth': reserves['total_eth'],
                'total_wbtc': reserves['total_wbtc'],
                'by_exchange': {
                    ex: {
                        'eth': data['eth'],
                        'wbtc': data['wbtc']
                    }
                    for ex, data in reserves['per_exchange'].items()
                }
            },
            'flows_24h': {
                ex: {
                    'inflow': f.inflow_eth,
                    'outflow': f.outflow_eth,
                    'net': f.net_flow_eth,
                    'transfers': f.transfer_count
                }
                for ex, f in flows.items()
            },
            'signal': {
                'value': signal,
                'direction': 'BULLISH' if signal > 0 else 'BEARISH' if signal < 0 else 'NEUTRAL',
                'reasoning': reasoning
            }
        }


if __name__ == '__main__':
    print("\n" + "="*60)
    print("EXCHANGE RESERVES TRACKER")
    print("="*60)
    
    tracker = ExchangeReservesTracker()
    
    # Get reserves summary
    print("\n📊 Fetching exchange reserves...")
    reserves = tracker.get_total_reserves()
    
    print(f"\n💰 Total Exchange Reserves:")
    print(f"   ETH: {reserves['total_eth']:,.2f}")
    print(f"   WBTC: {reserves['total_wbtc']:.4f}")
    
    print("\n📈 Per Exchange:")
    for exchange, data in reserves['per_exchange'].items():
        print(f"   {exchange}: {data['eth']:,.2f} ETH, {data['wbtc']:.4f} WBTC")
    
    # Get signal
    print("\n🎯 Generating trading signal...")
    signal, reasoning = tracker.get_signal()
    
    print(f"\n📊 Signal: {signal:+.2f}")
    print(f"   {reasoning}")
    
    if signal > 0.3:
        print("   → BULLISH - Consider LONG positions")
    elif signal < -0.3:
        print("   → BEARISH - Consider SHORT positions")
    else:
        print("   → NEUTRAL - No strong directional bias")
    
    print("\n" + "="*60)
