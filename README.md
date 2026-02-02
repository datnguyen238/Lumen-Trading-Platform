# Lumen Trading Platform

**Lumen Trading Platform** is a full-stack, paper-trading system designed to simulate real-world trading workflows for equities and crypto.  
It combines a **FastAPI backend** for market data ingestion, portfolio accounting, and order execution with a **Next.js frontend** inspired by modern trading platforms (Robinhood, Webull, Binance).

This project is built as a **monorepo** and is intentionally designed to scale toward authentication, real-time data, and advanced analytics.

---

## 🚀 Features

### Backend (FastAPI)
- Market data ingestion
  - Stocks via **Yahoo Finance**
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
- Trading-style UI shell (sidebar + top bar)
- Dashboard with:
  - Account summary
  - Positions
- Asset detail pages:
  - Latest price display
  - Order ticket (market orders)
- Markets view for symbol discovery
- Orders & watchlists scaffolding
- API-driven UI (no mock-only components)

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

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic

### Data Sources
- Yahoo Finance (stocks)
- Binance Public API (crypto)

## 🖥️ Running the Project Locally

### Prerequisites
- Node.js 18+
- Python 3.10+
- npm
- Git

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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

## 🔑 Development Notes
- Authentication is not implemented yet (intentional v1 decision)
- Frontend stores user_id and account_id locally to simulate sessions
- Architecture is auth-ready to minimize future refactors
- Market orders currently fill at the latest available close price
- Designed as a learning + portfolio project, not a live trading system

## 🛣️ Roadmap
- Authentication (JWT / session-based)
- Real-time price updates (WebSockets / SSE)
- Limit orders & order book simulation
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
