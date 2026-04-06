import type { MetalRates } from "../../hooks/useMetalRates";
import { formatRupees } from "../../lib/formatIndian";

interface MetalRateBarProps {
  rates: MetalRates | undefined;
  isLoading?: boolean;
  selectedMetal: string | null;
}

const METAL_COLORS: Record<string, string> = {
  gold: "#D4A843",
  silver: "#C0C0C0",
  platinum: "#A0B2C6",
};

const METAL_LABELS: Record<string, string> = {
  gold: "Gold",
  silver: "Silver",
  platinum: "Platinum",
};

/** Valid purity keys per metal — used to filter out metadata fields */
const VALID_PURITIES: Record<string, string[]> = {
  gold: ["24K", "22K", "18K"],
  silver: ["999", "925", "900"],
  platinum: ["999", "950", "900"],
};

/** The "headline" purity for each metal shown in the "All" view */
const HEADLINE_PURITY: Record<string, string> = {
  gold: "24K",
  silver: "999",
  platinum: "999",
};

export function MetalRateBar({ rates, isLoading, selectedMetal }: MetalRateBarProps) {
  if (isLoading) {
    return (
      <div className="bg-[#D4A843]/10 rounded-lg px-4 py-3 border border-[#D4A843]/20 mb-4">
        <span className="text-sm text-[#E8ECF1]/50">Loading metal rates...</span>
      </div>
    );
  }

  if (!rates || Object.keys(rates).length === 0) {
    return (
      <div className="bg-[#D4A843]/10 rounded-lg px-4 py-3 border border-[#D4A843]/20 mb-4">
        <span className="text-sm text-[#E8ECF1]/50">Metal rates unavailable</span>
      </div>
    );
  }

  // Which metals to show
  const metals = selectedMetal ? [selectedMetal] : ["gold", "silver", "platinum"];

  return (
    <div className="bg-[#D4A843]/10 rounded-lg px-4 py-3 border border-[#D4A843]/20 mb-4">
      <div className="flex flex-wrap items-center gap-6">
        {metals.map((metal) => {
          const metalRates = rates[metal];
          if (!metalRates) return null;

          const color = METAL_COLORS[metal] ?? "#6B7280";
          const label = METAL_LABELS[metal] ?? metal;

          // When a single metal is selected, show all valid purities; otherwise just the headline
          // Filter out metadata keys (source, fetched_at, is_stale) from API response
          const validPurities = VALID_PURITIES[metal] ?? [];
          const purities = selectedMetal
            ? validPurities.filter((p) => metalRates[p] != null)
            : [HEADLINE_PURITY[metal]].filter((p) => p && metalRates[p]);

          return (
            <div key={metal} className="flex items-center gap-3">
              <span
                className="text-xs font-bold uppercase tracking-wider"
                style={{ color }}
              >
                {label}
              </span>
              <div className="flex items-center gap-3">
                {purities.map((purity) => {
                  const rate = metalRates[purity];
                  if (rate == null) return null;
                  return (
                    <div key={purity} className="flex items-center gap-1.5">
                      <span className="text-xs text-[#E8ECF1]/50 uppercase tracking-wider">
                        {purity}
                      </span>
                      <span
                        className="text-sm font-semibold"
                        style={{ color, fontVariantNumeric: "tabular-nums" }}
                      >
                        {formatRupees(rate)}/g
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
