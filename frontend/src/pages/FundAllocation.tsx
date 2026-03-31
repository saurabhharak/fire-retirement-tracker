import { useFundAllocation } from "../hooks/useProjections";
import type { FundAllocationRow } from "../hooks/useProjections";
import { PageHeader } from "../components/PageHeader";
import { MetricCard } from "../components/MetricCard";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { formatRupees } from "../lib/formatIndian";

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  Equity: { bg: "bg-[#00895E]/20", text: "text-[#00895E]" },
  Debt: { bg: "bg-[#1A8A7A]/20", text: "text-[#1A8A7A]" },
  Gold: { bg: "bg-[#D4A843]/20", text: "text-[#D4A843]" },
  Cash: { bg: "bg-[#E8ECF1]/10", text: "text-[#E8ECF1]/80" },
};

function CategoryBadge({ category }: { category: string }) {
  const style = CATEGORY_COLORS[category] ?? { bg: "bg-[#1A3A5C]/30", text: "text-[#E8ECF1]/70" };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}>
      {category}
    </span>
  );
}

function groupByCategory(funds: FundAllocationRow[]): Map<string, FundAllocationRow[]> {
  const groups = new Map<string, FundAllocationRow[]>();
  for (const fund of funds) {
    const existing = groups.get(fund.category) ?? [];
    existing.push(fund);
    groups.set(fund.category, existing);
  }
  return groups;
}

export default function FundAllocation() {
  const { data, isLoading } = useFundAllocation();

  if (isLoading) return <LoadingState message="Loading fund allocation..." />;
  if (!data || data.length === 0)
    return <EmptyState message="No fund allocation data available." />;

  const totalSip = data.reduce((s, f) => s + f.monthly_sip, 0);
  const equityPct = data.filter((f) => f.category === "Equity").reduce((s, f) => s + f.pct, 0);
  const debtPct = data.filter((f) => f.category === "Debt").reduce((s, f) => s + f.pct, 0);
  const cashPct = data
    .filter((f) => f.category !== "Equity" && f.category !== "Debt")
    .reduce((s, f) => s + f.pct, 0);

  const grouped = groupByCategory(data);

  return (
    <div>
      <PageHeader
        title="Fund Allocation"
        subtitle="Your mutual fund portfolio breakdown and SIP distribution"
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard label="Total SIP" value={totalSip} color="gold" />
        <MetricCard label="Equity" value={equityPct} prefix="" suffix="%" color="success" />
        <MetricCard label="Debt" value={debtPct} prefix="" suffix="%" />
        <MetricCard label="Cash / Gold" value={cashPct} prefix="" suffix="%" />
      </div>

      {/* Fund Table */}
      <div className="bg-[#132E3D] rounded-xl border border-[#1A3A5C]/30 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-[#E8ECF1]">
            <thead>
              <tr className="border-b border-[#1A3A5C]">
                {["Fund Name", "Category", "% of Portfolio", "Monthly SIP", "Account"].map(
                  (h) => (
                    <th key={h} className="px-4 py-3 text-left text-[#E8ECF1]/60 font-medium">
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {[...grouped.entries()].map(([category, funds]) => (
                <GroupRows key={category} category={category} funds={funds} />
              ))}
              {/* Total row */}
              <tr className="border-t-2 border-[#D4A843]/30 bg-[#0D1B2A]/40">
                <td className="px-4 py-3 font-bold text-[#D4A843]">Total</td>
                <td className="px-4 py-3" />
                <td className="px-4 py-3 font-bold text-[#D4A843]">
                  {data.reduce((s, f) => s + f.pct, 0).toFixed(1)}%
                </td>
                <td className="px-4 py-3 font-bold text-[#D4A843]">{formatRupees(totalSip)}</td>
                <td className="px-4 py-3" />
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function GroupRows({ category, funds }: { category: string; funds: FundAllocationRow[] }) {
  return (
    <>
      {/* Category header row */}
      <tr className="bg-[#0D1B2A]/30">
        <td colSpan={5} className="px-4 py-2">
          <span className="text-xs font-semibold text-[#E8ECF1]/50 uppercase tracking-wider">
            {category} Funds
          </span>
        </td>
      </tr>
      {funds.map((fund) => (
        <tr key={fund.name} className="border-b border-[#1A3A5C]/20 hover:bg-[#1A3A5C]/10">
          <td className="px-4 py-3">{fund.name}</td>
          <td className="px-4 py-3">
            <CategoryBadge category={fund.category} />
          </td>
          <td className="px-4 py-3">{fund.pct.toFixed(1)}%</td>
          <td className="px-4 py-3">{formatRupees(fund.monthly_sip)}</td>
          <td className="px-4 py-3 text-[#E8ECF1]/60">{fund.account}</td>
        </tr>
      ))}
    </>
  );
}
