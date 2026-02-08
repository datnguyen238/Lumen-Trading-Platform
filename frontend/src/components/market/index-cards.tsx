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
        <Card key={it.symbol} className="relative overflow-hidden">
          <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-foreground/70 via-foreground/20 to-transparent" />
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
              {it.label}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold tracking-tight">{it.price}</div>
            <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
              <span className="rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.15em]">
                {it.symbol}
              </span>
              <span>{it.ts ? it.ts : "—"}</span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
