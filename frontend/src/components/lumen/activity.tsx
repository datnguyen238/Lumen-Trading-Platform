"use client";

import { useState } from "react";
import { useSession } from "@/components/shell/session-provider";
import { capitalizeFirst, errorMessage, money, quantity, timestamp } from "@/lib/format";
import type { OrderRead } from "@/lib/types";
import { api } from "@/lib/api";
import { AssetIdentity, Empty, ErrorNotice, Loading, PageHeading, RefreshButton } from "./common";
import { useAccount } from "./data";

function isOpen(order: OrderRead) {
  return ["PENDING", "PARTIALLY_FILLED"].includes(order.status || "");
}
function Status({ order }: { order: OrderRead }) {
  return <span className={`l-status ${isOpen(order) ? "pending" : order.status === "CANCELED" ? "canceled" : ""}`}>
    {order.status ? capitalizeFirst(order.status.replaceAll("_", " ").toLowerCase()) : "Unknown"}
  </span>;
}
function total(order: OrderRead) {
  return Number(order.filled_quantity) > 0 && order.avg_fill_price
    ? `${money(order.account_total, undefined, order.account_currency)} total`
    : "Not filled";
}

export function Activity() {
  const session = useSession();
  const account = useAccount();
  const [tab, setTab] = useState("all");
  const [page, setPage] = useState(0);
  const [canceling, setCanceling] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const rows = account.data?.orders.filter((order) => tab === "all" || (tab === "open" ? isOpen(order) : order.status === "FILLED")) ?? [];
  const maxPage = Math.max(0, Math.ceil(rows.length / 15) - 1);
  const currentPage = Math.min(page, maxPage);
  const visible = rows.slice(currentPage * 15, currentPage * 15 + 15);
  async function cancel(orderId: number) {
    if (!session.accountId) return;
    setCanceling(orderId);
    setError(null);
    try { await api.cancelOrder(orderId, session.accountId); account.reload(); }
    catch (failure) { setError(errorMessage(failure)); }
    finally { setCanceling(null); }
  }
  function cancelButton(order: OrderRead) {
    return isOpen(order) && <button className="l-button l-quiet" disabled={canceling === order.id} onClick={() => cancel(order.id)}>
      {canceling === order.id ? "Canceling…" : "Cancel order"}
    </button>;
  }
  return <>
    <PageHeading title="Activity">
      <RefreshButton busy={account.loading} onClick={account.reload}/>
    </PageHeading>
    {!session.ready || account.loading && !account.data && session.accountId ? <Loading label="Loading account activity"/> : !session.accountId ?
      <section className="l-surface"><Empty title="Sign in to view activity" action="Sign in" href="/dashboard"/></section> : <>
      {account.error && <ErrorNotice message={account.error} retry={account.reload}/>}
      <section className="l-surface">
        <div className="l-toolbar">
          <div className="l-tabs" aria-label="Order status">
            {[["all", "All orders"], ["filled", "Filled"], ["open", "Open"]].map(([id, label]) =>
              <button key={id} className={tab === id ? "active" : ""} aria-pressed={tab === id} onClick={() => { setTab(id); setPage(0); }}>{label}</button>
            )}
          </div>
          <span className="l-note">{rows.length} {rows.length === 1 ? "order" : "orders"}</span>
        </div>
        {error && <ErrorNotice message={error}/>}
        {!rows.length ? <Empty title={tab === "open" ? "No open orders" : "No trades yet"} action={tab === "open" ? undefined : "Explore investments"}/> : <>
          <div className="l-table-scroll l-mobile-hide">
            <table className="l-table">
              <thead><tr><th scope="col">Investment</th><th scope="col">Order</th><th scope="col">Quantity</th><th scope="col">Fill price</th><th scope="col">Placed</th><th scope="col">Status</th></tr></thead>
              <tbody>{visible.map((order) => <tr key={order.id}>
                <td><AssetIdentity symbol={order.symbol}/></td>
                <td>{order.side === "BUY" ? "Buy" : "Sell"}<small>{order.order_type === "LIMIT" ? `Limit ${money(order.limit_price, undefined, order.currency)}` : "Market"}</small></td>
                <td>{quantity(order.quantity)}{Number(order.filled_quantity) > 0 && Number(order.filled_quantity) < Number(order.quantity) && <small>{quantity(order.filled_quantity)} filled</small>}</td>
                <td>{money(order.avg_fill_price, undefined, order.currency)}<small>{total(order)}</small></td>
                <td><span className="l-muted">{timestamp(order.created_at)}</span></td>
                <td><Status order={order}/><div style={{ marginTop: 6 }}>{cancelButton(order)}</div></td>
              </tr>)}</tbody>
            </table>
          </div>
          <ul className="l-mobile-orders" aria-label="Paper order activity">
            {visible.map((order) => <li className="l-mobile-order" key={order.id}>
              <header><AssetIdentity symbol={order.symbol}/><Status order={order}/></header>
              <dl className="l-mobile-order-details">
                <div><dt>{order.order_type === "LIMIT" ? `Limit ${money(order.limit_price, undefined, order.currency)}` : "Market"}{Number(order.filled_quantity) > 0 && Number(order.filled_quantity) < Number(order.quantity) ? ` · ${quantity(order.filled_quantity)} filled` : ""}</dt><dd>{order.side === "BUY" ? "Buy" : "Sell"} {quantity(order.quantity)} shares</dd></div>
                <div><dt>Fill price</dt><dd>{money(order.avg_fill_price, undefined, order.currency)}</dd></div>
              </dl>
              <footer><time dateTime={order.created_at}>{timestamp(order.created_at)}</time><span>{total(order)}</span></footer>
              {cancelButton(order)}
            </li>)}
          </ul>
        </>}
        {rows.length > 15 && <div className="l-pagination">
          <span>{currentPage * 15 + 1}–{Math.min((currentPage + 1) * 15, rows.length)} of {rows.length}</span>
          <div className="l-actions"><button className="l-button l-quiet" disabled={!currentPage} onClick={() => setPage(currentPage - 1)}>Previous</button><button className="l-button l-quiet" disabled={currentPage >= maxPage} onClick={() => setPage(currentPage + 1)}>Next</button></div>
        </div>}
      </section>

    </>}
  </>;
}
