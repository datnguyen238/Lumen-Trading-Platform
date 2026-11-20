# Lumen Trading Platform

**Lumen Trading Platform** is a full-stack, paper-trading system designed to simulate real-world trading workflows for equities and crypto.  
It combines a **FastAPI backend** for market data ingestion, portfolio accounting, and order execution with a **Next.js frontend** inspired by modern trading platforms (Robinhood, Webull, Binance).

This **monorepo** includes email/password sessions, protected portfolios, simulated execution, and room for advanced analytics.
The current build uses **yfinance** for equities, **PostgreSQL** (Supabase) for persistence, and a pragmatic live data strategy: optional yfinance WebSocket, polling fallback, and TTL-cached latest price fetches to control provider load.

---

## 🚀 Features

### Backend (FastAPI)
- Market data ingestion
  - Stocks via **Yfinance**
  - Crypto via **Binance public API**
- OHLCV storage for historical and latest prices
- Paper trading engine
  - Market orders (BUY / SELL)
  - Immediate fills at latest close
- Portfolio & accounting
  - Accounts, cash balance, positions
  - Mark-to-market pricing
- Clean REST API design (OpenAPI/Swagger ready)

### Frontend (Next.js + Tailwind + shadcn/ui)
- Cream-and-black responsive investing workspace with desktop sidebar and mobile navigation
- Simple email/password signup and login, persistent private portfolios, and sign out
- Portfolio equity, buying power, holdings, allocation, realized and unrealized returns
- Searchable investment directory with stock/fund filters and quote timestamps
- Asset research with 1W/1M/3M/6M/1Y price histories
- Dollar/share entry, market and limit orders, reserved buying power, review, and fill/pending confirmation
- Account order activity, fill details, status filters, and pending-order cancellation
- Company logos, green/red gains and losses, and database-backed watchlists that sync across devices
- Loading, empty, error, and retry states throughout the main flow

---

## 🧱 Monorepo Structure

```text
Lumen-Trading-Platform/
├── frontend/          # Next.js (App Router) frontend
│   ├── src/
│   ├── package.json
│   └── ...
├── backend/           # FastAPI backend
│   ├── app/
│   ├── requirements.txt
│   └── ...
└── README.md
```
---

## 🔧 Tech Stack

