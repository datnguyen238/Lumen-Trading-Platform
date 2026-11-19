"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowUpRight } from "lucide-react";
import { useSession } from "@/components/shell/session-provider";
import { AccountSetup } from "./account-setup";

export function AuthPage({ mode = "login" }: { mode?: "login" | "signup" }) {
  const session = useSession();
  const router = useRouter();

  useEffect(() => {
    if (session.ready && session.user) router.replace("/dashboard");
  }, [session.ready, session.user, router]);

  return <div className="l-app l-auth-screen">
    <a className="l-skip" href="#main-content">Skip to content</a>
    <header className="l-auth-header">
      <Link href="/" className="l-brand" aria-label="Lumen home">
        <span className="l-brand-mark" aria-hidden="true"><svg viewBox="0 0 28 28"><path d="M8 5v18h14M14 5v12h8"/></svg></span>
        Lumen
      </Link>
      <Link href="/markets" className="l-auth-market-link">Explore markets<ArrowUpRight size={16} aria-hidden="true"/></Link>
    </header>
    <main id="main-content" className="l-auth-main" tabIndex={-1}>
      {!session.ready || session.user ? <div className="l-auth-wait" role="status"><span className="l-auth-progress" aria-hidden="true"/>{session.user ? "Opening your portfolio…" : "Loading your account…"}</div> :
        <AccountSetup key={mode} standalone initialMode={mode} onComplete={() => router.replace("/dashboard")}/>}
    </main>
    <footer className="l-auth-footer">Paper trading. No real money.</footer>
  </div>;
}
