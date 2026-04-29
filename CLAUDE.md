# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A-share daily stock screening tool (云端每日选股助手 v0.1). Fetches data from Tushare, computes forward-adjusted (前复权) prices, applies a 3-condition breakout strategy, and outputs candidates via CSV + email. Scheduled on GitHub Actions weekdays at 18:10 Beijing time.

## Commands

```bash
# Full pipeline: backfill missing data, then run screening for latest trading day
python full_test_runner.py

# Run screening for a specific date (daily CI entry point)
python main.py 20260427

# Bootstrap DB with ~400 days of historical data (run once)
python init_data.py

# Quick re-screening from existing DB data without API calls
python -c "
from main import run_job
run_job('20260427')
"
```

## Configuration

Copy `.env.example` to `.env` and set `TUSHARE_TOKEN` + SMTP settings. The GitHub Actions workflow at `.github/workflows/daily_run.yml` reads secrets via `${{ secrets.* }}` for the token, but SMTP credentials are hardcoded in the YAML — these should be migrated to GitHub Secrets. Never commit `.env` to version control.

Optional env vars:
- `SCREEN_STRATEGIES` — comma-separated strategy names to run (default: `breakout_30`)

## Architecture

Linear pipeline orchestrated by `main.py`:

```
TushareClient (src/core/tushare_client.py)
  → wraps tushare pro_api with retry (3 attempts, 60s backoff on rate-limit)
  → methods: get_stock_basic, get_trade_cal, get_daily, get_adj_factor, get_daily_basic

Database (src/utils/db_utils.py)
  → SQLite via stdlib sqlite3. Schema at database/schema.sql (8 tables).
  → save_df uses temp-table INSERT OR REPLACE for upsert (filters df columns to match table schema)
  → execute_query returns pd.DataFrame; execute_non_query returns lastrowid

DataProcessor (src/core/processor.py)
  → calculate_qfq(): merges daily_raw + adj_factor, computes qfq_close/qfq_high = price * (adj / latest_adj)
  → calculate_indicators(): MA200, high60, high30, vol_ma3, vol_ma7 (rolling windows use shift(1) to exclude current day)

Screener (src/core/screener.py)
  → thin coordinator that delegates to strategy objects (strategy pattern)
  → Screener(stock_names, strategy=Breakout30Strategy()) by default

Strategies (src/strategies/*.py)
  → BaseStrategy abstract class with auto-registration via __init_subclass__
  → StrategyRegistry maps name → class; resolved from SCREEN_STRATEGIES env var
  → Each strategy defines name, description, csv_columns (df col → Chinese header), and screen()
  → breakout_30.py: original v0.1 logic (close > MA200 AND close > high30 AND first-time breakout)
  → breakout_60.py: same logic but uses high60 instead of high30

Notifier (src/utils/notifier.py)
  → CSV export with Chinese column headers (行业 mapped names for UI)
  → TXT export: one ts_code per line (同花顺 import format)
  → SMTP_SSL email with attachments
```

## Database tables (8)

`stock_master` (replaced each run), `trade_calendar`, `daily_raw`, `adj_factor`, `daily_basic`, `daily_features`, `screen_results`, `job_runs`. All except `stock_master` use upsert semantics. `screen_results` has `strategy TEXT NOT NULL` column with PK `(trade_date, ts_code, strategy)` — the same stock can be selected by different strategies on the same day. `job_runs` tracks start/end/status/error for each pipeline execution.

## Key details

- Forward-adjusted prices: `qfq_price = raw_price * (adj_factor / latest_adj_factor_per_stock)`
- MA200/60d-high/30d-high rolling windows use `shift(1)` to exclude the current day from the window
- The first-breakout detection is a two-step: flag `is_breakout = qfq_close > high30`, then check `is_breakout & ~prev_is_breakout`
- Stock names are mapped via a dict built from `stock_master` (ts_code → name)
- Strategies are auto-registered via `BaseStrategy.__init_subclass__` — adding a new strategy = 1 new file + 1 import line in `src/strategies/__init__.py`. No existing code changes needed.
- `full_test_runner.py`: fetches trade calendar, identifies missing dates vs DB, backfills them with 0.2s delay, then calls `run_job()` on the latest trading day
- `init_data.py`: full bootstrap with 0.5s delay per day
- Tushare has per-minute rate limits; the client sleeps 60s on rate-limit errors
- SQLAlchemy is in `requirements.txt` but not actually used — all DB operations go through raw sqlite3 + pandas
- CI restores the DB from cache (key `stock-db-*`), runs, then saves cache back, so historical data accumulates across runs
