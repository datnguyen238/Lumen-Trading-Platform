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
