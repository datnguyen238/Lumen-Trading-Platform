"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/components/shell/session-provider";
import { Button } from "@/components/ui/button";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";

const DEFAULT_SYMBOLS = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "BTCUSDT", "ETHUSDT"];

export function TopBar(props: { onToggleSidebar?: () => void; sidebarOpen?: boolean }) {
  const router = useRouter();
  const { userId, accountId, setUserId, setAccountId } = useSession();

  const [open, setOpen] = useState(false);
  const [health, setHealth] = useState<"ok" | "down" | "checking">("checking");

  const symbols = useMemo(() => DEFAULT_SYMBOLS, []);

  useEffect(() => {
    let cancelled = false;
    api.health()
      .then((r) => {
        if (cancelled) return;
        setHealth(r.status === "ok" ? "ok" : "down");
      })
      .catch(() => {
        if (cancelled) return;
        setHealth("down");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function goToSymbol(symbol: string) {
    const cleaned = symbol.trim().toUpperCase();
    if (!cleaned) return;
    setOpen(false);
    router.push(`/asset/${encodeURIComponent(cleaned)}`);
  }

  return (
    <div className="flex items-center gap-3 px-4 py-3 md:px-6">
      <div className="flex items-center gap-2">
        {props.onToggleSidebar && props.sidebarOpen === false && (
          <Button
            variant="ghost"
            onClick={props.onToggleSidebar}
            className="h-9 w-9 px-0"
            aria-label="Toggle sidebar"
          >
            ≡
          </Button>
        )}
        <Button variant="outline" onClick={() => setOpen(true)} className="h-9">
          Search
        </Button>

        <div className="hidden text-xs text-muted-foreground md:block">
          API:{" "}
          <span className={health === "ok" ? "text-emerald-500" : health === "down" ? "text-rose-500" : ""}>
            {health}
          </span>
        </div>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <div className="hidden items-center gap-2 md:flex">
          <div className="text-xs text-muted-foreground">user_id</div>
          <Input
            className="h-8 w-24"
            value={userId ?? ""}
            onChange={(e) => setUserId(e.target.value ? Number(e.target.value) : null)}
            inputMode="numeric"
          />
          <div className="text-xs text-muted-foreground">account_id</div>
          <Input
            className="h-8 w-28"
            value={accountId ?? ""}
            onChange={(e) => setAccountId(e.target.value ? Number(e.target.value) : null)}
            inputMode="numeric"
          />
        </div>
      </div>

      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput
          placeholder="Search symbol (e.g., AAPL, BTCUSDT)"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              const value = (e.target as HTMLInputElement).value;
              goToSymbol(value);
            }
          }}
        />
        <CommandList>
          <CommandEmpty>No results.</CommandEmpty>
          <CommandGroup heading="Popular">
            {symbols.map((s) => (
              <CommandItem key={s} onSelect={() => goToSymbol(s)}>
                {s}
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </div>
  );
}
