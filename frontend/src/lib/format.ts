export function money(value: unknown, digits?: number, currency: string | null = "USD") {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  if (!currency || !/^[A-Z]{3}$/.test(currency)) return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: digits ?? 6 }).format(number)}${currency ? ` ${currency}` : ""}`;
  return new Intl.NumberFormat("en-US", { style: "currency", currency, ...(digits === undefined ? {} : { minimumFractionDigits: digits, maximumFractionDigits: digits }) }).format(number);
}
export function quantity(value: unknown) { return new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 }).format(Number(value) || 0); }
export function signedMoney(value: unknown, currency: string | null = "USD") { if (value == null || value === "") return "—"; const number = Number(value); return `${number > 0 ? "+" : ""}${money(number, undefined, currency)}`; }
export function percent(value: number, signed = false) { return Number.isFinite(value) ? `${signed && value > 0 ? "+" : ""}${value.toFixed(2)}%` : "—"; }
export function timestamp(value?: string | null) {
  if (!value) return "Time unavailable";
  const date = new Date(/(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`);
  return Number.isFinite(date.getTime()) ? date.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" }) : "Time unavailable";
}
export function errorMessage(error: unknown) { return error instanceof TypeError ? "We couldn’t reach Lumen. Check your connection and try again." : error instanceof Error ? error.message : "Something went wrong. Please try again."; }
export function assetUrl(symbol: string) { return `/asset/${encodeURIComponent(symbol.trim().toUpperCase())}`; }
export function ymd(date: Date) { return date.toISOString().slice(0, 10); }
export function capitalizeFirst(value: string) { return value.replace(/^(\s*)(\p{L})/u, (_, space: string, letter: string) => space + letter.toUpperCase()); }
export const assetNames: Record<string, string> = { AAPL: "Apple", MSFT: "Microsoft", NVDA: "NVIDIA", GOOGL: "Alphabet", AMZN: "Amazon", META: "Meta Platforms", TSLA: "Tesla", SPY: "SPDR S&P 500 ETF", QQQ: "Invesco QQQ", DIA: "SPDR Dow Jones ETF", VOO: "Vanguard S&P 500 ETF", AMD: "Advanced Micro Devices", NFLX: "Netflix", JPM: "JPMorgan Chase", "BRK-B": "Berkshire Hathaway", IWM: "iShares Russell 2000 ETF", VIXY: "ProShares VIX ETF" };
