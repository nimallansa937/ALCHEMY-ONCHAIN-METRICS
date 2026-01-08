# Allium Integration for HIMARI

Allium is now supported as an alternative to Dune for blockchain analytics.

## Why Allium?

- **Better Free Tier** - More queries before hitting limits
- **Lower Cost** - ~$29/mo vs $39/mo for Dune
- **Same Capabilities** - SQL queries on blockchain data
- **Ad-hoc Queries** - Run SQL directly for backtesting

## Setup

1. **Get Allium API Key:**
   - Sign up at <https://allium.so>
   - Get your API key from dashboard

2. **Set Environment Variable:**

   ```bash
   set ANALYTICS_PROVIDER=ALLIUM
   set ALLIUM_API_KEY=your_api_key_here
   ```

3. **Create Queries in Allium:**
   - Use the same SQL from `sql/query_*.sql` files
   - Note the query IDs
   - Update `config.py` with new IDs

## Usage

The code automatically uses Allium when configured:

```python
from dune_analytics import AnalyticsClient

# Automatically uses Allium if ANALYTICS_PROVIDER=ALLIUM
client = AnalyticsClient()
results = client.get_latest_results(query_id)
```

## Ad-hoc Queries (Allium Only)

Perfect for backtesting without creating saved queries:

```python
client = AnalyticsClient('ALLIUM')

sql = """
SELECT 
    AVG(funding_rate) as avg_funding,
    SUM(liquidation_value) as total_liq
FROM ethereum.perps_funding
WHERE timestamp BETWEEN '2025-01-01' AND '2025-01-30'
"""

results = client.run_sql(sql)
```

## Switching Between Providers

Just change the environment variable:

```bash
# Use Dune
set ANALYTICS_PROVIDER=DUNE

# Use Allium  
set ANALYTICS_PROVIDER=ALLIUM
```

No code changes needed!

## Cost Comparison

| | Free Tier | Paid Tier | Cost/mo |
|---|-----------|-----------|---------|
| **Dune** | 10 credits/day | 200 credits/day | $39 |
| **Allium** | More generous | ~5000 queries/mo | $29 |
