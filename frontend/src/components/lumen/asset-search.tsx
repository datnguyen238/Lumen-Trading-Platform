"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/format";
import type { SymbolItem } from "@/lib/types";
import { useResource } from "@/lib/use-resource";
import { CommandDialog, CommandInput, CommandList, CommandGroup, CommandItem, CommandEmpty } from "@/components/ui/command";
import { AssetLogo } from "./common";

export function AssetSearch({ open, onOpenChange, query, onQueryChange, onSelect }: {
  open: boolean; onOpenChange: (open: boolean) => void; query: string;
  onQueryChange: (query: string) => void; onSelect: (symbol: string) => void;
}) {
  const known = useResource("search-symbols", useCallback(() => api.getSymbols(), []));
  const term = query.trim();
  const [attempt, setAttempt] = useState(0);
  const [remote, setRemote] = useState<{ query: string; items: SymbolItem[]; loading: boolean; error: string | null }>({ query: "", items: [], loading: false, error: null });

  useEffect(() => {
    if (!open || term.length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setRemote({ query: term, items: [], loading: true, error: null });
      try {
        const items = await api.searchSymbols(term, controller.signal);
        if (!controller.signal.aborted) setRemote({ query: term, items, loading: false, error: null });
      } catch (error) {
        if (!controller.signal.aborted) setRemote({ query: term, items: [], loading: false, error: errorMessage(error) });
      }
    }, 300);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [open, term, attempt]);

  const searched = term.length >= 2;
  const searching = searched && (remote.query !== term || remote.loading);
  const matches = searched && remote.query === term ? remote.items : [];
  const matchedSymbols = new Set(matches.map(item => item.symbol));
  const items = [...matches, ...(known.data ?? []).filter(item => !matchedSymbols.has(item.symbol) && `${item.symbol} ${item.name || ""}`.toLowerCase().includes(term.toLowerCase()))];
  const failure = searched ? remote.query === term ? remote.error : null : known.error;

  return <CommandDialog className="l-search-dialog" shouldFilter={false} open={open} onOpenChange={onOpenChange} title="Search investments" description="Find a listed stock or fund by company name or ticker.">
    <CommandInput aria-label="Search companies or symbols" placeholder="Company name or ticker" maxLength={80} value={query} onValueChange={onQueryChange}/>
    <CommandList aria-busy={searching || known.loading}>
      {!searching && !known.loading && !failure && <CommandEmpty>No matching stocks or funds. Try another name or ticker.</CommandEmpty>}
      <CommandGroup heading="Stocks and funds">{items.map(item => <CommandItem key={item.symbol} value={`${item.symbol} ${item.name || ""}`} onSelect={() => onSelect(item.symbol)}>
        <AssetLogo symbol={item.symbol}/><strong>{item.symbol}</strong><span className="l-command-name">{item.name}</span><ArrowRight size={15} aria-hidden="true"/>
      </CommandItem>)}</CommandGroup>
      {(searching || known.loading) && <p className="l-search-feedback" role="status">Searching investments…</p>}
      {failure && <div className="l-search-feedback" role="status"><p>{failure}</p><button type="button" className="l-text-link" onClick={() => { known.reload(); setAttempt(value => value + 1); }}>Try again</button></div>}
    </CommandList>
  </CommandDialog>;
}
