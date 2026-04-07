import { RefreshCw, LogOut, Link } from "lucide-react";
import type { KiteStatus } from "../../hooks/useKitePortfolio";

interface Props {
  status: KiteStatus | undefined;
  isLoading: boolean;
  onConnect: () => void;
  onDisconnect: () => Promise<unknown>;
  onRefresh: () => void;
  isStale?: boolean;
}

export function KiteConnectionBanner({ status, isLoading, onConnect, onDisconnect, onRefresh, isStale }: Props) {
  if (isLoading) {
    return (
      <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6 animate-pulse h-14" />
    );
  }

  if (!status?.connected) {
    return (
      <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6 flex items-center justify-between">
        <p className="text-[#E8ECF1]/60 text-sm">Connect your Zerodha account to view live MF portfolio</p>
        <button
          onClick={onConnect}
          className="flex items-center gap-2 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          <Link size={16} />
          Connect Zerodha
        </button>
      </div>
    );
  }

  const syncText = status.last_sync
    ? `Synced ${new Date(status.last_sync).toLocaleTimeString()}`
    : "Not synced yet";

  return (
    <div className={`rounded-xl p-4 border mb-6 flex items-center justify-between ${
      status.is_expired || isStale
        ? "bg-[#3D2E13] border-[#E5A100]/30"
        : "bg-[#132E3D] border-[#1A3A5C]/30"
    }`}>
      <div>
        <p className="text-sm text-[#E8ECF1]">
          {status.is_expired
            ? "Zerodha session expired"
            : isStale
            ? "Showing cached data"
            : "Connected to Zerodha"}
          {" "}<span className="text-[#E8ECF1]/40">— {syncText}</span>
        </p>
      </div>
      <div className="flex items-center gap-2">
        {status.is_expired ? (
          <button
            onClick={onConnect}
            className="flex items-center gap-1 bg-[#D4A843] hover:bg-[#D4A843]/80 text-[#0D1B2A] rounded px-3 py-1.5 text-sm font-medium transition-colors"
          >
            Reconnect
          </button>
        ) : (
          <button
            onClick={onRefresh}
            aria-label="Refresh portfolio"
            className="flex items-center gap-1 text-[#E8ECF1]/60 hover:text-[#E8ECF1] transition-colors p-1.5 rounded hover:bg-[#1A3A5C]/30 focus-visible:ring-2 focus-visible:ring-[#00895E] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0D1B2A]"
          >
            <RefreshCw size={16} />
          </button>
        )}
        <button
          onClick={() => onDisconnect()}
          aria-label="Disconnect Zerodha"
          className="flex items-center gap-1 text-[#E8ECF1]/40 hover:text-[#E5A100] transition-colors p-1.5 rounded hover:bg-[#1A3A5C]/30 focus-visible:ring-2 focus-visible:ring-[#00895E] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0D1B2A]"
        >
          <LogOut size={16} />
        </button>
      </div>
    </div>
  );
}
