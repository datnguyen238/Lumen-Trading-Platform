"use client";
import Link from "next/link";
import Image from "next/image";
import { ArrowRight, AlertCircle, Bookmark, RefreshCw } from "lucide-react";
import { useState, type ReactNode } from "react";
import { assetNames, assetUrl, capitalizeFirst, percent, signedMoney } from "@/lib/format";
import { useWatchlist } from "@/lib/watchlist";
export function PageHeading({ title, description, children }: { title: string; description?: string; children?: ReactNode }) { return <div className="l-page-heading"><div><h1>{title}</h1>{description && <p>{description}</p>}</div>{children && <div className="l-actions">{children}</div>}</div>; }
export function ErrorNotice({ message, retry }: { message: string; retry?: () => void }) { return <div className="l-error" role="alert"><AlertCircle aria-hidden="true" size={19}/><p>{capitalizeFirst(message)}</p>{retry && <button className="l-button l-quiet" onClick={retry}>Try again</button>}</div>; }
export function Loading({ label = "Loading your portfolio" }: { label?: string }) { return <div className="l-loading" role="status"><span className="sr-only">{label}</span><div className="l-skeleton l-skeleton-heading"/><div className="l-skeleton l-skeleton-value"/><div className="l-skeleton l-skeleton-table"/></div>; }
export function Empty({ title, description, action, href = "/markets" }: { title: string; description?: string; action?: string; href?: string }) { return <div className="l-empty"><h2>{title}</h2>{description && <p>{description}</p>}{action && <Link href={href} className="l-button">{action}<ArrowRight size={16}/></Link>}</div>; }
export function RefreshButton({ busy, onClick }: { busy: boolean; onClick: () => void }) { return <button className="l-button l-secondary l-refresh" onClick={onClick} disabled={busy}><RefreshCw size={15} className={busy ? "l-spinning" : ""}/>{busy ? "Refreshing…" : "Refresh"}</button>; }
const lightLogos = new Set("ABBV BA DIS NKE QQQ UBER UNH V".split(" "));
const bundledLogos = new Set("AAPL ABBV ADBE AM AMD AMZN AR BA BRK-B COIN MSFT GOOGL META NVDA TSLA NFLX JPM V MA JNJ UNH PG XOM CVX WMT COST HD KO PEP BAC WFC GS DIS NKE PFE MRK ORCL CRM INTC CSCO PLTR UBER SHOP SPY DIA QQQ IWM VIXY VOO".split(" "));
export function AssetLogo({ symbol }: { symbol: string }) {
  const [failed, setFailed] = useState(false);
  const safe = /^[A-Z0-9.^=-]{1,20}$/.test(symbol);
  const src = bundledLogos.has(symbol) ? `/logos/${symbol}.png` : `https://images.financialmodelingprep.com/symbol/${encodeURIComponent(symbol)}.png`;
  return <span className={`l-asset-logo ${lightLogos.has(symbol) && !failed ? "l-logo-dark" : ""}`} aria-hidden="true">{!failed && safe
    ? <Image src={src} alt="" width={36} height={36} unoptimized onError={() => setFailed(true)}/>
    : <span className="l-logo-fallback">{symbol}</span>}</span>;
}
export function AssetIdentity({ symbol, name, link = true }: { symbol: string; name?: string | null; link?: boolean }) {
  const content = <><AssetLogo key={symbol} symbol={symbol}/><span><strong>{symbol}</strong><small>{name || assetNames[symbol] || "Market instrument"}</small></span></>;
  return link ? <Link className="l-asset" href={assetUrl(symbol)}>{content}</Link> : <span className="l-asset">{content}</span>;
}
export function SaveAsset({ symbol }: { symbol: string }) { const { symbols, toggle, busy } = useWatchlist(); const saved = symbols.includes(symbol); return <button className={`l-icon-button ${saved ? "is-saved" : ""}`} disabled={busy} onClick={() => void toggle(symbol)} aria-label={`${saved ? "Remove" : "Save"} ${symbol} ${saved ? "from" : "to"} watchlist`} aria-pressed={saved}><Bookmark size={18} fill={saved ? "currentColor" : "none"}/></button>; }

export function PriceChange({ change, percentage }: { change?: string | number | null; percentage?: string | number | null }) {
  if (change == null || percentage == null) return null;
  const value = Number(change);
  if (!Number.isFinite(value)) return null;
  return <span className={`l-price-change ${value > 0 ? "l-positive" : value < 0 ? "l-negative" : "l-muted"}`} aria-label={`${value === 0 ? "Unchanged" : value > 0 ? "Up" : "Down"} ${signedMoney(Math.abs(value))}, ${percent(Math.abs(Number(percentage)))} versus previous stored close`}>{value > 0 ? "+" : value < 0 ? "−" : ""}{Math.abs(Number(percentage)).toFixed(2)}%</span>;
}
