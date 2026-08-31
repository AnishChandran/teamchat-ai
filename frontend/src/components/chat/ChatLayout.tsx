import type { ReactNode } from "react";

import { ChatHeader } from "./ChatHeader";

interface ChatLayoutProps {
  sidebar: ReactNode;
  main: ReactNode;
}

export function ChatLayout({ sidebar, main }: ChatLayoutProps) {
  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100">
      <ChatHeader />
      <div className="flex min-h-0 flex-1">
        <aside className="flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-900/50">
          {sidebar}
        </aside>
        <section className="flex min-w-0 flex-1 flex-col">{main}</section>
      </div>
    </div>
  );
}
