import type { TradeRead } from "@/lib/types";
export function tradeStats(trades: TradeRead[]) {
  const sorted = [...trades].sort((a, b) => new Date(a.executed_at).getTime() - new Date(b.executed_at).getTime() || a.id - b.id);
  let owned = 0, average = 0, realized = 0, wins = 0, sales = 0;
  for (const trade of sorted) {
    const count = Number(trade.quantity), price = trade.account_total != null && count > 0 ? Number(trade.account_total) / count : Number(trade.price) * Number(trade.fx_rate ?? 1);
    if (!(count > 0) || !Number.isFinite(price)) continue;
    if (trade.side === "BUY") { average = (owned * average + count * price) / (owned + count); owned += count; }
    else if (owned > 0) { const sold = Math.min(owned, count); const gain = sold * (price - average); realized += gain; sales += 1; if (gain > 0) wins += 1; owned -= sold; if (!owned) average = 0; }
  }
  return { realized, sales, winRate: sales ? wins / sales * 100 : null };
}
