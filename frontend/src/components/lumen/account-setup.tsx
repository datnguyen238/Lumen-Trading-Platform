"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowRight, Eye, EyeOff } from "lucide-react";
import { api } from "@/lib/api";
import type { AccountCurrency } from "@/lib/types";
import { errorMessage } from "@/lib/format";
import { useSession } from "@/components/shell/session-provider";
import { ErrorNotice } from "./common";

export function AccountSetup({ compact = false, standalone = false, initialMode = "login", initialCurrency = "USD", onComplete }: { compact?: boolean; standalone?: boolean; initialMode?: "signup" | "login"; initialCurrency?: AccountCurrency; onComplete?: () => void }) {
  const session = useSession();
  const prefix = compact ? "dialog-auth" : "auth";
  const [mode, setMode] = useState<"signup" | "login">(initialMode);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [portfolio, setPortfolio] = useState("My portfolio");
  const [currency, setCurrency] = useState<AccountCurrency>(initialCurrency);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(null);
    try {
      if (session.userId) {
        const account = await api.createAccount({ user_id: session.userId, name: portfolio.trim(), currency });
        await session.reload(account.id);
      } else {
        const data = mode === "signup"
          ? await api.signup({ email: email.trim(), password, full_name: name.trim(), currency })
          : await api.login({ email: email.trim(), password });
        session.authenticate(data);
      }
      setPassword(""); onComplete?.();
    } catch (failure) { setError(errorMessage(failure)); }
    finally { setBusy(false); }
  }
  const signedIn = !!session.user;
  const Title = compact ? "h2" : "h1";
  return <div className={standalone ? "l-auth-form" : compact ? "l-setup compact" : "l-auth-page"}>
    <section className="l-setup-form">
      <Title>{signedIn ? "New portfolio" : mode === "signup" ? "Create your account" : "Sign in to Lumen"}</Title>
      <form onSubmit={submit} className="l-form" aria-busy={busy}>
        {signedIn ? <label htmlFor={`${prefix}-portfolio`}>Portfolio name<input id={`${prefix}-portfolio`} value={portfolio} onChange={e => setPortfolio(e.target.value)} required maxLength={80}/></label> : <>
          {mode === "signup" && <label htmlFor={`${prefix}-name`}>Your name<input id={`${prefix}-name`} autoComplete="name" value={name} onChange={e => setName(e.target.value)} required maxLength={100}/></label>}
          <label htmlFor={`${prefix}-email`}>Email address<input id={`${prefix}-email`} type="email" autoComplete="email" autoCapitalize="none" spellCheck={false} value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" required maxLength={200}/></label>
          <label htmlFor={`${prefix}-password`}>Password<div className="l-password-field"><input id={`${prefix}-password`} type={showPassword ? "text" : "password"} autoComplete={mode === "signup" ? "new-password" : "current-password"} value={password} onChange={e => setPassword(e.target.value)} required minLength={mode === "signup" ? 8 : 1} maxLength={128} aria-describedby={mode === "signup" ? `${prefix}-password-help` : undefined}/><button type="button" aria-label={showPassword ? "Hide password" : "Show password"} aria-controls={`${prefix}-password`} aria-pressed={showPassword} onClick={() => setShowPassword(v => !v)}>{showPassword ? <EyeOff size={18} aria-hidden="true"/> : <Eye size={18} aria-hidden="true"/>}</button></div>{mode === "signup" && <small id={`${prefix}-password-help`}>At least 8 characters.</small>}</label>
        </>}
        {(signedIn || mode === "signup") && <label htmlFor={`${prefix}-currency`}>Portfolio currency<select id={`${prefix}-currency`} value={currency} onChange={e => setCurrency(e.target.value as AccountCurrency)}><option value="USD">USD — US dollar</option><option value="VND">VND — Vietnamese đồng</option></select></label>}
        {session.error && <ErrorNotice message={session.error} retry={() => void session.reload()}/>}
        {error && <ErrorNotice message={error}/>}
        <button className="l-button" type="submit" disabled={busy}>{busy ? signedIn ? "Creating portfolio…" : mode === "signup" ? "Creating account…" : "Signing in…" : signedIn ? "Create portfolio" : mode === "signup" ? "Create account" : "Sign in"}<ArrowRight size={16} aria-hidden="true"/></button>
      </form>
      {!signedIn && <div className="l-auth-switch"><span>{mode === "signup" ? "Already have an account?" : "New to Lumen?"}</span>{standalone ? <Link className="l-text-link" href={mode === "signup" ? "/login" : "/signup"}>{mode === "signup" ? "Sign in" : "Create account"}</Link> : <button type="button" className="l-text-link" disabled={busy} onClick={() => { setMode(mode === "signup" ? "login" : "signup"); setPassword(""); setShowPassword(false); setError(null); }}>{mode === "signup" ? "Sign in" : "Create account"}</button>}</div>}
      {!compact && !standalone && <Link className="l-auth-explore" href="/markets">Explore markets<ArrowRight size={14}/></Link>}
    </section>
  </div>;
}
