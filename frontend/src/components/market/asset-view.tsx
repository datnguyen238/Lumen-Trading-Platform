"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { PriceBarRead } from "@/lib/types";
import { AssetHeader } from "@/components/market/asset-header";
import { PriceChart } from "@/components/market/price-chart";
import { AssetOverview } from "@/components/market/asset-overview";
import { OrderTicket } from "@/components/market/order-ticket";

export function AssetView(props: { symbol: string }) {
  const symbol = props.symbol.toUpperCase();
  const [latest, setLatest] = useState<PriceBarRead | null>(null);
  const [latestErr, setLatestErr] = useState<string | null>(null);
  const [latestLoading, setLatestLoading] = useState(true);
  const [refreshNonce, setRefreshNonce] = useState(0);

  const refreshLatest = useCallback(async () => {
    setLatestLoading(true);
    try {
      const row = await api.refreshLatestPrice(symbol);
      setLatest(row);
      setLatestErr(null);
    } catch (e) {
      setLatestErr(e instanceof Error ? e.message : "Failed to load price");
    } finally {
      setLatestLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    void refreshLatest();
  }, [refreshLatest]);

  function onOrderPlaced() {
    setRefreshNonce((n) => n + 1);
    void refreshLatest();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <AssetHeader symbol={symbol} latest={latest} loading={latestLoading} err={latestErr} />

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Chart</CardTitle>
          </CardHeader>
          <CardContent>
            <PriceChart symbol={symbol} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <AssetOverview symbol={symbol} latestOverride={latest} refreshNonce={refreshNonce} />
          </CardContent>
        </Card>
      </div>

      <div className="space-y-6">
        <OrderTicket symbol={symbol} onOrderPlaced={onOrderPlaced} />
      </div>
    </div>
  );
}
