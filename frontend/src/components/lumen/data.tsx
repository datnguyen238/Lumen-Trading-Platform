"use client";
import { createContext, useCallback, useContext, useEffect, type ReactNode } from "react";
import { api } from "@/lib/api";
import { useResource } from "@/lib/use-resource";
import { useSession } from "@/components/shell/session-provider";
async function loadAccount(accountId: number | null) {
  if (!accountId) return null;
  return api.getOverview(accountId);
}
type AccountResource = ReturnType<typeof useResource<Awaited<ReturnType<typeof loadAccount>>>>;
const AccountContext = createContext<AccountResource | null>(null);
export function AccountDataProvider({ children }: { children: ReactNode }) {
  const { accountId } = useSession();
  const loader = useCallback(() => loadAccount(accountId), [accountId]);
  const resource = useResource(`account:${accountId}`, loader);
  const refresh = resource.reload;
  useEffect(() => { if (!accountId) return; const interval = window.setInterval(refresh, 15000); return () => window.clearInterval(interval); }, [accountId, refresh]);
  return <AccountContext.Provider value={resource}>{children}</AccountContext.Provider>;
}
export function useAccount() { const resource = useContext(AccountContext); if (!resource) throw new Error("AccountDataProvider is required"); return resource; }
