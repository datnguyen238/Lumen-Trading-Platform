"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowDownUp, ArrowRight, Clock3, TrendingDown, TrendingUp } from "lucide-react";
import { useSession } from "@/components/shell/session-provider";
import { money as formatMoney, percent, quantity, signedMoney as formatSignedMoney, timestamp } from "@/lib/format";
import { useAccount } from "./data";
import { AccountSetup } from "./account-setup";
import { AssetIdentity, Empty, ErrorNotice, Loading, PageHeading, RefreshButton } from "./common";
import { RecentActivity } from "./recent-activity";
const allocationColors = ["#3a362e", "#837864", "#ac9d82", "#c6b89d", "#c8c0b0"];
export function Portfolio() {
  const session = useSession(); const { data, error, loading, reload } = useAccount();
  const [includeClosed, setIncludeClosed] = useState(false);
  const money = (value: unknown, digits?: number) => formatMoney(value, digits, data?.summary.currency ?? null);
  const signedMoney = (value: unknown) => formatSignedMoney(value, data?.summary.currency ?? null);
  const [sort, setSort] = useState<{ field: "symbol" | "value" | "return"; asc: boolean }>({ field: "value", asc: false });
  const rows = useMemo(() => {
    if (!data) return [];
    return data.positions.filter((p) => includeClosed || Number(p.quantity) > 0).map((position) => ({ ...position, mark: data.summary.positions[position.symbol]?.mark_price, value: Number(data.summary.positions[position.symbol]?.market_value ?? 0), pnl: Number(data.summary.positions[position.symbol]?.unrealized_pnl ?? 0) })).sort((a, b) => (sort.field === "symbol" ? a.symbol.localeCompare(b.symbol) : sort.field === "value" ? a.value - b.value : a.pnl - b.pnl) * (sort.asc ? 1 : -1));
  }, [data, includeClosed, sort]);
  if (!session.ready) return <Loading/>;
  if (!session.accountId) return <AccountSetup/>;
  if (!data && loading) return <Loading/>;
  if (!data) return <><PageHeading title="Your portfolio" description="Your account data is temporarily unavailable."/>{error && <ErrorNotice message={error} retry={reload}/>}<button className="l-button l-secondary" onClick={session.forgetSelection}>Choose another portfolio</button></>;
  const reservedCash = Number(data.summary.reserved_cash);
  const summary = data.summary; const equity = Number(summary.equity); const totalPnl = Number(summary.total_pnl); const basis = equity - totalPnl;
  const positions = Object.values(summary.positions).sort((a, b) => Number(b.market_value) - Number(a.market_value));
  const oldestQuote = data.quotes.map((q) => q.timestamp).filter((time): time is string => !!time).sort()[0];
  const segments = positions.slice(0, 3).map((p, index) => ({ label: p.symbol, value: Number(p.market_value), color: allocationColors[index] }));
  if (positions.length > 3) segments.push({ label: "Other holdings", value: positions.slice(3).reduce((sum, p) => sum + Number(p.market_value), 0), color: allocationColors[3] });
  segments.push({ label: "Cash", value: Number(summary.cash), color: "#d1c5ab" });
  const sortBy = (field: typeof sort.field) => setSort((s) => ({ field, asc: field === s.field ? !s.asc : field === "symbol" }));
  return <><PageHeading title={`Portfolio · ${data.account.currency}`}><RefreshButton busy={loading} onClick={reload}/><Link className="l-button" href="/markets">Explore investments<ArrowRight size={15}/></Link></PageHeading>
    {error && <ErrorNotice message={error} retry={reload}/>}
    <section className={`l-summary ${summary.currency === "VND" ? "l-summary-vnd" : ""}`} aria-label="Portfolio balances"><div className="l-summary-primary"><span className="l-summary-label">Portfolio value</span><div className="l-equity">{money(summary.equity)}</div><div className={`l-return ${totalPnl > 0 ? "l-positive" : totalPnl < 0 ? "l-negative" : "l-muted"}`}>{totalPnl < 0 ? <TrendingDown size={14}/> : <TrendingUp size={14}/>}{signedMoney(totalPnl)} total return{basis > 0 ? ` · ${percent(totalPnl / basis * 100, true)}` : ""}</div></div><div className="l-summary-secondary"><span className="l-summary-label">Buying power</span><strong>{money(summary.available_cash)}</strong>{reservedCash > 0 && <p>{money(reservedCash)} reserved</p>}</div><div className="l-summary-secondary"><span className="l-summary-label">Invested</span><strong>{money(summary.market_value)}</strong>{positions.length > 0 && <p>{positions.length} {positions.length === 1 ? "position" : "positions"}</p>}</div></section>
    <div className={`l-portfolio-grid ${positions.length === 0 ? "l-no-holdings" : ""}`}><div><section className="l-surface"><div className="l-section-heading"><h2>Holdings</h2>{data.positions.some(p => Number(p.quantity) === 0) && <label className="l-note" style={{ display: "flex", gap: 6, alignItems: "center", fontSize: ".6875rem" }}><input type="checkbox" checked={includeClosed} onChange={(e) => setIncludeClosed(e.target.checked)}/>Include closed</label>}</div>
      {!rows.length ? <Empty title="No holdings yet" action="Explore investments"/> : <div className="l-table-scroll"><table className="l-table"><thead><tr><th scope="col" aria-sort={sort.field === "symbol" ? sort.asc ? "ascending" : "descending" : "none"}><button onClick={() => sortBy("symbol")}>Asset<ArrowDownUp size={11}/></button></th><th scope="col" className="l-mobile-hide">Last price</th><th scope="col" aria-sort={sort.field === "value" ? sort.asc ? "ascending" : "descending" : "none"}><button onClick={() => sortBy("value")}>Market value<ArrowDownUp size={11}/></button></th><th scope="col" aria-sort={sort.field === "return" ? sort.asc ? "ascending" : "descending" : "none"}><button onClick={() => sortBy("return")}>Open return<ArrowDownUp size={11}/></button></th></tr></thead><tbody>{rows.map((row) => { const cost = Number(row.quantity) * Number(row.average_price); return <tr key={row.id}><td><AssetIdentity symbol={row.symbol}/></td><td className="l-mobile-hide">{money(row.mark)}<small>Avg {money(row.average_price)}</small></td><td>{money(row.value)}<small>{quantity(row.quantity)} shares</small></td><td className={row.pnl > 0 ? "l-positive" : row.pnl < 0 ? "l-negative" : "l-muted"}>{signedMoney(row.pnl)}<small>{cost > 0 ? percent(row.pnl / cost * 100, true) : "Closed"}</small></td></tr>; })}</tbody></table></div>}
      {positions.length > 0 && <div className="l-table-note"><Clock3 size={12}/>{oldestQuote ? `As of ${timestamp(oldestQuote)}` : "Latest available prices"}</div>}</section>
      {data.trades.length > 0 && <section className="l-recent"><header><h2>Recent activity</h2><Link href="/orders" className="l-text-link">View all<ArrowRight size={13}/></Link></header><RecentActivity trades={data.trades}/></section>}
    </div>{positions.length > 0 && <aside className="l-portfolio-aside"><section className="l-allocation"><h2>Allocation</h2><div className="l-band" role="img" aria-label={segments.map((s) => `${s.label}: ${equity > 0 ? percent(s.value / equity * 100) : "0%"}`).join(", ")}>{segments.filter((s) => s.value > 0).map((s) => <span key={s.label} style={{ width: `${equity > 0 ? s.value / equity * 100 : 0}%`, background: s.color }}/>)}</div><div className="l-allocation-list">{segments.map((s) => <div key={s.label}><span className="l-swatch" style={{ background: s.color }}/><span>{s.label}</span><strong>{equity > 0 ? percent(s.value / equity * 100) : "0.00%"}</strong></div>)}</div></section></aside>}</div>
    {data.trades.length > 0 && <p className="l-screen-note">Realized {signedMoney(summary.realized_pnl)}<span aria-hidden="true">·</span>Open {signedMoney(summary.unrealized_pnl)}</p>}
  </>;
}
