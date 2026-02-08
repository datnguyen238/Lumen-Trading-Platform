import Link from "next/link";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/markets", label: "Markets" },
  { href: "/watchlists", label: "Watchlists" },
  { href: "/orders", label: "Orders" },
];

export function AppSidebar(props: { onToggle?: () => void }) {
  return (
    <div className="flex h-screen flex-col">
      <div className="flex items-center justify-between px-4 py-4">
        <Link href="/dashboard" className="text-sm font-semibold tracking-tight">
          Trading UI
        </Link>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {props.onToggle && (
            <button
              type="button"
              onClick={props.onToggle}
              className="rounded-md border px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-muted-foreground hover:text-foreground"
              aria-label="Close sidebar"
            >
              ≡
            </button>
          )}
        </div>
      </div>

      <nav className="px-2">
        {nav.map((item) => (
          <SidebarItem key={item.href} href={item.href} label={item.label} />
        ))}
      </nav>
    </div>
  );
}

function SidebarItem(props: { href: string; label: string }) {
  return (
    <Link
      href={props.href}
      className={cn(
        "flex items-center justify-between rounded-md px-3 py-2 text-sm",
        "hover:bg-accent hover:text-accent-foreground"
      )}
    >
      <span>{props.label}</span>
    </Link>
  );
}
