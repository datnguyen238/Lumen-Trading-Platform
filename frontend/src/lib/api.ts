import type {
  AccountRead,
  AccountSummary,
  Health,
  MarketOrderRequest,
  OrderRead,
  PositionRead,
  PriceBarRead,
  UserRead,
} from "@/lib/types";
import type { BulkLatestItem, SymbolItem } from "@/lib/types";



const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options?.headers ?? {}),
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  const text = await res.text();
  const body = text ? safeJsonParse(text) : null;

  if (!res.ok) {
    throw new ApiError(
      `Request failed: ${res.status} ${res.statusText}`,
      res.status,
      body
    );
  }
  return body as T;
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export const api = {
  // Health
  health: () => request<Health>("/health"),

  // Users
  createUser: (body: { email: string; full_name: string }) =>
    request<UserRead>("/users/", { method: "POST", body: JSON.stringify(body) }),
  getUser: (userId: number) => request<UserRead>(`/users/${userId}`),

  // Accounts
  createAccount: (body: { user_id: number; name: string }) =>
    request<AccountRead>("/accounts/", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getAccount: (accountId: number) =>
    request<AccountRead>(`/accounts/${accountId}`),
  getPositions: (accountId: number) =>
    request<PositionRead[]>(`/accounts/${accountId}/positions`),

  // Summary (you said “recommended additions”; if it exists, we’ll use it)
  getSummary: (accountId: number) =>
    request<AccountSummary>(`/accounts/${accountId}/summary`),

  // Prices
  getLatestPrice: (symbol: string) =>
    request<PriceBarRead>(`/prices/latest?symbol=${encodeURIComponent(symbol)}`),
  refreshLatestPrice: (symbol: string) =>
    request<PriceBarRead>(`/prices/refresh?symbol=${encodeURIComponent(symbol)}`, {
      method: "POST",
    }),

  getHistory: (params: { symbol: string; start: string; end: string }) => {
    const q = new URLSearchParams({
      symbol: params.symbol,
      start: params.start,
      end: params.end,
    });
    return request<PriceBarRead[]>(`/prices/history?${q.toString()}`);
  },

  loadStock: (body: { symbol: string; start: string; end: string; interval: string }) =>
    request<{ message: string }>("/prices/load/stock", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  loadCrypto: (body: { symbol: string; interval: string; limit: number }) =>
    request<{ message: string }>("/prices/load/crypto", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Orders
  placeMarketOrder: (body: MarketOrderRequest) =>
    request<OrderRead>("/orders/market", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Optional (if/when you add them)
  getOrders: (accountId: number) =>
    request<OrderRead[]>(`/accounts/${accountId}/orders`),
  getTrades: (accountId: number) =>
    request<any[]>(`/accounts/${accountId}/trades`),

    // Symbols + seeding
  getSymbols: () => request<SymbolItem[]>("/symbols"),
  seedDefaultWatchlist: () =>
    request<{ message: string }>("/seed/default-watchlist", { method: "POST" }),

  // Bulk latest prices
  // Bulk latest prices (backend expects a raw JSON array: ["AAPL","MSFT"])
  latestBulk: (symbols: string[]) =>
    request<BulkLatestItem[]>("/prices/latest/bulk", {
      method: "POST",
      body: JSON.stringify(symbols),
    }),

  // Symbols
  addSymbol: (body: { symbol: string }) =>
    request<SymbolItem>("/symbols/add", {
      method: "POST",
      body: JSON.stringify(body),
    }),


};
