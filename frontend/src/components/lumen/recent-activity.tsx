"use client";
import Link from "next/link";
import { ArrowDownLeft, ArrowUpRight } from "lucide-react";
import type { TradeRead } from "@/lib/types";
import { assetUrl, money, quantity, timestamp } from "@/lib/format";
export function RecentActivity({ trades, limit = 3 }: { trades: TradeRead[]; limit?: number }) {
  if (!trades.length) return <p className="l-inline-empty">No trades yet.</p>;
  return <div>{trades.slice(0, limit).map((trade) => <div className="l-activity-row" key={trade.id}><span className={`l-trade-icon ${trade.side === "SELL" ? "sell" : ""}`} aria-hidden="true">{trade.side === "BUY" ? <ArrowDownLeft size={17}/> : <ArrowUpRight size={17}/>}</span><div><Link href={assetUrl(trade.symbol)} className="l-text-link"><strong>{trade.side === "BUY" ? "Bought" : "Sold"} {quantity(trade.quantity)} {trade.symbol}</strong></Link><small>{timestamp(trade.executed_at)}</small></div><div className="l-activity-amount"><strong>{money(trade.account_total, undefined, trade.account_currency)}</strong><small>{money(trade.price, undefined, trade.currency)} per share</small></div></div>)}</div>;
}
