# Alchemy Real-Time Monitoring Setup

Get your free Alchemy API key to monitor on-chain activity in real-time.

## Step 1: Create Alchemy Account

1. Go to: <https://dashboard.alchemy.com/>
2. Sign up (free)
3. Create a new app
4. Select network: **Ethereum Mainnet**

## Step 2: Get API Key

1. Go to your app dashboard
2. Click "View Key"
3. Copy the **API KEY** (not the HTTP/WebSocket URLs)

## Step 3: Configure HIMARI

```bash
set ALCHEMY_API_KEY=your_api_key_here
set ALCHEMY_NETWORK=eth-mainnet
```

Or add to your `.env` file:

```
ALCHEMY_API_KEY=your_api_key_here
ALCHEMY_NETWORK=eth-mainnet
```

## Step 4: Install Dependencies

```bash
pip install web3 requests
```

## Step 5: Test

```bash
python dune_analytics/alchemy_monitor.py
```

---

## What You Can Monitor

### 🐋 Whale Activity

- Track large wallet movements (>100 ETH)
- Monitor known exchange wallets
- Detect unusual transfer patterns

### 💱 DEX Activity  

- Real-time swap events
- Large trades (market impact)
- Mempool frontrunning detection

### ⚠️ Protocol Events

- Liquidations as they happen
- Large deposits/withdrawals
- Flash loan attacks

---

## Usage Example

```python
from dune_analytics.alchemy_monitor import AlchemyMonitor

# Initialize
monitor = AlchemyMonitor(api_key="your_key", network="eth-mainnet")

# Check whale balance
balance = monitor.w3.eth.get_balance("0x wallet_address") / 1e18
print(f"Balance: {balance} ETH")

# Monitor whale activity
def alert_callback(data):
    print(f"Alert: {data['whale_name']} moved funds!")

monitor.monitor_whale_activity(
    min_value_eth=100.0,
    callback=alert_callback
)

# Get token metadata
metadata = monitor.get_token_metadata("0x2260FAC...") # WBTC
print(f"Token: {metadata['name']}")
```

---

## Alchemy Free Tier Limits

- **300M compute units/month** (generous!)
- Enough for:
  - ~10M requests/month
  - Real-time monitoring for HIMARI
  - Webhook notifications
  
---

## Setting Up Webhooks (Optional)

For automated alerts without polling:

1. Go to: <https://dashboard.alchemy.com/notify>
2. Create "Address Activity" webhook
3. Enter addresses to monitor
4. Set webhook URL (your server endpoint)
5. Receive instant notifications

---

## Networks Supported

- `eth-mainnet` - Ethereum
- `arb-mainnet` - Arbitrum
- `opt-mainnet` - Optimism
- `polygon-mainnet` - Polygon
- `base-mainnet` - Base
