import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function WatchlistsPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="text-lg font-semibold">Watchlists</div>
        <div className="text-sm text-muted-foreground">
          Track symbols you care about (UI scaffold).
        </div>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Default Watchlist</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Add watchlist CRUD later; this is the layout foundation.
        </CardContent>
      </Card>
    </div>
  );
}
