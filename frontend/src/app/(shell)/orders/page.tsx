import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function OrdersPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="text-lg font-semibold">Orders</div>
        <div className="text-sm text-muted-foreground">
          Open orders and history (UI scaffold).
        </div>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Open Orders</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          No orders yet.
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Order History</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          History will show here once wired to your backend.
        </CardContent>
      </Card>
    </div>
  );
}
