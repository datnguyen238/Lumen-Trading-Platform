"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useSession } from "@/components/shell/session-provider";
import type { AccountSummary, PositionRead } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function DashboardPage() {
  const { accountId } = useSession();
  const [summary, setSummary] = useState<AccountSummary | null>(null);
  const [positions, setPositions] = useState<PositionRead[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setErr(null);
    setSummary(null);
    setPositions(null);

    if (!accountId) return;

    (async () => {
      try {
        // Summary might not exist yet; positions should.
        const [pos] = await Promise.all([api.getPositions(accountId)]);
        setPositions(pos);

        try {
          const s = await api.getSummary(accountId);
          setSummary(s);
        } catch {
          // ignore if not implemented yet
        }
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Failed to load dashboard");
      }
    })();
  }, [accountId]);

  const metrics = useMemo(() => {
    if (!summary) return null;
    return [
      { title: "Cash", value: summary.cash },
      { title: "Equity", value: summary.equity },
      { title: "Unrealized PnL", value: summary.unrealized_pnl },
      { title: "Positions", value: String(Object.keys(summary.positions ?? {}).length) },
    ];
  }, [summary]);

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

      {metrics && (
        <div className="grid gap-4 md:grid-cols-4">
          {metrics.map((m) => (
            <Metric key={m.title} title={m.title} value={m.value} />
          ))}
        </div>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Positions</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {!positions && accountId && !err && (
            <div className="text-muted-foreground">Loading positions...</div>
          )}

          {positions && positions.length === 0 && (
            <div className="text-muted-foreground">No positions.</div>
          )}

          {positions && positions.length > 0 && (
            <div className="space-y-2">
              {positions.map((p) => (
                <div key={p.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                  <div className="font-medium">{p.symbol}</div>
                  <div className="text-muted-foreground">
                    qty {p.quantity} @ avg {p.average_price}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric(props: { title: string; value: string }) {
  const isNeg = props.title.toLowerCase().includes("pnl") && Number(props.value) < 0;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs text-muted-foreground">{props.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-lg font-semibold ${isNeg ? "text-rose-500" : ""}`}>
          {props.value}
        </div>
      </CardContent>
    </Card>
  );
}
