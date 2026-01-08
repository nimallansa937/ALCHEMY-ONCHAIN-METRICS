# HIMARI Dune Analytics Strategic Intelligence Layer

Batch-oriented blockchain analytics for strategic decision-making.
**NOT a real-time signal feed** - operates on 6-24 hour timeframes.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  HIMARI Core Trading System (Unchanged)                        │
│  OHLCV → Signal Layer → Tactical Layer → Execution (10ms path) │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ Reads strategic parameters
                           ▼
              ┌────────────────────────────────┐
              │   himari_strategy_params       │
              │   (PostgreSQL)                 │
              │   Updated 4x daily             │
              └────────────┬───────────────────┘
                           │
                           │ Written by analytics pipeline
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  Dune Strategic Analytics Pipeline (Cron-Scheduled)             │
│  • Market Regime Detection: Every 6 hours                       │
│  • Structural Liquidity: Every 4 hours                          │
│  • Protocol Health: Daily                                       │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**

   ```bash
   export DUNE_API_KEY="your_api_key"
   export POSTGRES_URL="postgresql://user:pass@localhost:5432/himari"
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/..."  # Optional
   ```

3. **Create database schema:**

   ```bash
   psql -d himari -f sql/schema.sql
   ```

4. **Test with dry run:**

   ```bash
   python dune_regime_check.py --dry-run
   ```

5. **Set up cron job (Linux/Mac):**

   ```cron
   0 */6 * * * cd /path/to/dune_analytics && python dune_regime_check.py
   ```

## Modules

| Module | Description |
|--------|-------------|
| `dune_client.py` | Synchronous Dune API wrapper |
| `regime_classifier.py` | Market regime classification |
| `strategy_params.py` | HIMARI integration |
| `alerts.py` | Slack notifications |
| `config.py` | Configuration constants |

## Regime Classifications

| Regime | Risk Multiplier | Description |
|--------|-----------------|-------------|
| STABLE | 1.0x | Normal operation |
| RECOVERY | 1.2x | Opportunity to increase risk |
| TRANSITIONAL | 0.8x | Uncertain, reduce risk |
| FRAGILE | 0.5x | High leverage + low liquidity |
| STRESS | 0.3x | Active deleveraging event |

## API Key

The system uses Dune API key for queries. Recommended tier: **Plus** ($39/mo, 200 credits/day).
