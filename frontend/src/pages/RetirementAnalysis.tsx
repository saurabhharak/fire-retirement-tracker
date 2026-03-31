import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useRetirementAnalysis } from "../hooks/useProjections";
import { PageHeader } from "../components/PageHeader";
import { MetricCard } from "../components/MetricCard";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { formatRupees } from "../lib/formatIndian";

const BUCKET_COLORS: Record<string, string> = {
  Safety: "#1A8A7A",
  Income: "#00895E",
  Growth: "#D4A843",
};

interface BucketTooltipPayloadEntry {
  name: string;
  value: number;
  payload: { name: string; pct: number; amount: number; coverage_years: number };
}

function BucketTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: BucketTooltipPayloadEntry[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-[#132E3D] border border-[#1A3A5C] rounded-lg p-3 text-sm text-[#E8ECF1]">
      <p className="font-semibold text-[#D4A843] mb-1">{d.name} Bucket</p>
      <p>Allocation: {d.pct}%</p>
      <p>Amount: {formatRupees(d.amount)}</p>
      <p>Coverage: {d.coverage_years} years</p>
    </div>
  );
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const lower = verdict.toLowerCase();
  let bgColor = "bg-[#1A3A5C]";
  let textColor = "text-[#E8ECF1]";

  if (lower.includes("safe") || lower.includes("comfort") || lower.includes("good")) {
    bgColor = "bg-[#00895E]/20";
    textColor = "text-[#00895E]";
  } else if (lower.includes("tight") || lower.includes("risk") || lower.includes("caution")) {
    bgColor = "bg-[#E5A100]/20";
    textColor = "text-[#E5A100]";
  } else if (lower.includes("danger") || lower.includes("fail") || lower.includes("short")) {
    bgColor = "bg-[#C45B5B]/20";
    textColor = "text-[#C45B5B]";
  }

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${bgColor} ${textColor}`}>
      {verdict}
    </span>
  );
}

export default function RetirementAnalysis() {
  const { data, isLoading } = useRetirementAnalysis();

  if (isLoading) return <LoadingState message="Analysing retirement readiness..." />;
  if (!data)
    return <EmptyState message="No retirement analysis data. Configure your FIRE settings first." />;

  const bucketChartData = data.buckets.map((b) => ({
    name: b.name,
    pct: b.pct,
    amount: b.amount,
    coverage_years: b.coverage_years,
  }));

  return (
    <div>
      <PageHeader
        title="Retirement Analysis"
        subtitle="Evaluate your FIRE readiness with multiple withdrawal strategies"
      />

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
        <MetricCard label="Corpus" value={data.corpus} color="gold" />
        <MetricCard label="Annual Expense" value={data.annual_expense} />
        <MetricCard label="Monthly SWP" value={data.monthly_swp} />
        <MetricCard label="Monthly Expense" value={data.monthly_expense} />
        <MetricCard
          label="Surplus"
          value={data.surplus}
          color={data.surplus >= 0 ? "success" : "warning"}
        />
        <MetricCard
          label="Funded Ratio"
          value={data.funded_ratio}
          prefix=""
          suffix="x"
          color={data.funded_ratio >= 1 ? "success" : "warning"}
        />
        <MetricCard label="Required Corpus" value={data.required_corpus} />
      </div>

      {/* 3-Bucket Strategy */}
      <div className="bg-[#132E3D] rounded-xl p-5 border border-[#1A3A5C]/30 mb-6">
        <h2 className="text-lg font-semibold text-[#E8ECF1] mb-4">3-Bucket Strategy</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          {data.buckets.map((b) => (
            <div
              key={b.name}
              className="rounded-lg p-3 border border-[#1A3A5C]/30"
              style={{ backgroundColor: `${BUCKET_COLORS[b.name] ?? "#1A3A5C"}15` }}
            >
              <div className="flex items-center gap-2 mb-1">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: BUCKET_COLORS[b.name] ?? "#1A3A5C" }}
                />
                <span className="text-sm font-medium text-[#E8ECF1]">{b.name}</span>
              </div>
              <p className="text-xl font-bold text-[#E8ECF1]">{b.pct}%</p>
              <p className="text-xs text-[#E8ECF1]/60">
                {formatRupees(b.amount)} &middot; {b.coverage_years}yr coverage
              </p>
            </div>
          ))}
        </div>

        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={bucketChartData} layout="vertical" margin={{ left: 60, right: 20 }}>
            <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12, fill: "#E8ECF1" }} opacity={0.4} unit="%" />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 12, fill: "#E8ECF1" }}
              opacity={0.6}
              width={55}
            />
            <Tooltip content={<BucketTooltip />} />
            <Bar dataKey="pct" radius={[0, 6, 6, 0]} barSize={28}>
              {bucketChartData.map((entry) => (
                <Cell key={entry.name} fill={BUCKET_COLORS[entry.name] ?? "#1A3A5C"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* SWR Comparison */}
      <div className="bg-[#132E3D] rounded-xl p-5 border border-[#1A3A5C]/30">
        <h2 className="text-lg font-semibold text-[#E8ECF1] mb-4">
          Safe Withdrawal Rate Comparison
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-[#E8ECF1]">
            <thead>
              <tr className="border-b border-[#1A3A5C]">
                <th className="px-3 py-2 text-left text-[#E8ECF1]/60 font-medium">SWR</th>
                <th className="px-3 py-2 text-left text-[#E8ECF1]/60 font-medium">Annual</th>
                <th className="px-3 py-2 text-left text-[#E8ECF1]/60 font-medium">Monthly</th>
                <th className="px-3 py-2 text-left text-[#E8ECF1]/60 font-medium">vs Expense</th>
                <th className="px-3 py-2 text-left text-[#E8ECF1]/60 font-medium">Verdict</th>
              </tr>
            </thead>
            <tbody>
              {data.swr_scenarios.map((s) => {
                const isHighlighted = s.rate === 3;
                return (
                  <tr
                    key={s.rate}
                    className={`border-b border-[#1A3A5C]/30 ${
                      isHighlighted ? "bg-[#D4A843]/10" : ""
                    }`}
                  >
                    <td className={`px-3 py-2 font-medium ${isHighlighted ? "text-[#D4A843]" : ""}`}>
                      {s.rate}%
                    </td>
                    <td className="px-3 py-2">{formatRupees(s.annual)}</td>
                    <td className="px-3 py-2">{formatRupees(s.monthly)}</td>
                    <td
                      className={`px-3 py-2 ${
                        s.vs_expense >= 0 ? "text-[#00895E]" : "text-[#E5A100]"
                      }`}
                    >
                      {s.vs_expense >= 0 ? "+" : ""}
                      {formatRupees(s.vs_expense)}
                    </td>
                    <td className="px-3 py-2">
                      <VerdictBadge verdict={s.verdict} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
