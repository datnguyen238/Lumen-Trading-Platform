"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowRight, Eye, EyeOff } from "lucide-react";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/format";
import { useSession } from "@/components/shell/session-provider";
import { ErrorNotice } from "./common";

export function AccountSetup({ compact = false, onComplete }: { compact?: boolean; onComplete?: () => void }) {
  const session = useSession();
  const prefix = compact ? "dialog-auth" : "auth";
  const [mode, setMode] = useState<"signup" | "login">("signup");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [portfolio, setPortfolio] = useState("My portfolio");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null);
    try {
      if (session.userId) {
        const account = await api.createAccount({ user_id: session.userId, name: portfolio.trim() });
        await session.reload(account.id);
      } else {
        const data = mode === "signup"
          ? await api.signup({ email: email.trim(), password, full_name: name.trim() })
          : await api.login({ email: email.trim(), password });
        session.authenticate(data);
      }
      setPassword(""); onComplete?.();
    } catch (failure) { setError(errorMessage(failure)); }
    finally { setBusy(false); }
  }
  const signedIn = !!session.user;
  const Title = compact ? "h2" : "h1";
  return <div className={compact ? "l-setup compact" : "l-auth-page"}>
    <section className="l-setup-form">
      <Title>{signedIn ? "New portfolio" : mode === "signup" ? "Create account" : "Sign in"}</Title>
      {(signedIn || mode === "signup") && <p>$100,000 in virtual cash.</p>}
      <form onSubmit={submit} className="l-form">
        {signedIn ? <label htmlFor={`${prefix}-portfolio`}>Portfolio name<input id={`${prefix}-portfolio`} value={portfolio} onChange={e => setPortfolio(e.target.value)} required maxLength={80}/></label> : <>
          {mode === "signup" && <label htmlFor={`${prefix}-name`}>Your name<input id={`${prefix}-name`} autoComplete="name" value={name} onChange={e => setName(e.target.value)} required maxLength={100}/></label>}
          <label htmlFor={`${prefix}-email`}>Email address<input id={`${prefix}-email`} type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" required maxLength={200}/></label>
          <label htmlFor={`${prefix}-password`}>Password<div className="l-password-field"><input id={`${prefix}-password`} type={showPassword ? "text" : "password"} autoComplete={mode === "signup" ? "new-password" : "current-password"} value={password} onChange={e => setPassword(e.target.value)} required minLength={mode === "signup" ? 8 : 1} maxLength={128} aria-describedby={mode === "signup" ? `${prefix}-password-help` : undefined}/><button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(v => !v)}>{showPassword ? <EyeOff size={18}/> : <Eye size={18}/>}</button></div>{mode === "signup" && <small id={`${prefix}-password-help`}>8 characters minimum.</small>}</label>
        </>}
        {session.error && <ErrorNotice message={session.error} retry={() => void session.reload()}/>}
        {error && <ErrorNotice message={error}/>}
        <button className="l-button" type="submit" disabled={busy}>{busy ? "Opening your portfolio…" : signedIn ? "Create portfolio" : mode === "signup" ? "Create account" : "Sign in"}<ArrowRight size={16}/></button>
      </form>
      {!signedIn && <div className="l-auth-switch"><span>{mode === "signup" ? "Have an account?" : "New to Lumen?"}</span><button type="button" className="l-text-link" onClick={() => { setMode(mode === "signup" ? "login" : "signup"); setError(null); }}>{mode === "signup" ? "Sign in" : "Create account"}</button></div>}
      {!compact && <Link className="l-auth-explore" href="/markets">Explore markets<ArrowRight size={14}/></Link>}
    </section>
  </div>;
}
