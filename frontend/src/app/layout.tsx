import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { WatchlistProvider } from "@/lib/watchlist";
import { SessionProvider } from "@/components/shell/session-provider";

const publicSans = localFont({
  src: "../../public/fonts/PublicSans-Variable.ttf",
  variable: "--font-lumen-sans",
  weight: "100 900",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Lumen — Your paper investing workspace", template: "%s · Lumen" },
  description: "Explore investments, practice with virtual money, and understand your portfolio with Lumen.",
};

export default function RootLayout(props: { children: React.ReactNode }) {
  return (
    <html lang="en" className={publicSans.variable}>
      <body className="min-h-screen bg-background text-foreground">
        <SessionProvider><WatchlistProvider>{props.children}</WatchlistProvider></SessionProvider>
      </body>

    </html>
  );
}
