"use client";

import { money } from "@/lib/format";
import type { PriceRangeDays, PriceRangeRead } from "@/lib/types";

const periodNames: Record<PriceRangeDays, string> = {
  7: "1-week", 30: "1-month", 90: "3-month", 180: "6-month", 365: "1-year",
};

function limitPrice(value: string, currency: string) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0 || (currency === "VND" && !Number.isInteger(number))) return null;
  const price = number.toFixed(currency === "VND" ? 0 : 2);
  return Number(price) > 0 ? price : null;
}

function dateLabel(value: string) {
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric", timeZone: "UTC",
  });
}

export function LimitPriceReference({ symbol, currency, days, range, loading, onRetry, onChoose }: {
  symbol: string; currency: string; days: PriceRangeDays; range: PriceRangeRead | null;
  loading: boolean; onRetry: () => void; onChoose: (price: string) => void;
}) {
  const matches = range?.symbol === symbol.toUpperCase() && range.currency === currency
    && range.interval === "1d" && range.days === days;
  const low = matches ? limitPrice(range.low, currency) : null;
  const high = matches ? limitPrice(range.high, currency) : null;
  const valid = !!low && !!high && Number(low) <= Number(high);
  const period = periodNames[days];

  return <div className="l-limit-reference" aria-label={`${period} limit price shortcuts`}>
    {loading ? <p className="l-limit-reference-caption" role="status">Loading {period} range…</p>
      : valid && range ? <>
        <p className="l-limit-reference-caption">{period} range <span>{dateLabel(range.start_date)} – {dateLabel(range.end_date)}</span></p>
        <div className="l-limit-shortcuts">
          {([["Low", low], ["High", high]] as const).map(([label, price]) => <button key={label} type="button"
            aria-label={`Use ${period} ${label.toLowerCase()} of ${money(price, undefined, currency)} as limit price`}
            onClick={() => onChoose(price!)}>
            <span>{label}</span><strong>{money(price, undefined, currency)}</strong>
          </button>)}
        </div>
      </> : <div className="l-limit-reference-error" role="status"><span>Range prices unavailable.</span><button type="button" onClick={onRetry}>Retry</button></div>}
  </div>;
}
