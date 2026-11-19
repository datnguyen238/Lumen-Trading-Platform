"use client";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ArrowRight, Bookmark, Check, ChevronDown, Compass, LayoutDashboard, ListOrdered, LogOut, Plus, Search, Wallet } from "lucide-react";
import { useSession } from "@/components/shell/session-provider";
import { api } from "@/lib/api";
import { assetUrl, errorMessage } from "@/lib/format";
import { useWatchlist } from "@/lib/watchlist";
import { useResource } from "@/lib/use-resource";
import { CommandDialog, CommandInput, CommandList, CommandGroup, CommandItem, CommandEmpty } from "@/components/ui/command";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { AccountDataProvider, useAccount } from "./data";
import { AccountSetup } from "./account-setup";
import { AuthPage } from "./auth-page";
import { AssetLogo, ErrorNotice } from "./common";
const navigation = [{ href: "/dashboard", label: "Portfolio", icon: LayoutDashboard }, { href: "/markets", label: "Discover", icon: Compass }, { href: "/watchlists", label: "Watchlist", icon: Bookmark }, { href: "/orders", label: "Activity", icon: ListOrdered }];
export function AppShell({ children }: { children: ReactNode }) {
  const session = useSession();
  const path = usePathname();
  const router = useRouter();
  const privatePage = path === "/dashboard" || path === "/orders";
  useEffect(() => {
    if (privatePage && session.ready && !session.user) router.replace("/login");
  }, [privatePage, session.ready, session.user, router]);
  if (privatePage && (!session.ready || !session.user)) return <AuthPage/>;
  return <AccountDataProvider><Shell>{children}</Shell></AccountDataProvider>;
}
function Shell({ children }: { children: ReactNode }) {
  const path = usePathname(); const router = useRouter();
  const session = useSession(); const account = useAccount(); const watchlist = useWatchlist();
  const [searchOpen, setSearchOpen] = useState(false); const [query, setQuery] = useState(""); const [setupOpen, setSetupOpen] = useState(false);
  const symbols = useResource("search-symbols", useCallback(() => api.getSymbols(), []));
  useEffect(() => { const key = (event: KeyboardEvent) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setSearchOpen((v) => !v); } }; window.addEventListener("keydown", key); return () => window.removeEventListener("keydown", key); }, []);
  function go(symbol: string) { setSearchOpen(false); setQuery(""); router.push(assetUrl(symbol)); }
  const [menuError, setMenuError] = useState<string | null>(null);
  const [signingOut, setSigningOut] = useState(false);
  async function signOut() {
    setSigningOut(true); setMenuError(null);
    try { await session.logout(); document.querySelector<HTMLDetailsElement>(".l-account-menu")?.removeAttribute("open"); router.replace("/login"); }
    catch (failure) { setMenuError(errorMessage(failure)); }
    finally { setSigningOut(false); }
  }
  const currentName = account.data?.account.name || session.accounts.find((a) => a.id === session.accountId)?.name || (session.accountId ? "Paper portfolio" : "Sign in");
  const cleanQuery = query.trim().toUpperCase();
  return <div className="l-app"><a className="l-skip" href="#main-content">Skip to content</a>
    <aside className="l-rail"><Link href="/dashboard" className="l-brand" aria-label="Lumen home"><span className="l-brand-mark" aria-hidden="true"><svg viewBox="0 0 28 28"><path d="M8 5v18h14M14 5v12h8"/></svg></span>Lumen</Link><nav aria-label="Main navigation" className="l-nav">{navigation.map(({ href, label, icon: Icon }) => <Link key={href} href={href} aria-current={path === href ? "page" : undefined} className={path === href ? "active" : ""}><Icon size={19} strokeWidth={1.7}/><span>{label}</span></Link>)}</nav><div className="l-rail-footer"><span className="l-dot"/>Paper trading</div></aside>
    <div className="l-shell"><header className="l-topbar"><button className="l-search-trigger" aria-label="Search investments" onClick={() => setSearchOpen(true)}><Search size={18}/><span>Search companies or symbols</span><kbd>⌘ K</kbd></button><div className="l-topbar-account"><span className="l-paper-badge">Paper trading</span>{session.user ? <details className="l-account-menu"><summary><span className="l-account-avatar"><Wallet size={16}/></span><span className="l-account-name">{currentName}</span><ChevronDown size={14}/></summary><div className="l-account-popover"><strong>Your paper portfolios</strong>{session.accounts.map((item) => <button key={item.id} onClick={() => { session.selectAccount(item); document.querySelector<HTMLDetailsElement>(".l-account-menu")?.removeAttribute("open"); }}><Wallet size={16}/><span>{item.name}</span>{item.id === session.accountId && <Check size={15}/>}</button>)}<p className="l-account-email">{session.user.email}</p><button onClick={() => { setSetupOpen(true); document.querySelector<HTMLDetailsElement>(".l-account-menu")?.removeAttribute("open"); }}><Plus size={16}/>New practice portfolio</button><button disabled={signingOut} onClick={signOut}><LogOut size={16}/>{signingOut ? "Signing out…" : "Sign out"}</button></div></details> : <Link href="/login" className="l-button l-secondary">Sign in</Link>}</div></header>
    <main id="main-content" className="l-main" tabIndex={-1}>{menuError && <ErrorNotice message={menuError}/ >}{session.error && <ErrorNotice message={session.error} retry={() => void session.reload()}/ >}{watchlist.error && <ErrorNotice message={watchlist.error} retry={watchlist.reload}/ >}{children}</main><footer className="l-footer"><span>Simulated trading · Market data may be delayed.</span></footer></div>
    <nav className="l-mobile-nav" aria-label="Mobile navigation">{navigation.map(({ href, label, icon: Icon }) => <Link href={href} key={href} aria-current={path === href ? "page" : undefined} className={path === href ? "active" : ""}><Icon size={20}/><span>{label}</span></Link>)}</nav>
    <CommandDialog className="l-search-dialog" open={searchOpen} onOpenChange={(open) => { setSearchOpen(open); if (!open) setQuery(""); }} title="Search" description="Search known symbols, or enter a stock or fund symbol to research it."><CommandInput aria-label="Search companies or symbols" placeholder="Search a company or symbol…" value={query} onValueChange={setQuery}/><CommandList><CommandEmpty>No matching investments. Try a company name or ticker.</CommandEmpty><CommandGroup heading="Stocks and funds">{(symbols.data ?? []).map((item) => <CommandItem key={item.symbol} value={`${item.symbol} ${item.name || ""}`} onSelect={() => go(item.symbol)}><AssetLogo symbol={item.symbol}/><strong>{item.symbol}</strong><span className="l-command-name">{item.name}</span><ArrowRight size={15}/></CommandItem>)}</CommandGroup>{/^[A-Z^][A-Z0-9.^=-]{0,19}$/.test(cleanQuery) && <CommandGroup heading="Research a symbol"><CommandItem forceMount value={`research-${cleanQuery}`} onSelect={() => go(cleanQuery)}>Research {cleanQuery}<ArrowRight size={16}/></CommandItem></CommandGroup>}</CommandList></CommandDialog>
    <Dialog open={setupOpen} onOpenChange={setSetupOpen}><DialogContent className="l-setup-dialog"><DialogTitle className="sr-only">{session.user ? "New practice portfolio" : "Your Lumen account"}</DialogTitle><DialogDescription className="sr-only">Sign in or create your paper-trading account.</DialogDescription><AccountSetup compact onComplete={() => { setSetupOpen(false); router.push("/dashboard"); }}/></DialogContent></Dialog>
  </div>;
}
