"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useSession } from "@/components/shell/session-provider";
import type { AccountSummary, PositionRead } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const { accountId } = useSession();
  const [summary, setSummary] = useState<AccountSummary | null>(null);
  const [positions, setPositions] = useState<PositionRead[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [showClosedPositions, setShowClosedPositions] = useState(false);
  const [sparklines, setSparklines] = useState<Record<string, number[]>>({});

  useEffect(() => {
    let cancelled = false;
    setErr(null);
    setSummary(null);
    setPositions(null);

    if (!accountId) return;

    const loadDashboard = async () => {
      try {
        const pos = await api.getPositions(accountId);
        const symbolsToRefresh = Array.from(
          new Set(
            pos
              .filter((p) => Number(p.quantity) !== 0)
              .map((p) => String(p.symbol).trim().toUpperCase())
              .filter(Boolean)
          )
        );

        // Keep dashboard valuations current by refreshing held symbols before summary.
        if (symbolsToRefresh.length > 0) {
          await api.latestBulk(symbolsToRefresh, { force: true });
        }

        const s = await api.getSummary(accountId);

        if (cancelled) return;
        setPositions(pos);
        setSummary(s);
      } catch (e) {
        if (cancelled) return;
        setErr(e instanceof Error ? e.message : "Failed to load dashboard");
      }
    };

    void loadDashboard();
    const t = window.setInterval(() => {
      void loadDashboard();
    }, 15000);

    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [accountId]);

  const metrics = useMemo(() => {
    if (!summary) return null;
    return [
      {
        title: "Cash",
        value: formatMoney(summary.cash),
        hint: "Available buying power",
        accent: "from-emerald-500/45 to-transparent",
      },
      {
        title: "Equity",
        value: formatMoney(summary.equity),
        hint: "Cash + marked holdings",
        accent: "from-sky-500/45 to-transparent",
      },
      {
        title: "Unrealized PnL",
        value: formatMoney(summary.unrealized_pnl),
        hint: "Open-position gain/loss",
        accent: Number(summary.unrealized_pnl) >= 0 ? "from-emerald-500/45 to-transparent" : "from-rose-500/45 to-transparent",
      },
      {
        title: "Positions",
        value: String(Object.keys(summary.positions ?? {}).length),
        hint: "Open symbols tracked",
        accent: "from-violet-500/45 to-transparent",
      },
    ];
  }, [summary]);

  const visiblePositions = useMemo(() => {
    if (!positions) return null;
    if (showClosedPositions) return positions;
    return positions.filter((p) => Number(p.quantity) !== 0);
  }, [positions, showClosedPositions]);

  useEffect(() => {
    if (!visiblePositions || visiblePositions.length === 0) {
      setSparklines({});
      return;
    }

    let cancelled = false;
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 30);

    (async () => {
      const entries = await Promise.all(
        visiblePositions.map(async (p) => {
          try {
            const rows = await api.getHistory({
              symbol: p.symbol,
              start: toYmd(start),
              end: toYmd(end),
            });
            const closes = rows
              .map((r) => Number(r.close))
              .filter((v) => Number.isFinite(v))
              .slice(-30);
            return [p.symbol, closes] as const;
          } catch {
            return [p.symbol, []] as const;
          }
        })
      );

      if (cancelled) return;
      setSparklines(Object.fromEntries(entries));
    })();

    return () => {
      cancelled = true;
    };
  }, [visiblePositions]);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-lg font-semibold">Dashboard</div>
        <div className="text-sm text-muted-foreground">
          Enter your account_id in the top bar to load real data.
        </div>
      </div>

      {!accountId && (
        <div className="rounded-md border p-4 text-sm text-muted-foreground">
          No account selected. Set <span className="font-medium">account_id</span> in the top bar.
        </div>
      )}

      {err && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {err}
        </div>
      )}

      <div className="grid items-stretch gap-4 lg:h-[calc(100vh-11rem)] lg:grid-cols-3">
        <div className="grid gap-3 lg:col-span-1 lg:grid-rows-4">
          {metrics &&
            metrics.map((m) => <Metric key={m.title} title={m.title} value={m.value} hint={m.hint} accent={m.accent} />)}
        </div>

        <Card className="overflow-hidden lg:col-span-2 lg:h-full">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">Positions</CardTitle>
              <Button
                type="button"
                variant={showClosedPositions ? "default" : "outline"}
                className="h-8 text-xs"
                onClick={() => setShowClosedPositions((v) => !v)}
              >
                {showClosedPositions ? "Showing Closed" : "Hide Closed"}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="text-sm flex-1 min-h-0 overflow-hidden">
            {!positions && accountId && !err && (
              <div className="text-muted-foreground">Loading positions...</div>
            )}

            {visiblePositions && visiblePositions.length === 0 && (
              <div className="text-muted-foreground">No positions.</div>
            )}

            {visiblePositions && visiblePositions.length > 0 && (
              <div className="h-full max-h-full space-y-1.5 overflow-y-auto pr-1">
                {visiblePositions.map((p) => {
                  const summaryPos = findSummaryPosition(summary, p.symbol);
                  return (
                  <div key={p.id} className="grid gap-1 rounded-md border px-3 py-1.5 md:grid-cols-[1.2fr,160px]">
                    <div className="space-y-0.5 pt-1">
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/asset/${encodeURIComponent(p.symbol)}`}
                          className="font-medium hover:underline"
                        >
                          {p.symbol}
                        </Link>
                        <span className="rounded-full border px-2 py-0.5 text-[10px] text-muted-foreground">
                          {formatQty(p.quantity)} shares
                        </span>
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        Avg {formatMoney(p.average_price)}
                          {summaryPos
                            ? ` • Mark ${formatMoney(String(summaryPos.mark_price))}`
                            : ""}
                      </div>
                    </div>

                    <div className="space-y-0.5">
                      <PositionSparkline
                        values={sparklines[p.symbol] ?? []}
                        positive={positionUnrealized(summary, p.symbol) >= 0}
                      />
                      <div className="text-right">
                        <div className="text-[11px] text-muted-foreground">Unrealized PnL</div>
                        <div
                          className={`text-sm font-semibold ${
                            positionUnrealized(summary, p.symbol) >= 0 ? "text-emerald-600" : "text-rose-600"
                          }`}
                        >
                          {formatMoney(String(positionUnrealized(summary, p.symbol)))}
                        </div>
                      </div>
                    </div>
                  </div>
                )})}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Metric(props: { title: string; value: string; hint: string; accent: string }) {
  const isNeg = props.title.toLowerCase().includes("pnl") && parseMaybeNumber(props.value) < 0;
  return (
    <Card className="relative h-full overflow-hidden">
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${props.accent}`} />
      <CardHeader className="pb-1">
        <CardTitle className="text-[11px] font-semibold tracking-[0.12em] text-muted-foreground uppercase">
          {props.title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <div className={`text-2xl font-semibold tabular-nums leading-none ${isNeg ? "text-rose-500" : ""}`}>
          {props.value}
        </div>
        <div className="text-[11px] text-muted-foreground">{props.hint}</div>
      </CardContent>
    </Card>
  );
}

function parseMaybeNumber(v: string) {
  const cleaned = String(v).replace(/[$,]/g, "");
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : 0;
}

function formatMoney(v: string) {
  const n = Number(v);
  if (!Number.isFinite(n)) return v;
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatQty(v: string) {
  const n = Number(v);
  if (!Number.isFinite(n)) return v;
  return n.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function toYmd(d: Date) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function positionUnrealized(summary: AccountSummary | null, symbol: string) {
  const raw = findSummaryPosition(summary, symbol)?.unrealized_pnl;
  const n = Number(raw ?? 0);
  return Number.isFinite(n) ? n : 0;
}

function findSummaryPosition(summary: AccountSummary | null, symbol: string) {
  if (!summary?.positions) return null;
  const target = String(symbol).trim().toUpperCase();
  const exact = summary.positions[target];
  if (exact) return exact;
  const key = Object.keys(summary.positions).find((k) => k.trim().toUpperCase() === target);
  return key ? summary.positions[key] : null;
}

function PositionSparkline(props: { values: number[]; positive: boolean }) {
  if (props.values.length < 2) {
    return <div className="ml-auto h-6 w-24 rounded-md bg-muted/40" />;
  }

  const w = 96;
  const h = 20;
  const pad = 0;
  const min = Math.min(...props.values);
  const max = Math.max(...props.values);
  const span = max - min || 1;
  const points = props.values
    .map((v, i) => {
      const x = pad + (i / Math.max(1, props.values.length - 1)) * (w - pad * 2);
      const y = pad + (1 - (v - min) / span) * (h - pad * 2);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="ml-auto h-6 w-24">
      <polyline
        points={points}
        fill="none"
        stroke={props.positive ? "#16a34a" : "#dc2626"}
        strokeWidth="2"
      />
    </svg>
  );
}
