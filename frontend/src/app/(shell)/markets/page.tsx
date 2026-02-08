"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { IndexCards } from "@/components/market/index-cards";
import { PopularTickers } from "@/components/market/popular-tickers";
import type { BulkLatestItem, SymbolItem } from "@/lib/types";

type UiState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; symbols: SymbolItem[]; latest: BulkLatestItem[] }
  | { kind: "error"; message: string };

const INDEX_SYMBOLS = [
  { label: "S&P 500", symbol: "SPY" },
  { label: "NASDAQ", symbol: "QQQ" },
  { label: "VIX Proxy", symbol: "VIXY" },
];

export default function MarketsPage() {
  const [state, setState] = useState<UiState>({ kind: "idle" });

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

  const requested = useMemo(() => {
    if (state.kind !== "ready") return [];
    return dedupe([
      ...INDEX_SYMBOLS.map((x) => x.symbol),
      ...state.symbols.map((s) => s.symbol),
    ]);
  }, [state.kind, state.kind === "ready" ? state.symbols : null]);

  // WS live updates disabled (rate limits / entitlement issues)



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




  return (
    <div className="space-y-6">
      <div>
        <div className="text-lg font-semibold">Markets</div>
        <div className="text-sm text-muted-foreground">
          Loads symbols, seeds defaults if needed, then fetches latest prices in bulk.
        </div>
      </div>

      {state.kind === "error" && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {state.message}
        </div>
      )}

      <IndexCards items={indexCards} />

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Popular Tickers</CardTitle>
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
    </div>
  );
}

function dedupe(xs: string[]) {
  return Array.from(new Set(xs.map((s) => s.trim().toUpperCase()).filter(Boolean)));
}

function formatUsd(v: string) {
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
