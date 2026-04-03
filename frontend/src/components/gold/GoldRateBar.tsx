import type { GoldRate } from "../../hooks/useGoldRate";
import { formatRupees } from "../../lib/formatIndian";

interface GoldRateBarProps {
  rate: GoldRate | null;
  isLoading?: boolean;
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function GoldRateBar({ rate, isLoading }: GoldRateBarProps) {
  if (isLoading) {
    return (
      <div className="bg-[#D4A843]/10 rounded-lg px-4 py-3 border border-[#D4A843]/20 mb-4">
        <span className="text-sm text-[#E8ECF1]/50">Loading gold rates...</span>
      </div>
    );
  }

  if (!rate) {
    return (
      <div className="bg-[#D4A843]/10 rounded-lg px-4 py-3 border border-[#D4A843]/20 mb-4">
        <span className="text-sm text-[#E8ECF1]/50">Gold rates unavailable</span>
      </div>
    );
  }

  return (
    <div className="bg-[#D4A843]/10 rounded-lg px-4 py-3 border border-[#D4A843]/20 mb-4">
      <div className="flex flex-wrap items-center gap-4">
        {/* Rates */}
        <div className="flex items-center gap-4 flex-1 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-[#E8ECF1]/50 uppercase tracking-wider">24K</span>
            <span
              className="text-sm font-semibold text-[#D4A843]"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {formatRupees(rate.rate_24k)}/g
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-[#E8ECF1]/50 uppercase tracking-wider">22K</span>
            <span
              className="text-sm font-semibold text-[#D4A843]/80"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {formatRupees(rate.rate_22k)}/g
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-[#E8ECF1]/50 uppercase tracking-wider">18K</span>
            <span
              className="text-sm font-semibold text-[#6B7280]"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {formatRupees(rate.rate_18k)}/g
            </span>
          </div>
        </div>

        {/* Meta */}
        <div className="flex items-center gap-2 text-xs text-[#E8ECF1]/40">
          {rate.is_stale && (
            <span className="bg-[#E5A100]/20 text-[#E5A100] px-2 py-0.5 rounded-full text-xs font-medium">
              Stale
            </span>
          )}
          <span>via {rate.source}</span>
          <span>Updated {formatTimestamp(rate.fetched_at)}</span>
        </div>
      </div>
    </div>
  );
}
