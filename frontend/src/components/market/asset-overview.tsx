"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useSession } from "@/components/shell/session-provider";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { OrderRead, PositionRead, PriceBarRead, TradeRead } from "@/lib/types";

type ActivityTab = "orders" | "trades";

type UiState =
  | { kind: "loading" }
  | {
      kind: "ready";
      latest: PriceBarRead | null;
      position: PositionRead | null;
      orders: OrderRead[];
      trades: TradeRead[];
      pnlSeries: Array<{ ts: number; pnl: number }>;
      realizedPnl: number;
      winRate: number | null;
      closedTrades: number;
    }
  | { kind: "error"; message: string };

export function AssetOverview(props: { symbol: string; latestOverride?: PriceBarRead | null; refreshNonce?: number }) {
  const symbol = props.symbol.toUpperCase();
  const { accountId } = useSession();
  const [tab, setTab] = useState<ActivityTab>("orders");
  const [openOrdersOnly, setOpenOrdersOnly] = useState(false);
  const [state, setState] = useState<UiState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setState({ kind: "loading" });
      try {
        const latest = props.latestOverride ?? null;

        let position: PositionRead | null = null;
        let orders: OrderRead[] = [];
        let trades: TradeRead[] = [];
        let pnlSeries: Array<{ ts: number; pnl: number }> = [];
        let realizedPnl = 0;
        let winRate: number | null = null;
        let closedTrades = 0;
        if (accountId) {
          const [positions, rawOrders, rawTrades] = await Promise.all([
            api.getPositions(accountId),
            api.getOrders(accountId),
            api.getTrades(accountId),
          ]);
          position = positions.find((p) => norm(p.symbol) === norm(symbol)) ?? null;
          const symbolOrders = rawOrders.filter((o) => norm(o.symbol) === norm(symbol));
          const symbolTrades = rawTrades.filter((t) => norm(t.symbol) === norm(symbol));
          const tradeStats = computeTradeStats(symbolTrades);

          orders = symbolOrders.slice(0, 20);
          trades = symbolTrades.slice(0, 20);
          realizedPnl = tradeStats.realizedPnl;
          winRate = tradeStats.winRate;
          closedTrades = tradeStats.closedTrades;

          if (position) {
            const qty = Number(position.quantity);
            const avg = Number(position.average_price);
            if (Number.isFinite(qty) && Number.isFinite(avg) && qty > 0) {
              const end = new Date();
              const start = new Date();
              start.setDate(end.getDate() - 30);
              const history = await api
                .getHistory({ symbol, start: toYmd(start), end: toYmd(end) })
                .catch(() => []);

              pnlSeries = history
                .map((h) => {
                  const ts = new Date(h.timestamp).getTime();
                  const close = Number(h.close);
                  return { ts, pnl: (close - avg) * qty };
                })
                .filter((p) => Number.isFinite(p.ts) && Number.isFinite(p.pnl))
                .sort((a, b) => a.ts - b.ts);
            }
          }
        }

        if (cancelled) return;
        setState({ kind: "ready", latest, position, orders, trades, pnlSeries, realizedPnl, winRate, closedTrades });
      } catch (e) {
        if (cancelled) return;
        setState({
          kind: "error",
          message: e instanceof Error ? e.message : "Failed to load asset overview",
        });
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [symbol, accountId, props.latestOverride?.timestamp, props.refreshNonce]);

  const stats = useMemo(() => {
    if (state.kind !== "ready") return null;

    const last = state.latest ? Number(state.latest.close) : NaN;
    const open = state.latest ? Number(state.latest.open) : NaN;
    const high = state.latest ? Number(state.latest.high) : NaN;
    const low = state.latest ? Number(state.latest.low) : NaN;
    const volume = state.latest ? Number(state.latest.volume ?? "") : NaN;
    const dayMove = Number.isFinite(last) && Number.isFinite(open) ? ((last - open) / open) * 100 : NaN;

    const qty = state.position ? Number(state.position.quantity) : NaN;
    const avg = state.position ? Number(state.position.average_price) : NaN;
    const marketValue = Number.isFinite(last) && Number.isFinite(qty) ? qty * last : NaN;
    const unrealized = Number.isFinite(last) && Number.isFinite(qty) && Number.isFinite(avg)
      ? (last - avg) * qty
      : NaN;

    return { last, open, high, low, volume, dayMove, qty, avg, marketValue, unrealized };
  }, [state]);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Last" value={stats ? formatUsd(stats.last) : "$—"} />
        <MetricCard title="Day Change" value={stats ? formatPct(stats.dayMove) : "—"} tone={toneFromNumber(stats?.dayMove)} />
        <MetricCard title="Day Range" value={stats ? `${formatUsd(stats.low)} - ${formatUsd(stats.high)}` : "—"} />
        <MetricCard title="Volume" value={stats ? formatInt(stats.volume) : "—"} />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium">Your Position</CardTitle>
            {!accountId && <Badge variant="outline">Set account_id to view</Badge>}
          </div>
        </CardHeader>
        <CardContent>
          {state.kind === "loading" && <div className="text-sm text-muted-foreground">Loading position...</div>}
          {state.kind === "error" && <div className="text-sm text-rose-500">{state.message}</div>}
          {state.kind === "ready" && !state.position && (
            <div className="text-sm text-muted-foreground">No open position for {symbol}.</div>
          )}
          {state.kind === "ready" && state.position && (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <MiniStat label="Quantity" value={formatDec(stats?.qty)} />
              <MiniStat label="Avg Cost" value={formatUsd(stats?.avg)} />
              <MiniStat label="Market Value" value={formatUsd(stats?.marketValue)} />
              <MiniStat
                label="Unrealized PnL"
                value={formatUsd(stats?.unrealized)}
                tone={toneFromNumber(stats?.unrealized)}
              />
            </div>
          )}
          {state.kind === "ready" && state.position && (
            <div className="mt-4 rounded-md border p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-xs text-muted-foreground">30D Unrealized PnL</div>
                <div className={`text-xs font-medium ${toneFromNumber(stats?.unrealized)}`}>
                  {formatUsd(stats?.unrealized)}
                </div>
              </div>
              <PnlSparkline points={state.pnlSeries} />
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              {state.kind === "ready" && (
                <>
                  <Badge variant="outline">Realized: {formatUsd(state.realizedPnl)}</Badge>
                  <Badge variant="outline">
                    Win Rate: {state.winRate === null ? "—" : `${state.winRate.toFixed(1)}%`} ({state.closedTrades})
                  </Badge>
                </>
              )}
              <Tabs value={tab} onValueChange={(v) => setTab(v as ActivityTab)}>
                <TabsList variant="line">
                  <TabsTrigger value="orders">Orders</TabsTrigger>
                  <TabsTrigger value="trades">Trades</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {state.kind === "loading" && <div className="text-sm text-muted-foreground">Loading activity...</div>}
          {state.kind === "error" && <div className="text-sm text-rose-500">{state.message}</div>}
          {state.kind === "ready" && tab === "orders" && (
            <ActivityOrders
              rows={state.orders}
              openOnly={openOrdersOnly}
              onToggleOpenOnly={() => setOpenOrdersOnly((v) => !v)}
            />
          )}
          {state.kind === "ready" && tab === "trades" && (
            <ActivityTrades rows={state.trades} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ActivityOrders(props: { rows: OrderRead[]; openOnly: boolean; onToggleOpenOnly: () => void }) {
  const visible = props.openOnly
    ? props.rows.filter((r) => r.status === "PENDING" || r.status === "PARTIALLY_FILLED")
    : props.rows;

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={props.onToggleOpenOnly}
        className={`rounded-md border px-2 py-1 text-xs ${
          props.openOnly ? "border-foreground bg-foreground text-background" : "text-muted-foreground"
        }`}
      >
        Open orders only
      </button>
      {visible.length === 0 && <div className="text-sm text-muted-foreground">No recent orders.</div>}
      {visible.length > 0 && (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Side</TableHead>
              <TableHead className="text-right">Qty</TableHead>
              <TableHead className="text-right">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="text-muted-foreground">{formatTs(r.created_at)}</TableCell>
                <TableCell className={r.side === "BUY" ? "text-emerald-600" : "text-rose-600"}>{r.side}</TableCell>
                <TableCell className="text-right tabular-nums">{r.quantity}</TableCell>
                <TableCell className="text-right text-muted-foreground">{String(r.status)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      )}
    </div>
  );
}

function ActivityTrades(props: { rows: TradeRead[] }) {
  if (props.rows.length === 0) {
    return <div className="text-sm text-muted-foreground">No recent trades.</div>;
  }
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>Side</TableHead>
            <TableHead className="text-right">Qty</TableHead>
            <TableHead className="text-right">Price</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {props.rows.map((r) => (
            <TableRow key={r.id}>
              <TableCell className="text-muted-foreground">{formatTs(r.executed_at)}</TableCell>
              <TableCell className={r.side === "BUY" ? "text-emerald-600" : "text-rose-600"}>{r.side}</TableCell>
              <TableCell className="text-right tabular-nums">{r.quantity}</TableCell>
              <TableCell className="text-right tabular-nums">{formatUsd(Number(r.price))}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function MetricCard(props: { title: string; value: string; tone?: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs text-muted-foreground">{props.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-lg font-semibold ${props.tone ?? ""}`}>{props.value}</div>
      </CardContent>
    </Card>
  );
}

function MiniStat(props: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-md border p-3">
      <div className="text-xs text-muted-foreground">{props.label}</div>
      <div className={`mt-1 text-sm font-medium tabular-nums ${props.tone ?? ""}`}>{props.value}</div>
    </div>
  );
}

function formatUsd(value: number | string | undefined) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "$—";
  return n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function formatPct(value: number | undefined) {
  if (value === undefined || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function formatInt(value: number | undefined) {
  if (value === undefined || !Number.isFinite(value)) return "—";
  return Math.round(value).toLocaleString();
}

function formatDec(value: number | undefined) {
  if (value === undefined || !Number.isFinite(value)) return "—";
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function toneFromNumber(value: number | undefined) {
  if (value === undefined || !Number.isFinite(value)) return "";
  if (value > 0) return "text-emerald-600";
  if (value < 0) return "text-rose-600";
  return "";
}

function formatTs(ts: string | undefined) {
  if (!ts) return "—";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
}

function norm(symbol: string) {
  return symbol.trim().toUpperCase();
}

function toYmd(d: Date) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function computeTradeStats(trades: TradeRead[]) {
  const sorted = [...trades].sort((a, b) => new Date(a.executed_at).getTime() - new Date(b.executed_at).getTime());
  let qty = 0;
  let avg = 0;
  let realizedPnl = 0;
  let wins = 0;
  let closedTrades = 0;

  for (const t of sorted) {
    const q = Number(t.quantity);
    const p = Number(t.price);
    if (!Number.isFinite(q) || !Number.isFinite(p) || q <= 0) continue;

    if (t.side === "BUY") {
      const nextQty = qty + q;
      avg = nextQty > 0 ? (qty * avg + q * p) / nextQty : avg;
      qty = nextQty;
      continue;
    }

    if (t.side === "SELL" && qty > 0) {
      const sold = Math.min(qty, q);
      const pnl = (p - avg) * sold;
      realizedPnl += pnl;
      if (pnl > 0) wins += 1;
      closedTrades += 1;
      qty -= sold;
      if (qty <= 0) {
        qty = 0;
        avg = 0;
      }
    }
  }

  return {
    realizedPnl,
    closedTrades,
    winRate: closedTrades > 0 ? (wins / closedTrades) * 100 : null,
  };
}

function PnlSparkline(props: { points: Array<{ ts: number; pnl: number }> }) {
  if (props.points.length < 2) {
    return <div className="text-xs text-muted-foreground">Not enough points yet.</div>;
  }

  const w = 420;
  const h = 68;
  const pad = 2;
  const ys = props.points.map((p) => p.pnl);
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const span = max - min || 1;
  const poly = props.points
    .map((p, i) => {
      const x = pad + (i / Math.max(1, props.points.length - 1)) * (w - pad * 2);
      const y = pad + (1 - (p.pnl - min) / span) * (h - pad * 2);
      return `${x},${y}`;
    })
    .join(" ");

  const tone = ys[ys.length - 1] >= 0 ? "#16a34a" : "#dc2626";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-16 w-full">
      <polyline points={poly} fill="none" stroke={tone} strokeWidth="2" />
    </svg>
  );
}
