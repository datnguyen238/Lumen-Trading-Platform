"use client";
import { useCallback, useState } from "react";
import Link from "next/link";
import { ChevronLeft, Clock3, Search } from "lucide-react";
import { api } from "@/lib/api";
import type { PriceRangeDays } from "@/lib/types";
import { assetNames, money as formatMoney, quantity, signedMoney as formatSignedMoney, timestamp } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import { tradeStats } from "@/lib/trade-stats";
import { useSession } from "@/components/shell/session-provider";
import { useAccount } from "./data";
import { AssetLogo, PriceChange, ErrorNotice, Loading, RefreshButton, SaveAsset } from "./common";
import { HistoryChart } from "./history-chart";
import { TradeTicket } from "./trade-ticket";
import { RecentActivity } from "./recent-activity";
export function Research({ symbol }: { symbol: string }) {
  const session = useSession();
  const [historyDays, setHistoryDays] = useState<PriceRangeDays>(30);
  const account = useAccount(); const [tab, setTab] = useState("position");
  const quote = useResource(`asset:${symbol}`, useCallback(() => api.refreshLatestPrice(symbol), [symbol]));
  const currency = quote.data?.currency;
  const priceRange = useResource(`asset-range:${symbol}:${currency}:${historyDays}`, useCallback(
    () => currency ? api.getPriceRange(symbol, historyDays) : Promise.resolve(null), [symbol, currency, historyDays]));
  const range = !priceRange.error && priceRange.data?.symbol === symbol.toUpperCase()
    && priceRange.data.currency === currency && priceRange.data.days === historyDays ? priceRange.data : null;
  const refreshAsset = () => { quote.reload(); priceRange.reload(); };
  const name = useResource(`asset-name:${symbol}`, useCallback(async () => { const symbols = await api.getSymbols(); const known = symbols.find((item) => item.symbol === symbol); if (known) return known.name || assetNames[symbol] || symbol; const added = await api.addSymbol({ symbol }).catch(() => null); return added?.name || assetNames[symbol] || symbol; }, [symbol]));
  const position = account.data?.summary.positions[symbol]; const trades = account.data?.trades.filter((trade) => trade.symbol === symbol) ?? [];
  const stats = tradeStats(trades);
  const money = (value: unknown, digits?: number) => formatMoney(value, digits, quote.data?.currency ?? null);
  const signedMoney = (value: unknown) => formatSignedMoney(value, account.data?.summary.currency ?? null);
  return <><Link href="/markets" className="l-breadcrumb"><ChevronLeft size={14}/>Discover</Link><header className="l-asset-heading"><div><div className="l-symbol-title"><AssetLogo key={symbol} symbol={symbol}/>{symbol}</div><h1>{name.data || assetNames[symbol] || symbol}</h1>{quote.data && <div className="l-price-block"><strong>{money(quote.data.close)}</strong><PriceChange change={quote.data.change} percentage={quote.data.change_percent} currency={quote.data.currency}/><p><Clock3 size={11} style={{ display: "inline", marginRight: 5 }}/>{quote.data.currency || "Currency unavailable"} · As of {timestamp(quote.data.timestamp)}</p></div>}</div><div className="l-actions">{quote.data && <><a href="#trade-ticket" className="l-button l-mobile-trade">Trade</a><SaveAsset symbol={symbol}/></>}<RefreshButton busy={quote.loading} onClick={refreshAsset}/></div></header>
    {quote.error && quote.data && <ErrorNotice message={quote.error} retry={quote.reload}/>}
    {!quote.data ? quote.loading ? <Loading label="Loading market data"/> : <section className="l-surface l-research-unavailable" aria-labelledby="unavailable-heading"><div className="l-empty"><h2 id="unavailable-heading">Market data unavailable</h2><p>A price isn’t available for {symbol}. Search for a listed stock or fund, or try again.</p><div className="l-actions"><button className="l-button" onClick={() => window.dispatchEvent(new CustomEvent("lumen-open-search", { detail: symbol }))}><Search size={16} aria-hidden="true"/>Search investments</button><button className="l-button l-secondary" onClick={refreshAsset}>Try again</button></div></div></section> : <div className="l-research-grid"><div><HistoryChart symbol={symbol} currency={quote.data.currency} days={historyDays} onDaysChange={setHistoryDays} dateRange={range} rangeLoading={priceRange.loading}/><section className="l-position"><div className="l-tabs" style={{ marginBottom: 22 }} aria-label="Your asset details"><button className={tab === "position" ? "active" : ""} aria-pressed={tab === "position"} onClick={() => setTab("position")}>Position</button><button className={tab === "activity" ? "active" : ""} aria-pressed={tab === "activity"} onClick={() => setTab("activity")}>Activity</button></div>{tab === "position" ? position ? <><dl className="l-position-values"><div><dt>Shares owned</dt><dd>{quantity(position.quantity)}</dd></div><div><dt>Average cost</dt><dd>{formatMoney(position.avg_cost, undefined, position.currency)}</dd></div><div><dt>Market value</dt><dd>{formatMoney(position.market_value, undefined, position.currency)}</dd></div></dl><p className={`l-screen-note ${Number(position.unrealized_pnl) > 0 ? "l-positive" : Number(position.unrealized_pnl) < 0 ? "l-negative" : "l-muted"}`}>{signedMoney(position.unrealized_pnl)} open return</p></> : <p className="l-inline-empty">{account.loading ? "Loading your position…" : "No shares owned."}</p> : <><dl className="l-position-values"><div><dt>Realized return</dt><dd className={stats.realized > 0 ? "l-positive" : stats.realized < 0 ? "l-negative" : ""}>{signedMoney(stats.realized)}</dd></div><div><dt>Profitable sales</dt><dd>{stats.winRate === null ? "—" : `${stats.winRate.toFixed(1)}%`}</dd></div><div><dt>Completed sales</dt><dd>{stats.sales}</dd></div></dl><RecentActivity trades={trades} limit={5}/></>}</section></div><TradeTicket key={`${symbol}:${session.accountId}:${quote.data.currency}`} symbol={symbol} quote={quote.data} rangeDays={historyDays} priceRange={range} rangeLoading={priceRange.loading} onRangeRetry={priceRange.reload} onFilled={refreshAsset}/></div>}
  </>;
}
