"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

type SessionState = {
  userId: number | null;
  accountId: number | null;
  setUserId: (v: number | null) => void;
  setAccountId: (v: number | null) => void;
};

const Ctx = createContext<SessionState | null>(null);

export function SessionProvider(props: { children: React.ReactNode }) {
  const [userId, setUserIdState] = useState<number | null>(null);
  const [accountId, setAccountIdState] = useState<number | null>(null);

  useEffect(() => {
    const u = localStorage.getItem("user_id");
    const a = localStorage.getItem("account_id");
    setUserIdState(u ? Number(u) : null);
    setAccountIdState(a ? Number(a) : null);
  }, []);

  function setUserId(v: number | null) {
    setUserIdState(v);
    if (v === null) localStorage.removeItem("user_id");
    else localStorage.setItem("user_id", String(v));
  }

  function setAccountId(v: number | null) {
    setAccountIdState(v);
    if (v === null) localStorage.removeItem("account_id");
    else localStorage.setItem("account_id", String(v));
  }

  const value = useMemo(
    () => ({ userId, accountId, setUserId, setAccountId }),
    [userId, accountId]
  );

  return <Ctx.Provider value={value}>{props.children}</Ctx.Provider>;
}

export function useSession() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession must be used inside SessionProvider");
  return v;
}
