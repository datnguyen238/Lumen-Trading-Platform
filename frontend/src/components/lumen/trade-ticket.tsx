"use client";
import { useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowRight, Check, ChevronLeft, ClipboardCheck, Clock3 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { errorMessage, money, quantity, timestamp } from "@/lib/format";
import type { OrderRead, OrderPreview, PriceBarRead } from "@/lib/types";
import { useSession } from "@/components/shell/session-provider";
import { useAccount } from "./data";
import { ErrorNotice } from "./common";

type Review = { server: OrderPreview; request: { account_id: number; side: "BUY" | "SELL"; order_type: "MARKET" | "LIMIT"; quantity: number }; price: number; timestamp: string };
const floorShares = (value: number) => Math.floor((value + 1e-10) * 10000) / 10000;
export function TradeTicket({ symbol, quote, onFilled }: { symbol: string; quote: PriceBarRead | null; onFilled: () => void }) {
  const { accountId } = useSession();
  const account = useAccount();
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT">("MARKET");
  const [unit, setUnit] = useState<"dollars" | "shares">("dollars");
  const [amount, setAmount] = useState("100");
  const [limit, setLimit] = useState("");
  const [review, setReview] = useState<Review | null>(null);
  const [placed, setPlaced] = useState<OrderRead | null>(null);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const selected = account.data;
  const holding = selected?.summary.positions[symbol];
  const cash = Number(selected?.summary.available_cash ?? 0);
  const shares = Number(holding?.available_quantity ?? 0);
  const price = orderType === "LIMIT" ? Number(limit) : Number(quote?.close);
  const validPrice = Number.isFinite(price) && price > 0;
  const input = Number(amount);
  const dollars = unit === "dollars" && side === "BUY" && orderType === "MARKET";
  const count = dollars ? floorShares(input / price) : input;
  const validation = !Number.isFinite(input) || input <= 0 ? "Enter an amount greater than zero."
    : dollars && input < 1 ? "Dollar buys start at $1."
    : !validPrice ? orderType === "LIMIT" ? "Enter a limit price greater than zero." : "Waiting for an available market price."
    : count < 0.0001 ? "Choose an amount that buys at least 0.0001 shares."
    : !dollars && Math.abs(Math.round(count * 10000) - count * 10000) > 1e-6 ? "Use up to four decimal places for shares."
    : dollars && Math.abs(Math.round(input * 100) - input * 100) > 1e-6 ? "Use up to two decimal places for dollars."
    : side === "SELL" && count > shares ? `You have ${quantity(shares)} shares available to sell.`
    : side === "BUY" && count * price > cash + 1e-7 ? "This order exceeds your available paper cash." : null;
  const activeReview = review?.request.account_id === accountId ? review : null;
  const open = placed?.status === "PENDING";
  function chooseSide(next: "BUY" | "SELL") {
    setSide(next); setUnit(next === "BUY" ? "dollars" : "shares"); setAmount(next === "BUY" ? "100" : "1"); setError(null);
  }
  async function prepare(event: FormEvent) {
    event.preventDefault();
    if (!accountId || !selected || validation || submitting.current) return;
    submitting.current = true; setBusy(true); setError(null);
    try {
      const preview = await api.previewOrder({ account_id: accountId, symbol, side, order_type: orderType,
        ...(dollars ? { notional: input } : { quantity: count }),
        ...(orderType === "LIMIT" ? { limit_price: Number(limit) } : {}),
      });
      setReview({ server: preview, price: Number(preview.estimated_price), timestamp: preview.quote_timestamp,
        request: { account_id: preview.account_id, side: preview.side, order_type: preview.order_type, quantity: Number(preview.quantity) } });
      setUncertain(false);
    } catch (failure) { setError(errorMessage(failure)); }
    finally { setBusy(false); submitting.current = false; }
  }
  async function confirm() {
    if (!activeReview || submitting.current) return;
    submitting.current = true; setBusy(true); setError(null);
    try {
      const order = await api.confirmOrder(activeReview.server.id);
      setPlaced(order); setReview(null); setUncertain(false); account.reload(); onFilled();
    } catch (failure) {
      const unknown = !(failure instanceof ApiError) || failure.status >= 500;
      setUncertain(unknown);
      setError(unknown ? "We couldn’t confirm the result. Check Activity, or retry this same order safely using the button below." : errorMessage(failure));
    } finally { setBusy(false); submitting.current = false; }
  }
  return <section id="trade-ticket" className="l-order-ticket" tabIndex={-1} aria-label={`Paper trade ${symbol}`}>
    <header><h2>{placed ? open ? "Order placed" : "Trade complete" : activeReview ? "Review order" : `Trade ${symbol}`}</h2><span>Paper</span></header>
    {placed ? <div className="l-confirmation" role="status">
      <span className={`l-confirmation-icon ${open ? "is-pending" : ""}`}>{open ? <Clock3 size={23}/> : <Check size={23}/>}</span>
      <h3>{open ? "Limit order open" : "Order filled"}</h3>
      <p>{open ? <>Order to {placed.side.toLowerCase()} <strong>{quantity(placed.quantity)} {placed.symbol}</strong><br/>at {money(placed.limit_price)} or better.</> : <>{placed.side === "BUY" ? "Bought" : "Sold"} <strong>{quantity(placed.filled_quantity)} {placed.symbol}</strong><br/>at {money(placed.avg_fill_price)} per share.</>}</p>
      {open && <p>Reserved until filled or canceled.</p>}
      <Link href="/orders" className="l-button">View activity<ArrowRight size={15}/></Link>
      <button className="l-button l-quiet" onClick={() => { setPlaced(null); setError(null); }}>Place another trade</button>
    </div> : !accountId ? <><p className="l-note">Sign in to trade with virtual cash.</p><Link href="/dashboard" className="l-button" style={{ marginTop: 20 }}>Sign in<ArrowRight size={15}/></Link></> : activeReview ? <>
      <div className="l-review-heading"><ClipboardCheck size={22}/><strong>{activeReview.request.side === "BUY" ? "Buy" : "Sell"} {quantity(activeReview.request.quantity)} {symbol}</strong></div>
      <dl className="l-trade-details"><div><dt>Order type</dt><dd>{activeReview.request.order_type === "LIMIT" ? "Limit · until canceled" : "Market"}</dd></div><div><dt>{activeReview.request.order_type === "LIMIT" ? "Limit price" : "Estimated price"}</dt><dd>{money(activeReview.price)}</dd></div><div><dt>Fees</dt><dd>{money(activeReview.server.fees)}</dd></div><div className="l-estimate"><dt>Estimated {activeReview.request.side === "BUY" ? "cost" : "proceeds"}</dt><dd>{money(activeReview.server.estimated_total)}</dd></div></dl>
      <section className="l-review-impact"><h3>{activeReview.request.order_type === "LIMIT" ? "If filled" : "Estimated balance"}</h3><div><span>Cash balance</span><strong>{money(activeReview.server.cash_after)}</strong></div><div><span>{symbol} shares</span><strong>{quantity(activeReview.server.shares_after)}</strong></div></section>
      <p className="l-note l-review-meta">Quote {timestamp(activeReview.timestamp)} · Expires {timestamp(activeReview.server.expires_at)}.</p>
      <details className="l-order-info"><summary>Order details</summary><p>{activeReview.request.order_type === "LIMIT" ? "Fills at your limit or better. Unfilled orders reserve cash or shares until filled or canceled." : "Estimated using the latest available price. Final price and share count may vary; dollar buys stay within your budget."}</p></details>
      {error && <ErrorNotice message={error}/>}
      {uncertain && <Link href="/orders" className="l-text-link">Check activity<ArrowRight size={14}/></Link>}
      <button className="l-button" onClick={confirm} disabled={busy}>{busy ? "Placing paper order…" : uncertain ? "Retry same order safely" : `Confirm ${activeReview.request.side.toLowerCase()}`}<ArrowRight size={15}/></button>
      <button className="l-button l-quiet" disabled={busy || uncertain} onClick={() => { setReview(null); setError(null); }}><ChevronLeft size={15}/>Edit order</button>
    </> : <>
      <div className="l-side-toggle" aria-label="Order side">{(["BUY", "SELL"] as const).map(value => <button key={value} className={side === value ? "active" : ""} aria-pressed={side === value} onClick={() => chooseSide(value)}>{value === "BUY" ? "Buy" : "Sell"}</button>)}</div>
      <form className="l-form" onSubmit={prepare}>
        <label htmlFor="order-type">Order type<select id="order-type" value={orderType} onChange={e => { const next = e.target.value as "MARKET" | "LIMIT"; setOrderType(next); setUnit("shares"); setAmount("1"); setLimit(Number(quote?.close) > 0 ? Number(quote?.close).toFixed(2) : ""); setError(null); }}><option value="MARKET">Market</option><option value="LIMIT">Limit</option></select></label>
        {side === "BUY" && orderType === "MARKET" && <div className="l-unit-toggle" aria-label="Enter order in"><button type="button" aria-pressed={unit === "dollars"} className={unit === "dollars" ? "active" : ""} onClick={() => { setUnit("dollars"); setAmount("100"); }}>Dollars</button><button type="button" aria-pressed={unit === "shares"} className={unit === "shares" ? "active" : ""} onClick={() => { setUnit("shares"); setAmount("1"); }}>Shares</button></div>}
        <label htmlFor="trade-quantity">{dollars ? "Amount (USD)" : "Shares"}<input id="trade-quantity" type="number" inputMode="decimal" min={dollars ? "1" : "0.0001"} step={dollars ? "0.01" : "0.0001"} value={amount} onChange={e => setAmount(e.target.value)} aria-describedby="trade-help trade-validation" required/></label>
        {orderType === "LIMIT" && <label htmlFor="limit-price">Limit price per share<input id="limit-price" type="number" inputMode="decimal" min="0.01" step="0.01" value={limit} onChange={e => setLimit(e.target.value)} required/><small id="trade-help">{side === "BUY" ? "Maximum buy price." : "Minimum sell price."}</small></label>}
        {orderType === "MARKET" && <p id="trade-help" className="l-field-help">{dollars && validPrice && count > 0 ? `Est. ${quantity(count)} shares` : "Up to 4 decimal places."}</p>}
        <div className="l-quick-amounts">{dollars ? [100, 500, 1000].map(value => <button type="button" key={value} onClick={() => setAmount(String(value))}>{money(value, 0)}</button>) : null}<button type="button" disabled={!selected || !validPrice} onClick={() => setAmount(side === "SELL" ? String(shares) : dollars ? String(Math.floor(cash * 100) / 100) : String(floorShares(cash / price)))}>{side === "SELL" ? "Sell all" : "Max"}</button></div>
        <dl className="l-trade-details"><div><dt>Market price</dt><dd>{quote ? money(quote.close) : "Unavailable"}</dd></div><div><dt>{side === "BUY" ? "Buying power" : "Shares available"}</dt><dd>{selected ? side === "BUY" ? money(cash) : `${quantity(shares)} shares` : "Loading…"}</dd></div><div className="l-estimate"><dt>Estimated {side === "BUY" ? "cost" : "proceeds"}</dt><dd>{validPrice && count > 0 ? money(count * price) : "—"}</dd></div></dl>
        <p id="trade-validation" className={validation ? "l-note l-negative" : "sr-only"} aria-live="polite">{validation || "Order amount is valid."}</p>
        {error && <ErrorNotice message={error}/>}
        <button className="l-button" type="submit" disabled={busy || !!validation || !selected}>{busy ? "Preparing review…" : "Review order"}<ArrowRight size={15}/></button>
      </form>
      <details className="l-order-info"><summary>About {orderType === "MARKET" ? "market" : "limit"} orders</summary><p>{orderType === "MARKET" ? "Practice trades fill at the latest available price, even outside market hours. Prices may be delayed." : "Buy at your limit or lower; sell at your limit or higher. Open orders reserve cash or shares until filled or canceled."}</p></details>
      {account.error && <ErrorNotice message="Your portfolio couldn’t be loaded. Refresh it before placing a trade." retry={account.reload}/>}
    </>}
  </section>;
}
