"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { IndexCards } from "@/components/market/index-cards";
import { PopularTickers } from "@/components/market/popular-tickers";
import type { BulkLatestItem, SymbolItem } from "@/lib/types";
import Link from "next/link";

type UiState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; symbols: SymbolItem[]; latest: BulkLatestItem[] }
  | { kind: "error"; message: string };

const INDEX_SYMBOLS = [
  { label: "S&P 500", symbol: "SPY" },
  { label: "NASDAQ", symbol: "QQQ" },
  { label: "Dow Jones", symbol: "DIA" },
];

export default function MarketsPage() {
  const [state, setState] = useState<UiState>({ kind: "idle" });
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<"all" | "indexes" | "stocks">("all");
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setState({ kind: "loading" });

      try {
        // 1) GET /symbols
        let symbols = await api.getSymbols();

        // 2) Seed if needed
        if (!symbols || symbols.length === 0) {
          await api.seedDefaultWatchlist();
          symbols = await api.getSymbols();
        }

        // Build final list of symbols to price:
        // indexes + whatever /symbols returns (dedupe)
        const requested = dedupe([
          ...INDEX_SYMBOLS.map((x) => x.symbol),
          ...symbols.map((s) => s.symbol),
        ]);

        // 3) POST /prices/latest/bulk
        const latest = await api.latestBulk(requested);


        if (cancelled) return;
        setState({ kind: "ready", symbols, latest });
      } catch (e) {
        if (cancelled) return;
        setState({
          kind: "error",
          message: e instanceof Error ? e.message : "Failed to load markets",
        });
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshNow() {
    if (state.kind !== "ready") return;
    setRefreshing(true);
    try {
      const latest = await api.latestBulk(requested);
      setState((prev) => (prev.kind === "ready" ? { ...prev, latest } : prev));
    } finally {
      setRefreshing(false);
    }
  }

  const requested = useMemo(() => {
    if (state.kind !== "ready") return [];
    return dedupe([
      ...INDEX_SYMBOLS.map((x) => x.symbol),
      ...state.symbols.map((s) => s.symbol),
    ]);
  }, [state]);

  useEffect(() => {
    if (state.kind !== "ready") return;
    if (requested.length === 0) return;

    const ws = new WebSocket(`${wsBaseUrl()}/prices/ws/live`);

    ws.onopen = () => {
      ws.send(JSON.stringify({ symbols: requested }));
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type !== "prices" || !Array.isArray(msg.data)) return;
        if (msg.data.length === 0) return;

        setState((prev) => {
          if (prev.kind !== "ready") return prev;
          const map = new Map(prev.latest.map((x) => [x.symbol.trim().toUpperCase(), x]));
          for (const item of msg.data) {
            if (!item?.symbol) continue;
            map.set(String(item.symbol).trim().toUpperCase(), item);
          }
          return { ...prev, latest: Array.from(map.values()) };
        });
      } catch {
        // ignore malformed websocket payload
      }
    };

    return () => ws.close();
  }, [state.kind, requested]);

  const lastUpdated = useMemo(() => {
    if (state.kind !== "ready") return "—";
    const times = state.latest
      .map((x) => (x.timestamp ? new Date(x.timestamp).getTime() : NaN))
      .filter((t) => Number.isFinite(t));
    if (times.length === 0) return "—";
    return new Date(Math.max(...times)).toLocaleString();
  }, [state]);

  const symbolCount = state.kind === "ready" ? state.symbols.length : 0;
  const pricedCount =
    state.kind === "ready"
      ? state.latest.filter((x) => x.close !== null && x.close !== undefined).length
      : 0;

  const indexCards = useMemo(() => {
    if (state.kind !== "ready") {
      return INDEX_SYMBOLS.map((x) => ({ label: x.label, symbol: x.symbol, price: "$—" }));
    }
    const map = new Map(state.latest.map((b) => [b.symbol.trim().toUpperCase(), b]));

    return INDEX_SYMBOLS.map((x) => {
      const bar = map.get(x.symbol.trim().toUpperCase());

      return {
        label: x.label,
        symbol: x.symbol,
        price: bar ? formatUsd(bar.close) : "$—",
        ts: formatTimestamp(bar?.timestamp),
      };
    });
  }, [state]);

  const popularRows = useMemo(() => {
    if (state.kind !== "ready") return [];

    const norm = (s: string) => s.trim().toUpperCase();
    const indexSet = new Set(INDEX_SYMBOLS.map((x) => norm(x.symbol)));

    const latestMap = new Map(
      state.latest.map((b) => [norm(b.symbol), b])
    );

    const N = 12;
    return state.symbols
      .filter((s) => !indexSet.has(norm(s.symbol)))
      .slice(0, N)
      .map((s) => {
        const b = latestMap.get(norm(s.symbol));
        return {
          symbol: s.symbol,
          close: b?.close ?? "NaN",       // PopularTickers can format or show —
          timestamp: formatTimestamp(b?.timestamp),
        };
      });
  }, [state]);

  const boardRows = useMemo(() => {
    if (state.kind !== "ready") return [];
    const norm = (s: string) => s.trim().toUpperCase();
    const latestMap = new Map(state.latest.map((b) => [norm(b.symbol), b]));
    const indexSet = new Set(INDEX_SYMBOLS.map((x) => norm(x.symbol)));

    const rows = dedupe([...INDEX_SYMBOLS.map((x) => x.symbol), ...state.symbols.map((s) => s.symbol)]).map(
      (symbol) => {
        const item = latestMap.get(norm(symbol));
        const isIndex = indexSet.has(norm(symbol));
        return {
          symbol,
          group: isIndex ? "indexes" : "stocks",
          close: item?.close ?? "",
          timestamp: formatTimestamp(item?.timestamp),
        };
      }
    );

    const q = query.trim().toUpperCase();
    return rows
      .filter((r) => (tab === "all" ? true : r.group === tab))
      .filter((r) => (!q ? true : r.symbol.includes(q)))
      .sort((a, b) => a.symbol.localeCompare(b.symbol));
  }, [state, tab, query]);



  return (
    <div className="space-y-6">
      <div className="rounded-2xl border bg-gradient-to-br from-muted/40 via-background to-muted/10 p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              Markets
            </div>
            <div className="mt-1 text-2xl font-semibold tracking-tight">
              Market Pulse
            </div>
            <div className="mt-1 text-sm text-muted-foreground">
              Live-ish snapshots blended with your cached history.
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">Symbols: {symbolCount}</Badge>
            <Badge variant="outline">Priced: {pricedCount}</Badge>
            <Badge variant="secondary">Updated: {lastUpdated}</Badge>
          </div>
        </div>
      </div>

      {state.kind === "error" && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {state.message}
        </div>
      )}

      <div className="space-y-2">
        <div className="text-sm font-medium text-muted-foreground">Indexes</div>
        <IndexCards items={indexCards} />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium">Popular Tickers</CardTitle>
            <Badge variant="outline">Top {popularRows.length || 0}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {state.kind === "loading" && (
            <div className="text-sm text-muted-foreground">Loading…</div>
          )}
          {state.kind === "ready" && popularRows.length === 0 && (
            <div className="text-sm text-muted-foreground">
              No symbols returned. Check GET /symbols or your seed route.
            </div>
          )}
          {popularRows.length > 0 && <PopularTickers rows={popularRows} />}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle className="text-sm font-medium">Market Board</CardTitle>
            <div className="flex items-center gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter ticker..."
                className="h-9 w-[220px]"
              />
              <Button variant="outline" className="h-9" onClick={() => void refreshNow()} disabled={refreshing}>
                {refreshing ? "Refreshing..." : "Refresh"}
              </Button>
            </div>
          </div>
          <Tabs value={tab} onValueChange={(v) => setTab(v as "all" | "indexes" | "stocks")}>
            <TabsList variant="line">
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="indexes">Indexes</TabsTrigger>
              <TabsTrigger value="stocks">Stocks</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent>
          <div className="mb-3 flex items-center justify-between text-xs text-muted-foreground">
            <div>
              Showing <span className="font-medium text-foreground">{boardRows.length}</span> symbols
            </div>
            <div className="hidden md:block">Tip: click a ticker to open the asset page</div>
          </div>
          <div className="overflow-hidden rounded-xl border bg-muted/10">
            <div className="max-h-[460px] overflow-auto">
              <Table className="min-w-[720px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky top-0 z-10 bg-background/95 backdrop-blur">Symbol</TableHead>
                    <TableHead className="sticky top-0 z-10 bg-background/95 backdrop-blur">Group</TableHead>
                    <TableHead className="sticky top-0 z-10 bg-background/95 text-right backdrop-blur">Last</TableHead>
                    <TableHead className="sticky top-0 z-10 bg-background/95 text-right backdrop-blur">Time</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {boardRows.map((r) => (
                    <TableRow key={r.symbol} className="odd:bg-muted/25 hover:bg-accent/40">
                      <TableCell className="py-2.5 font-medium">
                        <Link href={`/asset/${encodeURIComponent(r.symbol)}`} className="hover:underline">
                          {displaySymbol(r.symbol)}
                        </Link>
                      </TableCell>
                      <TableCell className="py-2.5 text-muted-foreground">{r.group}</TableCell>
                      <TableCell className="py-2.5 text-right tabular-nums">{formatUsd(r.close)}</TableCell>
                      <TableCell className="py-2.5 text-right text-muted-foreground tabular-nums">{r.timestamp}</TableCell>
                    </TableRow>
                  ))}
                  {state.kind === "ready" && boardRows.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-sm text-muted-foreground">
                        No symbols match the current filter.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function dedupe(xs: string[]) {
  return Array.from(new Set(xs.map((s) => s.trim().toUpperCase()).filter(Boolean)));
}

function formatUsd(v: string) {
  if (!v || !String(v).trim()) return "$—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "$—";
  return `$${n.toFixed(2)}`;
}

function formatTimestamp(ts?: string | null) {
  if (!ts) return "—";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
}

function displaySymbol(symbol: string) {
  return symbol.replace(/^\^/, "");
}

function wsBaseUrl() {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.hostname}:8000`;
}
