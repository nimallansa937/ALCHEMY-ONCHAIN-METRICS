"""
Test Allium API endpoints to verify structure.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dune_analytics.allium_client import AlliumClient
from dune_analytics.config import ALLIUM_API_KEY
import json

print("="*60)
print("ALLIUM API ENDPOINT TEST")
print("="*60)

client = AlliumClient(ALLIUM_API_KEY)

# Test 1: Check if we can make a basic API call
print("\n1. Testing base API connection...")
try:
    response = client.session.get(f"{client.base_url}/health")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ API connection working")
    else:
        print(f"   ⚠️  Unexpected status: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Try different query endpoints
print("\n2. Testing query endpoints...")

# Try getting account/user info
try:
    response = client.session.get(f"{client.base_url}/user")
    print(f"   /user: {response.status_code}")
    if response.status_code == 200:
        print(f"   Data: {response.json()}")
except Exception as e:
    print(f"   /user error: {e}")

# Try listing queries
try:
    response = client.session.get(f"{client.base_url}/queries")
    print(f"   /queries: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Found {len(data.get('data', []))} queries")
except Exception as e:
    print(f"   /queries error: {e}")

print("\n" + "="*60)
print("BACKTESTING DEMO - Historical Bitcoin Price Query")
print("="*60)

# Test historical data query
historical_query = """
SELECT 
    DATE(block_timestamp) as date,
    AVG(price_usd) as avg_price,
    MIN(price_usd) as low_price,
    MAX(price_usd) as high_price,
    SUM(volume_usd) as total_volume
FROM ethereum.dex_swaps
WHERE token_out_address = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'  -- WETH
  AND block_timestamp >= '2024-01-01'
  AND block_timestamp < '2024-01-08'
GROUP BY DATE(block_timestamp)
ORDER BY date
"""

print("\nQuery: Historical WETH trading data (Jan 1-7, 2024)")
print("Attempting to execute...")

# Try different endpoint variations
endpoints_to_try = [
    "/query/run",
    "/queries/run",
    "/query/execute",
    "/sql/execute",
    "/explorer/query"
]

for endpoint in endpoints_to_try:
    try:
        url = f"{client.base_url}{endpoint}"
        payload = {
            "sql": historical_query,
            "chain": "ethereum"
        }
        
        response = client.session.post(url, json=payload, timeout=10)
        print(f"\n   Trying {endpoint}: {response.status_code}")
        
        if response.status_code in [200, 201, 202]:
            data = response.json()
            print(f"   ✅ Success! Response: {json.dumps(data, indent=2)[:500]}")
            break
        else:
            print(f"   ❌ Failed: {response.text[:200]}")
    
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}")

print("\n" + "="*60)
