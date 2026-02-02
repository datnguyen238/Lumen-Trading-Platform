import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const rows = [
  { symbol: "AAPL", qty: 10, avg: 170.25, last: 182.12, dayPct: 0.8 },
  { symbol: "TSLA", qty: 3, avg: 220.0, last: 210.55, dayPct: -1.4 },
  { symbol: "NVDA", qty: 5, avg: 850.0, last: 910.4, dayPct: 1.1 },
];

export function HoldingsTable() {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead className="text-right">Qty</TableHead>
            <TableHead className="text-right">Avg</TableHead>
            <TableHead className="text-right">Last</TableHead>
            <TableHead className="text-right">Day</TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.symbol} className="hover:bg-accent/50">
              <TableCell className="font-medium">
                <Link
                  href={`/asset/${encodeURIComponent(r.symbol)}`}
                  className="hover:underline"
                >
                  {r.symbol}
                </Link>
              </TableCell>
              <TableCell className="text-right">{r.qty}</TableCell>
              <TableCell className="text-right">{r.avg.toFixed(2)}</TableCell>
              <TableCell className="text-right">{r.last.toFixed(2)}</TableCell>
              <TableCell
                className={`text-right ${
                  r.dayPct >= 0 ? "text-emerald-500" : "text-rose-500"
                }`}
              >
                {r.dayPct >= 0 ? "+" : ""}
                {r.dayPct.toFixed(2)}%
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
