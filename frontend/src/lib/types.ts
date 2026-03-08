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
};

export type OrderRead = {
  id: number;
  account_id: number;
  symbol: string;
  side: "BUY" | "SELL";
  order_type: "MARKET" | string;
  quantity: string;
  status?: string;
  filled_price?: string;
  created_at?: string;
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
    }
  >;
};

export type MarketOrderRequest = {
  account_id: number;
  symbol: string;
  side: "BUY" | "SELL";
  order_type: "MARKET";
  quantity: number;
};

export type SymbolItem = {
  symbol: string;
  kind?: "stock" | "crypto" | "index" | string;
  name?: string;
};

export type BulkLatestRequest = {
  symbols: string[];
};

export type BulkLatestItem = {
  symbol: string;
  close: string;         
  timestamp: string;
  // open?: string;
  // high?: string;
  // low?: string;
  // volume?: string;
};

export type BulkLatestResponse = BulkLatestItem[];
