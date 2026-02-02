"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type IndexCard = {
  label: string;
  symbol: string;
  price: string;
  ts?: string;
};

export function IndexCards(props: { items: IndexCard[]; loading?: boolean }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {props.items.map((it) => (
        <Card key={it.symbol}>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">
              {it.label}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-semibold">{it.price}</div>
            <div className="mt-1 text-xs text-muted-foreground">
              {it.symbol}
              {it.ts ? ` • ${it.ts}` : ""}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
