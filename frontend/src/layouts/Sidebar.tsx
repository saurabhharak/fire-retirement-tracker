import { useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Coins,
  Gem,
  Settings,
  Briefcase,
  TrendingUp,
  Shield,
  ClipboardList,
  Lock,
  LogOut,
  X,
  Hammer,
  LineChart,
  Wallet,
} from "lucide-react";
import { NAV_ITEMS } from "../lib/constants";
import { useAuth } from "../contexts/AuthContext";

const iconMap: Record<string, React.ComponentType<{ size?: number }>> = {
  LayoutDashboard,
  Coins,
  Gem,
  Settings,
  Briefcase,
  TrendingUp,
  Shield,
  ClipboardList,
  Lock,
  Hammer,
  LineChart,
  Wallet,
};

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleNav = (path: string) => {
    navigate(path);
    onClose();
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
          role="dialog"
          aria-modal="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 z-50 h-full w-64 bg-[#0c1324] flex flex-col
          transition-transform duration-300 ease-in-out
          md:translate-x-0
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-5 border-b border-[#1A3A5C]/30">
          <h2 className="text-lg font-bold text-[#E8ECF1]">FIRE Tracker</h2>
          <button
            className="md:hidden p-1 rounded text-[#E8ECF1]/60 hover:text-[#E8ECF1]"
            onClick={onClose}
            aria-label="Close navigation menu"
          >
            <X size={20} />
          </button>
        </div>

        {/* Nav items */}
        <nav className="flex-1 overflow-y-auto py-4 px-3">
          {NAV_ITEMS.map((item) => {
            const Icon = iconMap[item.icon];
            const isActive = location.pathname === item.path;

            return (
              <button
                key={item.path}
                onClick={() => handleNav(item.path)}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 mb-1 rounded-lg text-sm
                  transition-colors duration-150
                  ${
                    isActive
                      ? "bg-[#00895E] text-white font-medium"
                      : "text-[#E8ECF1]/70 hover:bg-[#1A3A5C]/30 hover:text-[#E8ECF1]"
                  }
                `}
              >
                {Icon && <Icon size={18} />}
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* User section */}
        <div className="border-t border-[#1A3A5C]/30 px-4 py-4">
          <p className="text-xs text-[#E8ECF1]/50 truncate mb-3">
            {user?.email ?? ""}
          </p>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-[#E8ECF1]/60 hover:text-[#E8ECF1] transition-colors"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </aside>
    </>
  );
}
