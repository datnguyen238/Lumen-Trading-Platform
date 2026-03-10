"use client";

import { Badge } from "@/components/ui/badge";
import type { PriceBarRead } from "@/lib/types";

export function AssetHeader(props: {
  symbol: string;
  latest: PriceBarRead | null;
  loading: boolean;
  err: string | null;
}) {
  const symbol = props.symbol.toUpperCase();
  const display = displaySymbol(symbol);
  const close = props.latest ? Number(props.latest.close) : null;

  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <div className="flex items-center gap-2">
          <div className="text-xl font-semibold tracking-tight">{display}</div>
          <Badge variant="secondary">{props.err ? "Error" : props.latest ? "Live" : props.loading ? "Loading" : "—"}</Badge>
        </div>

        <div className="mt-1 flex items-baseline gap-3">
          <div className="text-2xl font-semibold">
            {close !== null && Number.isFinite(close) ? `$${close.toFixed(2)}` : "$—"}
          </div>
          <div className="text-sm text-muted-foreground">
            {props.latest ? `as of ${formatTimestamp(props.latest.timestamp)}` : ""}
          </div>
        </div>

        {props.err && <div className="mt-2 text-sm text-rose-500">{props.err}</div>}
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
