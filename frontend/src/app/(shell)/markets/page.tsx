import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MarketsTable } from "@/components/market/markets-table";

export default function MarketsPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="text-lg font-semibold">Markets</div>
        <div className="text-sm text-muted-foreground">
          Movers and symbol discovery (mocked).
        </div>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Top Movers</CardTitle>
        </CardHeader>
        <CardContent>
          <MarketsTable />
        </CardContent>
      </Card>
    </div>
  );
}
