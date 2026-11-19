export type Health = { status: "ok" | string };

export type UserRead = {
  id: number;
  email: string;
  full_name: string;
};

export type AccountRead = {
  id: number;
  user_id: number;
  name: string;
  cash_balance: string;
  created_at: string;
};

export type PositionRead = {
  id: number;
  account_id: number;
  symbol: string;
  quantity: string;
  average_price: string;
};

export type PriceBarRead = {
  id?: number;
  symbol: string;
  timestamp: string; // or "ts" depending on your backend; we handle both in client
  open: string;
  high: string;
  low: string;
  close: string;
  volume?: string;
  change?: string | null;
  change_percent?: string | null;
  previous_timestamp?: string | null;
};

export type OrderRead = {
  id: number;
  account_id: number;
  symbol: string;
  side: "BUY" | "SELL";
  order_type: "MARKET" | "LIMIT";
  quantity: string;
  status?: string;
  filled_price?: string;
  avg_fill_price: string | null;
  filled_quantity: string;
  limit_price: string | null;
  created_at?: string;
  execution?: { quote_timestamp: string; quote_price: string; cash_before: string; cash_after: string; fees: string; model: string } | null;
};

export type TradeRead = {
  id: number;
  account_id: number;
  order_id: number;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: string;
  price: string;
  executed_at: string;
};

export type AccountSummary = {
  account_id: number;
  cash: string;
  reserved_cash: string;
  available_cash: string;
  equity: string;
  market_value: string;
  realized_pnl: string;
  unrealized_pnl: string;
  total_pnl: string;
  positions: Record<
    string,
    {
      symbol: string;
      quantity: string;
      avg_cost: string;
      mark_price: string;
      market_value: string;
      unrealized_pnl: string;
      available_quantity: string;
      reserved_quantity: string;
    }
  >;
};

export type MarketOrderRequest = {
  account_id: number;
  symbol: string;
  side: "BUY" | "SELL";
  order_type: "MARKET";
  quantity: number;
  client_order_id?: string;
};

export type SymbolItem = {
  symbol: string;
  asset_type?: string;
  kind?: "stock" | "crypto" | "index" | string;
  name?: string;
};

export type BulkLatestRequest = {
  symbols: string[];
};

export type BulkLatestItem = {
  symbol: string;
  close: string | number | null;
  timestamp: string | null;
  source?: string;
  // open?: string;
  // high?: string;
  // low?: string;
  // volume?: string;
};

export type BulkLatestResponse = BulkLatestItem[];

export type AuthRead = { user: UserRead; accounts: AccountRead[]; csrf_token: string };
export type OrderRequest = Omit<MarketOrderRequest, "order_type"> & { order_type: "MARKET" | "LIMIT"; limit_price?: number };

export type AccountOverview = { account: AccountRead; positions: PositionRead[]; summary: AccountSummary; orders: OrderRead[]; trades: TradeRead[]; quotes: BulkLatestItem[] };
export type PreviewRequest = { account_id: number; symbol: string; side: "BUY" | "SELL"; order_type: "MARKET" | "LIMIT"; quantity?: number; notional?: number; limit_price?: number };
export type OrderPreview = {
  id: string; account_id: number; symbol: string; side: "BUY" | "SELL"; order_type: "MARKET" | "LIMIT";
  quantity: string; notional: string | null; limit_price: string | null; estimated_price: string; estimated_total: string;
  quote_timestamp: string; expires_at: string; cash_before: string; cash_after: string; shares_before: string; shares_after: string;
  available_cash: string; available_shares: string; fees: string; explanation: string;
};
