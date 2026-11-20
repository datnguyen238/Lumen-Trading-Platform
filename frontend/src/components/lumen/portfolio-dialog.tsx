"use client";

import { useRef, useState, type FormEvent } from "react";
import { ArrowRight, X } from "lucide-react";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/format";
import type { AccountCurrency } from "@/lib/types";
import { useSession } from "@/components/shell/session-provider";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { ErrorNotice } from "./common";

const currencies = [
  { code: "USD", name: "US dollar" },
  { code: "VND", name: "Vietnamese đồng" },
] as const;

export function PortfolioDialog({ open, onOpenChange, initialCurrency, onComplete }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialCurrency: AccountCurrency;
  onComplete: () => void;
}) {
  const session = useSession();
  const heading = useRef<HTMLHeadingElement>(null);
  const submitting = useRef(false);
  const [name, setName] = useState("My portfolio");
  const [currency, setCurrency] = useState<AccountCurrency>(initialCurrency);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!session.userId || !name.trim() || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError(null);
    try {
      const account = await api.createAccount({ user_id: session.userId, name: name.trim(), currency });
      await session.reload(account.id);
      onComplete();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return <Dialog open={open} onOpenChange={value => { if (!submitting.current) onOpenChange(value); }}>
    <DialogContent className="l-portfolio-dialog" showCloseButton={false}
      onOpenAutoFocus={event => { event.preventDefault(); heading.current?.focus(); }}>
      <header className="l-portfolio-dialog-header">
        <DialogTitle ref={heading} tabIndex={-1}>New portfolio</DialogTitle>
        <DialogClose asChild><button type="button" className="l-portfolio-close" aria-label="Close new portfolio" disabled={busy}><X size={19} aria-hidden="true"/></button></DialogClose>
      </header>
      <DialogDescription className="sr-only">Choose a name and currency for your paper portfolio.</DialogDescription>
      <form className="l-portfolio-form" onSubmit={submit} aria-busy={busy}>
        <fieldset className="l-portfolio-fields" disabled={busy}>
          <label className="l-portfolio-name" htmlFor="new-portfolio-name">Portfolio name
            <input id="new-portfolio-name" autoComplete="off" value={name} onChange={event => setName(event.target.value)} required maxLength={80}/>
          </label>
          <fieldset className="l-portfolio-currency">
            <legend>Balance currency</legend>
            <div className="l-currency-options">
              {currencies.map(item => <label key={item.code} className="l-currency-option">
                <span><strong>{item.code}</strong><small>{item.name}</small></span>
                <input type="radio" name="portfolio-currency" value={item.code} checked={currency === item.code} onChange={() => setCurrency(item.code)}/>
              </label>)}
            </div>
          </fieldset>
        </fieldset>
        {error && <ErrorNotice message={error}/>}
        <button className="l-button l-portfolio-submit" type="submit" disabled={busy || !name.trim() || !session.userId}>
          {busy ? "Creating portfolio…" : "Create portfolio"}{!busy && <ArrowRight size={17} aria-hidden="true"/>}
        </button>
      </form>
    </DialogContent>
  </Dialog>;
}
