import type { Metadata } from "next";
import "./globals.css";
import { SessionProvider } from "@/components/shell/session-provider";

export const metadata: Metadata = {
  title: "Trading UI",
  description: "Trading-style frontend",
};

export default function RootLayout(props: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-foreground">
        <SessionProvider>{props.children}</SessionProvider>
      </body>

    </html>
  );
}
