"use client";

import Link from "next/link";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Row = {
  symbol: string;
  close: string;
  timestamp: string;
};

export function PopularTickers(props: { rows: Row[] }) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead className="text-right">Last</TableHead>
            <TableHead className="text-right">Time</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {props.rows.map((r) => (
            <TableRow key={r.symbol} className="odd:bg-muted/30 hover:bg-accent/50">
              <TableCell className="font-medium">
                <Link href={`/asset/${encodeURIComponent(r.symbol)}`} className="hover:underline">
                  {displaySymbol(r.symbol)}
                </Link>
              </TableCell>
              <TableCell className="text-right tabular-nums">{formatPrice(r.close)}</TableCell>
              <TableCell className="text-right text-muted-foreground tabular-nums">
                {r.timestamp}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function formatPrice(v: string) {
  const n = Number(v);
  if (!Number.isFinite(n)) return v;
  if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return n.toFixed(2);
}

function displaySymbol(symbol: string) {
  return symbol.replace(/^\^/, "");
}
