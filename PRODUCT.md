# Lumen Trading Platform

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Everyday investors practicing investing with simulated money. They need to understand a portfolio, find an asset, research it, review a trade, and track its result.

## Product Purpose

Make the complete paper-investing workflow understandable and usable. The primary path is portfolio → discover an asset → research → review and place a paper trade → track results.

## Operating Context

Responsive browser application. Next.js 16, React 19, TypeScript, Tailwind, shadcn/ui, and Recharts communicate with a FastAPI / SQLAlchemy backend and Supabase PostgreSQL. The database was restored and verified reachable on 2026-11-19, with accounts, orders, positions, price_bars, symbols, trades, and users present.

## Capabilities and Constraints

- Preserve the existing stack, Lumen name, paper-trading capabilities, and existing data.
- The user authorized rebuilding the entire UI, including navigation, onboarding, and every screen.
- Account currency is immutable: USD portfolios start with $100,000 and VND portfolios with ₫1,000,000,000 in simulated cash. One portfolio can hold US and Vietnamese stocks; buys and sells automatically exchange between the stock’s native currency and the portfolio balance currency; there are no brokerage connections or real-money trades.
- Market orders execute at the latest stored close. Market and limit orders support fractional shares for USD-priced stocks and whole shares for VND-priced stocks, trade review, cash/share reservations, cancellation, and idempotent retries. A backend worker checks pending limits and refreshes relevant quotes every 30 seconds independently of the browser. Fills use new observations after order creation, with quote-age guards and persisted execution details.
- Backend accounting tracks cash, quantities, reservations, buying power, weighted average cost, realized P&L, unrealized P&L, and equity. Server-generated trade reviews expire after two minutes; amount-based buys honor their budget in the portfolio balance currency at confirmation.
- Stock prices and histories use yfinance with caching and database fallbacks; market-data timestamps must remain visible and meaningful. Binance historical ingestion also exists, but the current discovery and asset interface primarily uses the stock/yfinance route.
- Quotes, charts, limit prices, and per-share fills retain their native market currency. Cash, total order cost, position cost basis, and P&L use the portfolio balance currency. Trade reviews expose the conversion rate and estimated cash impact; each fill preserves the applied rate, timestamp, and source for audit and realized returns. Conversion is automatic; a different market never requires a new portfolio. Unavailable or stale FX blocks cross-currency execution. Vietnamese listings use `.VN`; Yahoo coverage is limited. Vietnam-specific lots, sessions, tick bands, taxes, fees, and settlement are not simulated.
- Email/password authentication uses scrypt hashes and expiring, revocable HttpOnly server sessions. Account ownership is enforced server-side and state-changing account actions require a CSRF token.
- Account IDs stay out of the investing flow. Old passwordless accounts remain preserved and cannot be claimed through an email or portfolio number; attaching credentials requires a deliberate operator migration.
- Activity displays real orders and fills. Signed-in watchlists are persisted per user in the database and sync across devices; guest watchlists stay in the browser.
- Portfolio history is not recorded as time-series snapshots; do not invent an equity-performance curve or represent current-position back-calculations as historical portfolio performance.

## Brand Commitments

Lumen. Clear, direct investing language. Paper-trading status is explicit throughout the experience. The user requested a full redesign and then pinned cream and black as the theme colors. Cream and black override the initial plum-and-lilac direction; green and red remain functional gain/loss and status colors only.

## Evidence on Hand

Existing API endpoints, database tables, and frontend components. Backend tests run against SQLite and isolated PostgreSQL, covering accounting, authentication, account isolation, trade previews, dollar budgets, retries, reservations, worker matching, stale quotes, concurrent buys, cancellation races, and database privacy. No verified testimonials, investment returns, or commercial proof claims are supplied. Demonstration data must be explicitly labeled and separate from the connected account.

## Product Principles

1. Lead with what the investor owns, what it is worth, and what they can do next.
2. Show the cash and position impact before submitting a paper trade.
3. Distinguish loading, missing data, stale quotes, empty portfolios, and request failures.
4. Carry asset and account context across discovery, research, trading, and review.
5. Keep the primary screens concise: no marketing filler, automatic tutorials, or repeated instructions; optional explanations belong behind a detail disclosure.

## Open Decisions

The user selected Considered Capital’s workspace composition, then explicitly changed the theme to cream and black. No standing build-path preference was confirmed; app screens use the code-first workflow for this redesign.

The user requested a cleaner, simpler UI after the trading backend was completed: remove repeated copy, the beginner checklist, sidebar marketing, and redundant research prompts; retain trading controls, quote timestamps, balances, errors, and order review.
