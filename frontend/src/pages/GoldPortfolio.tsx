import { useState, useMemo } from "react";
import { useGoldPurchases } from "../hooks/useGoldPurchases";
import { useGoldRate } from "../hooks/useGoldRate";
import { useGoldSummary } from "../hooks/useGoldSummary";
import { PageHeader } from "../components/PageHeader";
import { MetricCard } from "../components/MetricCard";
import { LoadingState } from "../components/LoadingState";
import { OwnerFilter } from "../components/expenses/OwnerFilter";
import type { OwnerOption } from "../components/expenses/OwnerFilter";
import { GoldRateBar } from "../components/gold/GoldRateBar";
import { GoldPurchaseForm } from "../components/gold/GoldPurchaseForm";
import { GoldHoldingsTable } from "../components/gold/GoldHoldingsTable";
import { formatIndian } from "../lib/formatIndian";

export default function GoldPortfolio() {
  // All hooks must be called before any early return (Rules of Hooks)
  const { entries, isLoading: purchasesLoading, save, update, deactivate } = useGoldPurchases({ active: true });
  const { rate, isLoading: rateLoading } = useGoldRate();
  const { summary, isLoading: summaryLoading } = useGoldSummary();

  const [ownerFilter, setOwnerFilter] = useState<OwnerOption>("all");

  const filteredEntries = useMemo(() => {
    if (ownerFilter === "all") return entries;
    return entries.filter((e) => e.owner === ownerFilter);
  }, [entries, ownerFilter]);

  const isLoading = purchasesLoading || summaryLoading;

  async function handleGoldDeactivate(id: string) {
    if (!window.confirm("Deactivate this gold purchase?")) return;
    await deactivate(id);
  }

  async function handleGoldEdit(id: string, data: import("../hooks/useGoldPurchases").GoldPurchaseUpdate) {
    await update({ id, data });
  }

  if (isLoading) return <LoadingState message="Loading gold portfolio..." />;

  const totalWeight = summary?.total_weight_grams ?? 0;
  const totalCost = summary?.total_cost ?? 0;
  const currentValue = summary?.current_value ?? 0;
  const totalPnlPct = summary?.total_pnl_pct ?? 0;

  return (
    <div>
      <PageHeader
        title="Gold Portfolio"
        subtitle="Track your physical gold holdings"
      />

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
          {summary && (
            <p
              className={`text-sm mt-1 ${totalPnlPct >= 0 ? "text-[#00895E]" : "text-[#E5A100]"}`}
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {summary.total_pnl >= 0 ? "+" : ""}&nbsp;
              {`\u20B9${formatIndian(Math.round(Math.abs(summary.total_pnl)))}`}
            </p>
          )}
        </div>
      </div>

      {/* Live Rates */}
      <GoldRateBar rate={rate} isLoading={rateLoading} />

      {/* Controls row: owner filter */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="text-sm font-medium text-[#E8ECF1]/60">Holdings</h2>
        <OwnerFilter selected={ownerFilter} onChange={setOwnerFilter} />
      </div>

      {/* Quick-add form */}
      <GoldPurchaseForm onSave={save} />

      {/* Holdings Table */}
      <div className="bg-[#132E3D] rounded-xl border border-[#1A3A5C]/30 overflow-hidden">
        <GoldHoldingsTable
          entries={filteredEntries}
          rate={rate}
          onDeactivate={handleGoldDeactivate}
          onEdit={handleGoldEdit}
        />
      </div>
    </div>
  );
}
