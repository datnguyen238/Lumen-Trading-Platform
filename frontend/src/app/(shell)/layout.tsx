import type { ReactNode } from "react";
import { AppSidebar } from "@/components/shell/app-sidebar";
import { TopBar } from "@/components/shell/topbar";

export default function ShellLayout(props: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 border-r md:block">
        <AppSidebar />
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
          <TopBar />
        </header>

        <main className="flex-1 p-4 md:p-6">
          {props.children}
        </main>
      </div>
    </div>
  );
}
