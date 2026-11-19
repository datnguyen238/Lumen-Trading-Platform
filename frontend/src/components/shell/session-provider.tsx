"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api, ApiError, setCsrfToken } from "@/lib/api";
import type { AuthRead, UserRead } from "@/lib/types";
export type RememberedAccount = { id: number; userId: number; name: string };
type Session = {
  user: UserRead | null; userId: number | null; accountId: number | null;
  accounts: RememberedAccount[]; ready: boolean; error: string | null;
  authenticate: (data: AuthRead) => void; reload: (selectId?: number) => Promise<void>;
  selectAccount: (account: RememberedAccount) => void;
  logout: () => Promise<void>; forgetSelection: () => void;
};
const Ctx = createContext<Session | null>(null);
export function SessionProvider({ children }: { children: ReactNode }) {
  const generation = useRef(0);
  const [user, setUser] = useState<UserRead | null>(null);
  const [accounts, setAccounts] = useState<RememberedAccount[]>([]);
  const [accountId, setAccountId] = useState<number | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const clear = useCallback(() => {
    generation.current++;
    setUser(null); setAccounts([]); setAccountId(null); setCsrfToken(null);
    // Selection is a preference, never proof of identity.
    try { localStorage.removeItem("lumen.session"); localStorage.removeItem("user_id"); localStorage.removeItem("account_id"); } catch {}
  }, []);
  const authenticate = useCallback((data: AuthRead) => {
    generation.current++;
    setCsrfToken(data.csrf_token); setUser(data.user);
    const owned = data.accounts.map(a => ({ id: a.id, userId: a.user_id, name: a.name }));
    setAccounts(owned);
    let remembered = 0;
    try { remembered = Number(localStorage.getItem(`lumen.account.${data.user.id}`)); } catch {}
    setAccountId(previous => owned.some(a => a.id === previous) ? previous : owned.find(a => a.id === remembered)?.id ?? owned[0]?.id ?? null);
    setError(null); setReady(true);
  }, []);
  const reload = useCallback(async (selectId?: number) => {
    const started = generation.current;
    try {
      const data = await api.me();
      if (started !== generation.current) return;
      authenticate(data);
      if (selectId && data.accounts.some(a => a.id === selectId)) setAccountId(selectId);
    }
    catch (failure) {
      if (started !== generation.current) return;
      if (failure instanceof ApiError && failure.status === 401) { clear(); setError(null); }
      else setError("We couldn’t connect to your account. Check your connection and try again.");
    } finally { setReady(true); }
  }, [authenticate, clear]);
  useEffect(() => {
    void reload();
    const expired = () => { clear(); setReady(true); };
    const focus = () => { void reload(); };
    window.addEventListener("lumen-auth-expired", expired);
    window.addEventListener("focus", focus);
    return () => { window.removeEventListener("lumen-auth-expired", expired); window.removeEventListener("focus", focus); };
  }, [reload, clear]);
  function selectAccount(account: RememberedAccount) {
    if (!accounts.some(a => a.id === account.id)) return;
    setAccountId(account.id);
    try { localStorage.setItem(`lumen.account.${user?.id}`, String(account.id)); } catch {}
  }
  async function logout() {
    generation.current++;
    try { await api.logout(); clear(); }
    catch (failure) { if (failure instanceof ApiError && failure.status === 401) clear(); else throw failure; }
  }
  return <Ctx.Provider value={{ user, userId: user?.id ?? null, accounts, accountId, ready, error,
    authenticate, reload, selectAccount, logout, forgetSelection: () => { setAccountId(accounts[0]?.id ?? null); },
  }}>{children}</Ctx.Provider>;
}
export function useSession() { const value = useContext(Ctx); if (!value) throw new Error("SessionProvider is required"); return value; }
