"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import { AppSidebar } from "@/components/shell/app-sidebar";
import { TopBar } from "@/components/shell/topbar";

export default function ShellLayout(props: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const sidebarClass = `fixed inset-y-0 left-0 z-50 w-64 border-r bg-background transition-transform duration-200 ${
    sidebarOpen ? "translate-x-0" : "-translate-x-full"
  }`;

  return (
    <div className="min-h-screen">
      <aside className={sidebarClass}>
        <AppSidebar onToggle={() => setSidebarOpen(false)} />
      </aside>

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div
        className={`flex min-h-screen flex-col transition-[padding] ${
          sidebarOpen ? "md:pl-64" : "md:pl-0"
        }`}
      >
        <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
          <TopBar
            sidebarOpen={sidebarOpen}
            onToggleSidebar={() => setSidebarOpen((v) => !v)}
          />
        </header>

        <main className="flex-1 p-4 md:p-6">
          {props.children}
        </main>
      </div>
    </div>
  );
}
