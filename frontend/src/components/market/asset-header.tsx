"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import type { PriceBarRead } from "@/lib/types";

export function AssetHeader(props: { symbol: string }) {
  const symbol = props.symbol.toUpperCase();
  const display = displaySymbol(symbol);
  const [latest, setLatest] = useState<PriceBarRead | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setErr(null);
    setLatest(null);

    api.refreshLatestPrice(symbol)
      .then(setLatest)
      .catch((e) => setErr(e instanceof Error ? e.message : "Failed to load price"));
  }, [symbol]);

  const close = latest ? Number((latest as any).close) : null;

  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <div className="flex items-center gap-2">
          <div className="text-xl font-semibold tracking-tight">{display}</div>
          <Badge variant="secondary">{err ? "Error" : latest ? "Live" : "Loading"}</Badge>
        </div>

        <div className="mt-1 flex items-baseline gap-3">
          <div className="text-2xl font-semibold">
            {close !== null && Number.isFinite(close) ? `$${close.toFixed(2)}` : "$—"}
          </div>
          <div className="text-sm text-muted-foreground">
            {latest ? `as of ${formatTimestamp((latest as any).timestamp ?? (latest as any).ts)}` : ""}
          </div>
        </div>

        {err && <div className="mt-2 text-sm text-rose-500">{err}</div>}
      </div>

      <div className="text-right">
        <div className="text-xs text-muted-foreground">Source</div>
        <div className="text-sm font-medium">/prices/latest</div>
      </div>
    </div>
  );
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
