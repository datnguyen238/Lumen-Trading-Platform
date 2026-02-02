import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

const movers = [
  { symbol: "AAPL", price: 182.12, changePct: 0.8, tag: "Large Cap" },
  { symbol: "TSLA", price: 210.55, changePct: -1.4, tag: "EV" },
  { symbol: "BTCUSDT", price: 45000, changePct: 2.1, tag: "Crypto" },
  { symbol: "ETHUSDT", price: 2400, changePct: -0.6, tag: "Crypto" },
];

export function MarketsTable() {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead>Tag</TableHead>
            <TableHead className="text-right">Last</TableHead>
            <TableHead className="text-right">Change</TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {movers.map((r) => (
            <TableRow key={r.symbol} className="hover:bg-accent/50">
              <TableCell className="font-medium">
                <Link
                  href={`/asset/${encodeURIComponent(r.symbol)}`}
                  className="hover:underline"
                >
                  {r.symbol}
                </Link>
              </TableCell>

              <TableCell>
                <Badge variant="secondary">{r.tag}</Badge>
              </TableCell>

              <TableCell className="text-right">{formatPrice(r.price)}</TableCell>

              <TableCell
                className={`text-right ${
                  r.changePct >= 0 ? "text-emerald-500" : "text-rose-500"
                }`}
              >
                {r.changePct >= 0 ? "+" : ""}
                {r.changePct.toFixed(2)}%
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function formatPrice(n: number) {
  if (n >= 1000) {
    return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return n.toFixed(2);
}
