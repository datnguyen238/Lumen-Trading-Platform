"use client";

import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import { ErrorNotice } from "./common";

export function DailyPriceDetails({ symbol, currency }: { symbol: string; currency: string | null }) {
  const [open, setOpen] = useState(false);
  const daily = useResource(`daily-price:${symbol}:${currency}:${open}`, useCallback(
    () => open ? api.getDailyPrice(symbol) : Promise.resolve(null), [open, symbol]));
  const bar = daily.data?.currency === currency && currency ? daily.data : null;
  const sessionDate = bar ? new Date(`${bar.session_date}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric", timeZone: "UTC",
  }) : null;

  return <details className="l-price-details" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Price details</summary>
    {open && (daily.loading ? <p className="l-daily-price-period" role="status">Loading daily prices…</p>
      : bar ? <>
        <p className="l-daily-price-period">Daily prices · {sessionDate}</p>
        <dl className="l-chart-stats">{(["open", "high", "low", "close"] as const).map(field => <div key={field}>
          <dt>{field[0].toUpperCase() + field.slice(1)}</dt><dd>{money(bar[field], undefined, currency)}</dd>
        </div>)}</dl>
      </> : <ErrorNotice message={daily.error || "Daily price details are unavailable. Refresh this investment or try again."} retry={daily.reload}/>)}
  </details>;
}
