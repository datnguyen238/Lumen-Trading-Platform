"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useSession } from "@/components/shell/session-provider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

type Side = "BUY" | "SELL";

export function OrderTicket(props: { symbol: string; onOrderPlaced?: () => void }) {
  const { accountId } = useSession();
  const symbol = props.symbol.toUpperCase();

  const [side, setSide] = useState<Side>("BUY");
  const [qty, setQty] = useState<string>("1");
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const canSubmit = useMemo(() => {
    const q = Number(qty);
    return !!accountId && Number.isFinite(q) && q > 0;
  }, [qty, accountId]);

  async function submit() {
    if (!canSubmit || !accountId) return;
    setSubmitting(true);
    setMsg(null);

    try {
      const q = Number(qty);
      const order = await api.placeMarketOrder({
        account_id: accountId,
        symbol,
        side,
        order_type: "MARKET",
        quantity: q,
      });

      setMsg(`Order placed: ${order.side} ${order.symbol} x ${order.quantity}`);
      props.onOrderPlaced?.();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Order failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Order Ticket</CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {!accountId && (
          <div className="rounded-md border p-3 text-sm text-muted-foreground">
            Set <span className="font-medium">account_id</span> in the top bar to trade.
          </div>
        )}

        <div className="grid grid-cols-2 gap-2">
          <Button variant={side === "BUY" ? "default" : "outline"} onClick={() => setSide("BUY")}>
            Buy
          </Button>
          <Button variant={side === "SELL" ? "default" : "outline"} onClick={() => setSide("SELL")}>
            Sell
          </Button>
        </div>

        <div className="space-y-2">
          <Label>Quantity</Label>
          <Input value={qty} onChange={(e) => setQty(e.target.value)} inputMode="decimal" />
        </div>

        <Button className="w-full" disabled={!canSubmit || submitting} onClick={submit}>
          {submitting ? "Placing..." : "Place Market Order"}
        </Button>

        {msg && (
          <div className="text-sm text-muted-foreground">
            {msg}
          </div>
        )}

        <div className="text-xs text-muted-foreground">
          Endpoint: <span className="font-medium">POST /orders/market</span> (fills at latest close)
        </div>
      </CardContent>
    </Card>
  );
}
