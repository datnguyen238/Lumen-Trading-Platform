import Link from "next/link";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/markets", label: "Markets" },
  { href: "/watchlists", label: "Watchlists" },
  { href: "/orders", label: "Orders" },
];

export function AppSidebar() {
  return (
    <div className="flex h-screen flex-col">
      <div className="flex items-center justify-between px-4 py-4">
        <Link href="/dashboard" className="text-sm font-semibold tracking-tight">
          Trading UI
        </Link>
        <div className="text-xs text-muted-foreground">Paper</div>
      </div>

      <nav className="px-2">
        {nav.map((item) => (
          <SidebarItem key={item.href} href={item.href} label={item.label} />
        ))}
      </nav>

      <div className="mt-auto border-t p-4">
        <div className="text-xs text-muted-foreground">Connection</div>
        <div className="mt-1 flex items-center justify-between">
          <div className="text-sm font-medium">API</div>
          <span className="text-xs text-muted-foreground">Unknown</span>
        </div>
      </div>
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
