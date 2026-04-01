import { type ReactNode, useState } from "react";
import { Menu } from "lucide-react";
import { Sidebar } from "./Sidebar";

export function AppLayout({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-[#0D1B2A]">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="flex-1 md:ml-64 p-6">
        {/* Mobile hamburger button */}
        <button
          className="md:hidden mb-4 p-2 rounded-lg bg-[#132E3D] text-[#E8ECF1]"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open navigation menu"
        >
          <Menu size={24} />
        </button>
        {children}
      </main>
    </div>
  );
}
