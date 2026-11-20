"use client";
import { useCallback, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { money as formatMoney, signedMoney as formatSignedMoney, percent, timestamp, ymd } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import { Empty, ErrorNotice } from "./common";
const ranges = [{ label: "1W", days: 7 }, { label: "1M", days: 30 }, { label: "3M", days: 90 }, { label: "6M", days: 180 }, { label: "1Y", days: 365 }];
export function HistoryChart({ symbol, currency }: { symbol: string; currency: string | null }) {
  const [days, setDays] = useState(30);
  const money = (value: unknown, digits?: number) => formatMoney(value, digits, currency);
  const signedMoney = (value: unknown) => formatSignedMoney(value, currency);
  const resource = useResource(`history:${symbol}:${currency}:${days}`, useCallback(async () => {
    const end = new Date(); const start = new Date(end.getTime() - days * 86400000);
    const params = { symbol, start: ymd(start), end: ymd(end) };
    let rows = await api.getHistory(params).catch(() => []);
    const first = rows[0]; const last = rows.at(-1);
    const incomplete = rows.some(row => row.currency !== currency) || !first || !last || new Date(first.timestamp).getTime() > start.getTime() + 5 * 86400000 || new Date(last.timestamp).getTime() < end.getTime() - 5 * 86400000;
    if (incomplete) {
      await api.loadStock({ ...params, interval: "1d" });
      rows = await api.getHistory(params);
    }
    return rows.filter(row => row.currency === currency).map((r) => ({ time: new Date(r.timestamp).getTime(), close: Number(r.close), open: Number(r.open), high: Number(r.high), low: Number(r.low) })).filter((r) => Number.isFinite(r.time) && Number.isFinite(r.close)).sort((a, b) => a.time - b.time);
  }, [symbol, currency, days]));
  const rows = resource.data ?? []; const last = rows.at(-1);
  const change = last && rows[0] ? last.close - rows[0].close : 0;
  const tone = change > 0 ? "var(--l-positive)" : change < 0 ? "var(--l-negative)" : "var(--l-ink)";
  return <section className="l-chart-panel" aria-label={`${symbol} historical closing prices`}><header className="l-chart-head"><div><h2>Price history</h2>{rows.length > 1 && <p className="l-range-change" style={{ color: tone }}>{signedMoney(change)} ({percent(change / rows[0].close * 100, true)})</p>}</div><div className="l-tabs" aria-label="History range">{ranges.map((range) => <button key={range.label} className={days === range.days ? "active" : ""} aria-pressed={days === range.days} onClick={() => setDays(range.days)}>{range.label}</button>)}</div></header>
    {resource.error && <ErrorNotice message={resource.error} retry={resource.reload}/>}
    {resource.loading && !resource.data ? <div className="l-chart l-skeleton" role="status"><span className="sr-only">Loading price history</span></div> : rows.length ? <div className="l-chart" role="img" aria-label={`${symbol}: ${rows.length} observations, from ${money(rows[0].close)} to ${money(last?.close)}. ${days}-day range.`}><ResponsiveContainer width="100%" height="100%" minWidth={0}><AreaChart data={rows} margin={{ top: 12, right: 8, bottom: 0, left: 0 }}><CartesianGrid vertical={false} stroke="#e9e0cf"/><XAxis dataKey="time" type="number" domain={["dataMin", "dataMax"]} scale="time" tickLine={false} axisLine={false} minTickGap={35} tick={{ fill: "#6c6457", fontSize: 10 }} tickFormatter={(time) => new Date(time).toLocaleDateString("en-US", { month: "short", day: "numeric" })}/><YAxis tickLine={false} axisLine={false} width={currency === "VND" ? 82 : 62} domain={["auto", "auto"]} tick={{ fill: "#6c6457", fontSize: 10 }} tickFormatter={(value) => money(value, 0)}/><Tooltip cursor={{ stroke: "#9d8b6a", strokeDasharray: "3 3" }} labelFormatter={(time) => timestamp(new Date(Number(time)).toISOString())} formatter={(value) => [money(value), "Close"]} contentStyle={{ border: "none", borderRadius: 9, boxShadow: "0 5px 22px #211f1b20", fontSize: 12, color: "#40382b" }}/><Area type="linear" dataKey="close" stroke={tone} strokeWidth={2} fill={tone} fillOpacity={0.065} isAnimationActive={false} dot={rows.length === 1}/></AreaChart></ResponsiveContainer></div> : !resource.error && <Empty title="No history in this range." description="Try another range or another investment."/>}
    {last && <details className="l-price-details"><summary>Price details</summary><dl className="l-chart-stats"><div><dt>Open</dt><dd>{money(last.open)}</dd></div><div><dt>High</dt><dd>{money(last.high)}</dd></div><div><dt>Low</dt><dd>{money(last.low)}</dd></div><div><dt>Close</dt><dd>{money(last.close)}</dd></div></dl></details>}
  </section>;
}
