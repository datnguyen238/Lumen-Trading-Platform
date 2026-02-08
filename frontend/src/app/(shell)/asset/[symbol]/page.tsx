import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AssetHeader } from "@/components/market/asset-header";
import { OrderTicket } from "@/components/market/order-ticket";
import { PriceChart } from "@/components/market/price-chart";

export default async function AssetPage(props: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol: rawSymbol } = await props.params;
  const symbol = safeDecode(rawSymbol);

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <AssetHeader symbol={symbol} />

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
          <CardContent className="text-sm text-muted-foreground">
            Stats / description placeholder.
          </CardContent>
        </Card>
      </div>

      <div className="space-y-6">
        <OrderTicket symbol={symbol} />
      </div>
    </div>
  );
}

function safeDecode(value: string) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
