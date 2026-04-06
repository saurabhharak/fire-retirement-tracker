import { useState, useMemo } from "react";
import { usePreciousMetals } from "../hooks/usePreciousMetals";
import type { PreciousMetalUpdate, MetalType } from "../hooks/usePreciousMetals";
import { useMetalRates } from "../hooks/useMetalRates";
import { useMetalsSummary } from "../hooks/useMetalsSummary";
import { PageHeader } from "../components/PageHeader";
import { MetricCard } from "../components/MetricCard";
import { LoadingState } from "../components/LoadingState";
import { OwnerFilter } from "../components/expenses/OwnerFilter";
import type { OwnerOption } from "../components/expenses/OwnerFilter";
import { MetalRateBar } from "../components/metals/MetalRateBar";
import { MetalPurchaseForm } from "../components/metals/MetalPurchaseForm";
import { MetalHoldingsTable } from "../components/metals/MetalHoldingsTable";
import { formatIndian } from "../lib/formatIndian";

type MetalTab = "all" | "gold" | "silver" | "platinum";

const METAL_TABS: { value: MetalTab; label: string; color: string }[] = [
  { value: "all", label: "All", color: "#E8ECF1" },
  { value: "gold", label: "Gold", color: "#D4A843" },
  { value: "silver", label: "Silver", color: "#C0C0C0" },
  { value: "platinum", label: "Platinum", color: "#A0B2C6" },
];

export default function PreciousMetals() {
  const [metalTab, setMetalTab] = useState<MetalTab>("all");
  const [ownerFilter, setOwnerFilter] = useState<OwnerOption>("all");

  // The metal filter for API calls: undefined means "all metals"
  const metalFilter = metalTab === "all" ? undefined : metalTab;

  // All hooks called before any early return (Rules of Hooks)
  const { entries, isLoading: purchasesLoading, save, update, deactivate } = usePreciousMetals({
    active: true,
    metal: metalFilter,
  });
  const { data: rates, isLoading: ratesLoading } = useMetalRates();
  const { data: summary, isLoading: summaryLoading } = useMetalsSummary(metalFilter);

  const filteredEntries = useMemo(() => {
    if (ownerFilter === "all") return entries;
    return entries.filter((e) => e.owner === ownerFilter);
  }, [entries, ownerFilter]);

  const isLoading = purchasesLoading || summaryLoading;

  async function handleDeactivate(id: string) {
    if (!window.confirm("Deactivate this purchase?")) return;
    await deactivate(id);
  }

  async function handleEdit(id: string, data: PreciousMetalUpdate) {
    await update({ id, data });
  }

  if (isLoading) return <LoadingState message="Loading precious metals..." />;

  const totalWeight = summary?.total_weight_grams ?? 0;
  const totalCost = summary?.total_cost ?? 0;
  const currentValue = summary?.current_value ?? 0;
  const totalPnl = summary?.total_pnl ?? 0;
  const totalPnlPct = summary?.total_pnl_pct ?? 0;

  return (
    <div>
      <PageHeader
        title="Precious Metals"
        subtitle="Track your gold, silver & platinum holdings"
      />

      {/* Metal Tab Bar */}
      <div className="flex gap-1 bg-[#132E3D] rounded-lg p-1 border border-[#1A3A5C]/30 mb-6 w-fit">
        {METAL_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setMetalTab(tab.value)}
            className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${
              metalTab === tab.value
                ? "text-white"
                : "text-[#E8ECF1]/60 hover:text-[#E8ECF1]"
            }`}
            style={
              metalTab === tab.value
                ? { backgroundColor: tab.value === "all" ? "#00895E" : tab.color }
                : undefined
            }
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard
          label="Total Weight"
          value={totalWeight}
          prefix=""
          suffix=" g"
          color="gold"
        />
        <MetricCard
          label="Total Invested"
          value={totalCost}
          color="default"
        />
        <MetricCard
          label="Current Value"
          value={currentValue}
          color="gold"
        />
        <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
          <p className="text-sm text-[#E8ECF1]/60 mb-1">P&amp;L</p>
          <p
            className={`text-2xl font-bold ${totalPnlPct >= 0 ? "text-[#00895E]" : "text-[#E5A100]"}`}
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {totalPnlPct >= 0 ? "+" : ""}{totalPnlPct.toFixed(2)}%
          </p>
          <p
            className={`text-sm mt-1 ${totalPnl >= 0 ? "text-[#00895E]" : "text-[#E5A100]"}`}
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {totalPnl >= 0 ? "+" : ""}&nbsp;
            {`\u20B9${formatIndian(Math.round(Math.abs(totalPnl)))}`}
          </p>
        </div>
      </div>

      {/* Live Rates */}
      <MetalRateBar
        rates={rates}
        isLoading={ratesLoading}
        selectedMetal={metalTab === "all" ? null : metalTab}
      />

      {/* Controls row: owner filter */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="text-sm font-medium text-[#E8ECF1]/60">Holdings</h2>
        <OwnerFilter selected={ownerFilter} onChange={setOwnerFilter} />
      </div>

      {/* Quick-add form */}
      <MetalPurchaseForm
        onSave={save}
        lockedMetal={metalTab === "all" ? null : (metalTab as MetalType)}
      />

      {/* Holdings Table */}
      <div className="bg-[#132E3D] rounded-xl border border-[#1A3A5C]/30 overflow-hidden">
        <MetalHoldingsTable
          entries={filteredEntries}
          rates={rates}
          onDeactivate={handleDeactivate}
          onEdit={handleEdit}
        />
      </div>
    </div>
  );
}
