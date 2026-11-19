"use client";
import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, Search } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { assetNames, assetUrl, errorMessage, money, timestamp } from "@/lib/format";
import type { PriceBarRead, SymbolItem } from "@/lib/types";
import { useResource } from "@/lib/use-resource";
import { useSession } from "@/components/shell/session-provider";
import { useWatchlist } from "@/lib/watchlist";
import { AssetIdentity, Empty, ErrorNotice, Loading, PageHeading, RefreshButton, PriceChange, SaveAsset } from "./common";
const indexItems = [{ symbol: "SPY", label: "S&P 500" }, { symbol: "QQQ", label: "Nasdaq 100" }, { symbol: "DIA", label: "Dow Jones" }];
function isFund(item: SymbolItem) { return item.asset_type === "etf" || item.kind === "etf" || ["SPY", "QQQ", "DIA", "IWM", "VOO", "VIXY"].includes(item.symbol); }
function useQuotes(symbols: string[]) {
  const key = symbols.join("|");
  return useResource(`quotes:${key}`, useCallback(async () => {
    const list = key.split("|").filter(Boolean);
    const results = await Promise.allSettled(list.map((symbol) => api.getLatestPrice(symbol)));
    if (results.length && results.every((r) => r.status === "rejected") && results.some((r) => r.status === "rejected" && !(r.reason instanceof ApiError && r.reason.status === 404))) throw new Error("Prices couldn’t be loaded. Please check your connection and try again.");
    return Object.fromEntries(results.map((result, index) => [list[index], result.status === "fulfilled" ? result.value : null])) as Record<string, PriceBarRead | null>;
  }, [key]));
}
export function Discover({ saved = false }: { saved?: boolean }) {
  const watchlist = useWatchlist(); const session = useSession();
  const symbols = useResource("symbol-directory", useCallback(() => api.getSymbols(), []));
  const [query, setQuery] = useState(""); const [tab, setTab] = useState("all"); const [page, setPage] = useState(0);
  const [refreshing, setRefreshing] = useState(false); const [refreshError, setRefreshError] = useState<string | null>(null);
  const filtered = useMemo(() => {
    const catalog = saved ? watchlist.symbols.map((symbol) => symbols.data?.find((item) => item.symbol === symbol) ?? { symbol, name: assetNames[symbol] }) : symbols.data ?? [];
    return catalog.filter((item) => (!query || `${item.symbol} ${item.name || ""}`.toLowerCase().includes(query.toLowerCase())) && (tab === "all" || (tab === "funds" ? isFund(item) : !isFund(item)))).sort((a, b) => a.symbol.localeCompare(b.symbol));
  }, [symbols.data, query, tab, saved, watchlist.symbols]);
  const maxPage = Math.max(0, Math.ceil(filtered.length / 12) - 1); const currentPage = Math.min(page, maxPage);
  const visible = filtered.slice(currentPage * 12, currentPage * 12 + 12);
  const quoteSymbols = Array.from(new Set([...(!saved ? indexItems.map((i) => i.symbol) : []), ...visible.map((i) => i.symbol)]));
  const quotes = useQuotes(quoteSymbols);
  async function refresh() { setRefreshing(true); setRefreshError(null); try { await api.latestBulk(quoteSymbols, { force: true }); quotes.reload(); } catch (error) { setRefreshError(errorMessage(error)); } finally { setRefreshing(false); } }
  async function seed() { setRefreshing(true); setRefreshError(null); try { await api.seedDefaultWatchlist(); symbols.reload(); } catch (error) { setRefreshError(errorMessage(error)); } finally { setRefreshing(false); } }
  return <><PageHeading title={saved ? "Watchlist" : "Discover"}><RefreshButton busy={refreshing || quotes.loading} onClick={refresh}/>{saved && <Link href="/markets" className="l-button">Find investments<ArrowRight size={15}/></Link>}</PageHeading>
    {saved && !session.userId && <p className="l-note" style={{ marginBottom: 20 }}>Guest watchlist · This device</p>}
    {symbols.error && <ErrorNotice message={symbols.error} retry={symbols.reload}/>}{quotes.error && <ErrorNotice message={quotes.error} retry={quotes.reload}/>}{refreshError && <ErrorNotice message={refreshError} retry={refresh}/>}
    {!saved && <section className="l-discovery-indices" aria-label="Broad market ETFs">{indexItems.map((item) => { const quote = quotes.data?.[item.symbol]; return <Link href={assetUrl(item.symbol)} className="l-index" key={item.symbol}><span className="l-index-title">{item.label}<b>{item.symbol} ETF</b></span><strong className="l-index-value">{money(quote?.close)}</strong><PriceChange change={quote?.change} percentage={quote?.change_percent}/><small>{quote ? timestamp(quote.timestamp) : quotes.loading ? "Loading quote…" : "Open to load market data"}</small></Link>; })}</section>}
    {symbols.loading && !symbols.data ? <Loading label="Loading investments"/> : saved && !watchlist.symbols.length ? <section className="l-surface"><Empty title="Your watchlist is empty" description="Bookmark an asset to save it." action="Find investments"/></section> : !symbols.data?.length && !saved && !symbols.error ? <section className="l-surface"><Empty title="No assets loaded"/><div style={{ textAlign: "center", paddingBottom: 30 }}><button className="l-button" onClick={seed} disabled={refreshing}>Load assets<ArrowRight size={15}/></button></div></section> : <section className="l-surface"><div className="l-toolbar"><label className="l-search-input"><Search size={16}/><span className="sr-only">Filter investments</span><input placeholder="Filter assets" value={query} onChange={(e) => { setQuery(e.target.value); setPage(0); }}/></label><div className="l-tabs" aria-label="Asset type">{[["all", "All"], ["stocks", "Stocks"], ["funds", "Funds"]].map(([id, label]) => <button key={id} className={tab === id ? "active" : ""} aria-pressed={tab === id} onClick={() => { setTab(id); setPage(0); }}>{label}</button>)}</div></div>
      {!filtered.length ? <Empty title="No matches" description="Try another name or symbol."/> : <div className="l-table-scroll"><table className="l-table"><thead><tr><th scope="col">Asset</th><th scope="col">Price</th><th scope="col" className="l-mobile-hide">As of</th><th scope="col"><span className="sr-only">Save or research</span></th></tr></thead><tbody>{visible.map((item) => { const quote = quotes.data?.[item.symbol]; return <tr key={item.symbol}><td><AssetIdentity symbol={item.symbol} name={item.name}/></td><td>{quote ? money(quote.close) : <span className="l-price-missing">{quotes.loading ? "Loading…" : "Not loaded"}</span>}<small><PriceChange change={quote?.change} percentage={quote?.change_percent}/>{quote?.change == null && (isFund(item) ? "Fund" : "Stock")}</small><small className="l-mobile-only l-row-quote-time">{quote ? timestamp(quote.timestamp) : "Quote time unavailable"}</small></td><td className="l-mobile-hide"><span className="l-muted">{quote ? timestamp(quote.timestamp) : "—"}</span></td><td><div className="l-table-actions"><SaveAsset symbol={item.symbol}/><Link className="l-icon-button" href={assetUrl(item.symbol)} aria-label={`Research ${item.symbol}`}><ArrowRight size={17}/></Link></div></td></tr>; })}</tbody></table></div>}
      {filtered.length > 0 && <div className="l-pagination"><span>{currentPage * 12 + 1}–{Math.min((currentPage + 1) * 12, filtered.length)} of {filtered.length} investments</span><div className="l-actions"><button className="l-button l-quiet" disabled={!currentPage} onClick={() => setPage(currentPage - 1)}>Previous</button><button className="l-button l-quiet" disabled={currentPage >= maxPage} onClick={() => setPage(currentPage + 1)}>Next</button></div></div>}
    </section>}
  </>;
}