### Frontend
- Next.js (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- psycopg2 (PostgreSQL driver)
- yfinance WebSocket + polling fallback
- In-memory TTL caching for live quote fetches

### Database
- PostgreSQL 16 (local Docker) or Supabase Postgres

### Market Data Sources
- Yfinance (stocks)
- Binance Public API (crypto)

## Hosting on Vercel

See [DEPLOYMENT.md](DEPLOYMENT.md) for the root-project Services configuration, separate trading daemon, Supabase environment variables, quota requirements, schema setup, and verification steps. The deployment targets Node 22 and Python 3.12.

## 🖥️ Running the Project Locally

### Prerequisites
- Node.js 22.x
- Python 3.10+
- npm
- Git

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

### Backend Setup (completed)
**Backend runs at:**  
`http://localhost:8000`  

**Swagger UI (API docs):**  
`http://localhost:8000/docs`

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

**Frontend runs at:**  
`http://localhost:3000`

Create an account with your name, email, and an 8+ character password, or sign in to resume. A single portfolio can hold US and Vietnamese stocks. Choose USD or VND as the balance currency: portfolios start with $100,000 or ₫1,000,000,000 in virtual cash. Stock prices stay in their market currency; buys and sells automatically convert against the portfolio balance. The primary workflow is **Portfolio → Discover → Research → Review paper order → Activity**.

For a production check, run `npm run build` with Node 22.x and `npm start`. Backend tests run with `DATABASE_URL=sqlite+pysqlite:///:memory: python -m pytest -q`; they use an isolated database.

Backend verification:

```bash
cd backend
.venv/bin/python -m pytest -q
# Runs API/accounting tests on isolated SQLite; concurrency tests require PostgreSQL.
.venv/bin/python scripts/verify_paper_trading.py
# Uses the configured database, then rolls back its verification account and trades.
```

For full PostgreSQL validation, start a dedicated local test cluster at `/tmp/lumen-paper-postgres` with user `lumen_test`, then set `TEST_POSTGRES_URL` to its connection URL. The test harness creates and removes a unique schema for each test and refuses non-test database targets. Do not point tests at the restored Supabase database.

The product brief is in `PRODUCT.md` and the visual system is in `DESIGN.md`. Local `.impeccable/` artifacts and review screenshots are ignored by Git.

## 🔑 Development Notes
- Credentials use salted scrypt hashes; sessions are opaque HttpOnly cookies, expire after seven days, and are revoked on logout
- Every account, summary, position, order and trade endpoint enforces ownership; account mutations require the session CSRF token
- Destructive reset endpoints are not exposed by the application router
- Frontend calls `/api/*`; local Next.js proxies to `BACKEND_URL` (legacy `NEXT_PUBLIC_API_BASE_URL` also works). Vercel routes `/api` to the FastAPI service at the same public origin.
- Set backend `FRONTEND_ORIGINS` to the allowed app URLs; set `SESSION_COOKIE_SECURE=true` behind HTTPS in production
- Hosted login limits use short-lived database buckets shared across Vercel API instances; local development uses an in-process limiter
- New credential, session, preview, execution-audit, receipt, and watchlist tables are additive; existing users, portfolios, prices, and trades are preserved
- Legacy passwordless accounts cannot be claimed by entering their email or portfolio number; an operator must deliberately attach credentials after verifying ownership
- Signed-in watchlists are persisted in PostgreSQL per user and sync across devices; guest watchlists stay on the browser
- Market orders fill at the latest stored price, including outside exchange hours; review estimates can differ from the final fill
- Market and limit orders are long-only; USD-priced stocks support up to four share decimals and VND-priced stocks use whole shares and whole-đồng limit prices. Orders accept a client order key for safe retries
- Trade previews and amount-to-share conversions are calculated server-side; reviews expire after two minutes, and confirming the same review is idempotent
- Amount-based buys round shares down so the final fill never exceeds the budget in the portfolio balance currency; Vietnamese stock orders must cover at least one whole share
- Quote currency is stored with each price bar. The portfolio balance currency is fixed at creation, but does not restrict stock markets. USD/VND conversions use validated Yahoo FX observations; missing or stale rates block cross-currency execution instead of using invented rates. FX observations are limited to 72 hours old by default (`FX_QUOTE_MAX_AGE_HOURS`). Native limits and prices stay unchanged
- Reviews show native trade value, the conversion rate, and the estimated balance-currency cost. Each cross-currency fill persists its applied exchange rate, source, timestamp, and converted account amount. Cash, reservations, cost basis, and realized returns use fill-time conversions; open positions use current conversion rates
- Search accepts explicit Vietnamese listings such as `FPT.VN` and `VNM.VN`, with live chart-feed validation when company search omits the listing. `VNM` is a separate US ETF; listing currency/exchange appear in search results. Coverage depends on Yahoo; this is not a complete Vietnam exchange directory
- Each new fill stores its source quote time, price, cash before/after, fee, and simulation model
- Resting limits cannot fill from observations that predate the order; quotes older than seven days or more than five minutes in the future are rejected for execution
- `/accounts/{id}/overview` returns a coherent account view with server-owned available cash and sellable shares
- Local startup can initialize schema/privacy; hosted deployments use an explicit `python -m app.db.bootstrap` step. Vercel requests never perform schema DDL.
- Set `PAPER_WORKER_ENABLED=false` for isolated/offline tests; `PAPER_WORKER_INTERVAL_SECONDS` and `PAPER_WORKER_SYMBOL_LIMIT` bound each cycle
- `GET /health` checks the database connection and reports the matcher’s last successful cycle
- Run `.venv/bin/python scripts/verify_paper_trading.py` from `backend` for a live-database API round trip that rolls back all verification records
- A dedicated Vercel Daemon (or the local embedded worker) checks quotes and pending limits every 30 seconds while running; open limits reserve cash/shares until filled or canceled
- No spread, slippage, market depth, dividends, corporate actions, borrowing, or real brokerage execution is simulated. Vietnam order lots, tick bands, price limits, market sessions, fees/taxes, and T+2 settlement are not simulated; whole-share VND practice is not a full HOSE broker simulator
- Email verification and self-service password recovery are not included in this simple login
- Company logos are bundled for starter symbols from Financial Modeling Prep; additional symbols request its public logo endpoint, falling back to the ticker on failure
- Fresh yfinance intraday observations are normalized to UTC; previously stored timestamps are not rewritten
- Quote timestamps are shown; no synthetic portfolio-equity history is presented as actual performance
- Live prices use cached fetches (TTL) to reduce provider load
- Search can add new symbols to DB dynamically
- Designed as a learning + portfolio project, not a live trading system

## 🛣️ Roadmap
- Email verification and password recovery
- Integrate the existing streaming endpoint across the redesigned workspace
- Order book, spread, liquidity and slippage simulation
- Trade blotter & performance analytics
- Candlestick charting with indicators
- Strategy backtesting integration

## 📄 Disclaimer
This project is for educational and research purposes only.  
It does not connect to real brokerage accounts and does not execute live trades.

## 👤 Author
**Dat Nguyen**  
B.S. Computer Science & Finance  
Arizona State University

**Dong Quan Tran**
