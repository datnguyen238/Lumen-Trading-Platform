import type {
  AuthRead,
  AccountCurrency,
  AccountOverview,
  PreviewRequest,
  OrderPreview,
  OrderRequest,
  AccountRead,
  AccountSummary,
  Health,
  MarketOrderRequest,
  OrderRead,
  PositionRead,
  PriceBarRead,
  TradeRead,
  UserRead,
} from "@/lib/types";
import type { BulkLatestItem, SymbolItem } from "@/lib/types";



const BASE_URL = "/api";
let csrfToken: string | null = null;
export function setCsrfToken(value: string | null) { csrfToken = value; }

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
    credentials: "include",
    headers: {
      ...(options?.headers ?? {}),
      "Content-Type": "application/json",
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    },
    cache: "no-store",
  });

  const text = await res.text();
  const body = text ? safeJsonParse(text) : null;

  if (!res.ok) {
    if (res.status === 401 && !path.startsWith("/auth/")) window.dispatchEvent(new Event("lumen-auth-expired"));
    throw new ApiError(
      typeof body === "object" && body && "detail" in body && typeof body.detail === "string"
        ? body.detail
        : typeof body === "object" && body && "detail" in body && Array.isArray(body.detail)
          ? body.detail.map((issue: { loc?: string[]; msg?: string }) => `${issue.loc?.at(-1)?.replaceAll("_", " ") || "Input"}: ${issue.msg || "Check this value"}`).join(". ")
          : `The request could not be completed (${res.status}). Please try again.`,
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
  getOverview: (id: number) => request<AccountOverview>(`/accounts/${id}/overview`),
  previewOrder: (body: PreviewRequest) => request<OrderPreview>("/orders/preview", { method: "POST", body: JSON.stringify(body) }),
  confirmOrder: (previewId: string) => request<OrderRead>("/orders/confirm", { method: "POST", body: JSON.stringify({ preview_id: previewId }) }),
  getWatchlist: () => request<string[]>("/watchlist"),
  saveAsset: (symbol: string) => request<string[]>(`/watchlist/${encodeURIComponent(symbol)}`, { method: "PUT" }),
  removeAsset: (symbol: string) => request<string[]>(`/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" }),
  me: () => request<AuthRead>("/auth/me"),
  login: (body: { email: string; password: string }) => request<AuthRead>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  signup: (body: { email: string; password: string; full_name: string; currency: AccountCurrency }) => request<AuthRead>("/auth/signup", { method: "POST", body: JSON.stringify(body) }),
  logout: () => request("/auth/logout", { method: "POST" }),
  placeOrder: (body: OrderRequest) => request<OrderRead>("/orders/", { method: "POST", body: JSON.stringify(body) }),
  processOrders: (accountId: number) => request(`/orders/process-pending?account_id=${accountId}`, { method: "POST" }),
  // Health
  health: () => request<Health>("/health"),

  // Users
  createUser: (body: { email: string; full_name: string }) =>
    request<UserRead>("/users/", { method: "POST", body: JSON.stringify(body) }),
  getUser: (userId: number) => request<UserRead>(`/users/${userId}`),

  // Accounts
  createAccount: (body: { user_id: number; name: string; currency: AccountCurrency }) =>
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
    request<TradeRead[]>(`/accounts/${accountId}/trades`),
  cancelOrder: (orderId: number, accountId: number) =>
    request<OrderRead>(`/orders/${orderId}/cancel?account_id=${accountId}`, { method: "POST" }),

    // Symbols + seeding
  getSymbols: () => request<SymbolItem[]>("/symbols"),
  searchSymbols: (query: string, signal?: AbortSignal) => request<SymbolItem[]>(`/symbols/search?q=${encodeURIComponent(query)}`, { signal }),
  seedDefaultWatchlist: () =>
    request<{ message: string }>("/seed/default-watchlist", { method: "POST" }),

  // Bulk latest prices
  // Bulk latest prices (backend expects a raw JSON array: ["AAPL","MSFT"])
  latestBulk: (symbols: string[], options?: { force?: boolean }) =>
    request<BulkLatestItem[]>(
      `/prices/latest/bulk${options?.force ? "?force=true" : ""}`,
      {
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
