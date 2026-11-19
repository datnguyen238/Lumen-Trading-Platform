"use client";
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { useSession } from "@/components/shell/session-provider";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
const guestKey = "lumen.watchlist.guest";
function guestSymbols(): string[] {
  try { const data = JSON.parse(localStorage.getItem(guestKey) || "[]"); return Array.isArray(data) ? data.filter(s => typeof s === "string") : []; } catch { return []; }
}
type Watchlist = { symbols: string[]; busy: boolean; error: string | null; toggle: (symbol: string) => Promise<void>; reload: () => void };
const Context = createContext<Watchlist | null>(null);
export function WatchlistProvider({ children }: { children: ReactNode }) {
  const { userId } = useSession();
  const owner = userId ?? "guest";
  const loader = useCallback(() => userId ? api.getWatchlist() : Promise.resolve(guestSymbols()), [userId]);
  const resource = useResource(`watchlist:${owner}`, loader);
  const [mutation, setMutation] = useState<{ owner: typeof owner; symbols: string[] } | null>(null);
  const [failure, setFailure] = useState<{ owner: typeof owner; message: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const locked = useRef(false);
  const symbols = mutation?.owner === owner ? mutation.symbols : resource.data ?? [];
  async function toggle(symbol: string) {
    if (locked.current || resource.loading) return;
    locked.current = true; setBusy(true); setFailure(null);
    const value = symbol.trim().toUpperCase();
    try {
      let next: string[];
      if (userId) next = symbols.includes(value) ? await api.removeAsset(value) : await api.saveAsset(value);
      else { next = symbols.includes(value) ? symbols.filter(s => s !== value) : [...symbols, value]; localStorage.setItem(guestKey, JSON.stringify(next)); }
      setMutation({ owner, symbols: next });
    } catch (error) { setFailure({ owner, message: errorMessage(error) }); }
    finally { locked.current = false; setBusy(false); }
  }
  function reload() { setMutation(null); setFailure(null); resource.reload(); }
  return <Context.Provider value={{ symbols, busy: busy || resource.loading, error: failure?.owner === owner ? failure.message : resource.error, toggle, reload }}>{children}</Context.Provider>;
}
export function useWatchlist() { const value = useContext(Context); if (!value) throw new Error("WatchlistProvider is required"); return value; }
