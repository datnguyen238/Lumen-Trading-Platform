"use client";

import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import { api } from "@/lib/api";
import type { PriceBarRead } from "@/lib/types";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

type RangeKey = "1W" | "1M" | "3M" | "6M" | "1Y";
const RANGES: { key: RangeKey; label: string; days: number }[] = [
  { key: "1W", label: "1W", days: 7 },
  { key: "1M", label: "1M", days: 30 },
  { key: "3M", label: "3M", days: 90 },
  { key: "6M", label: "6M", days: 180 },
  { key: "1Y", label: "1Y", days: 365 },
];

type UiState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; data: PriceBarRead[] }
  | { kind: "error"; message: string };

export function PriceChart(props: { symbol: string }) {
  const symbol = props.symbol.toUpperCase();
  const [range, setRange] = useState<RangeKey>("1M");
  const [state, setState] = useState<UiState>({ kind: "idle" });

  useEffect(() => {
    let cancelled = false;
    const r = RANGES.find((x) => x.key === range) ?? RANGES[2];
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - r.days);

    setState({ kind: "loading" });
    api.getHistory({ symbol, start: toYmd(start), end: toYmd(end) })
      .then((data) => {
        if (cancelled) return;
        setState({ kind: "ready", data });
      })
      .catch((e) => {
        if (cancelled) return;
        setState({
          kind: "error",
          message: e instanceof Error ? e.message : "Failed to load chart",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, range]);

  const series = useMemo(() => {
    if (state.kind !== "ready") return [];
    return [...state.data]
      .sort(
        (a, b) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      )
      .map((b) => ({
        ts: new Date(b.timestamp).getTime(),
        close: Number(b.close),
        open: Number(b.open),
        high: Number(b.high),
        low: Number(b.low),
      }))
      .filter((p) => Number.isFinite(p.close) && Number.isFinite(p.ts));
  }, [state]);

  const last = series.length > 0 ? series[series.length - 1] : null;

  const chartConfig = useMemo(
    () =>
      ({
        close: { label: "Close", color: "var(--chart-1)" },
      }) satisfies ChartConfig,
    []
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {RANGES.map((r) => (
          <button
            key={r.key}
            onClick={() => setRange(r.key)}
            className={`rounded-md border px-2 py-1 text-xs ${
              range === r.key
                ? "border-foreground bg-foreground text-background"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      {state.kind === "loading" && (
        <div className="text-sm text-muted-foreground">Loading chart…</div>
      )}
      {state.kind === "error" && (
        <div className="text-sm text-rose-500">{state.message}</div>
      )}

      {state.kind === "ready" && series.length === 0 && (
        <div className="text-sm text-muted-foreground">No data for this range.</div>
      )}

      {state.kind === "ready" && series.length > 0 && (
        <div className="space-y-2">
          <ChartContainer config={chartConfig} className="h-64 w-full">
            <LineChart data={series} margin={{ left: 12, right: 12 }}>
              <CartesianGrid vertical={false} />
              <YAxis
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                width={72}
                domain={["auto", "auto"]}
                tickFormatter={(value) => fmtAxisPrice(Number(value))}
              />
              <XAxis
                dataKey="ts"
                type="number"
                scale="time"
                domain={["dataMin", "dataMax"]}
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                minTickGap={32}
                tickFormatter={(value) => formatAxisDate(Number(value), range)}
              />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    className="w-[160px]"
                    nameKey="close"
                    labelFormatter={(value) => formatTooltipDate(Number(value))}
                  />
                }
              />
              <Line
                dataKey="close"
                type="linear"
                stroke="var(--color-close)"
                strokeWidth={2}
                dot={series.length === 1}
              />
            </LineChart>
          </ChartContainer>

          {last && (
            <div className="text-xs text-muted-foreground">
              O: {fmt(last.open)} H: {fmt(last.high)} L: {fmt(last.low)} C: {fmt(last.close)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function toYmd(d: Date) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function fmt(n: number) {
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(2);
}

function formatAxisDate(value: number, range: RangeKey) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  if (range === "1W" || range === "1M" || range === "3M") {
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }
  return d.toLocaleDateString(undefined, { month: "short", year: "2-digit" });
}

function formatTooltipDate(value: number) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function fmtAxisPrice(value: number) {
  if (!Number.isFinite(value)) return "—";
  if (value >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return value.toFixed(2);
}
