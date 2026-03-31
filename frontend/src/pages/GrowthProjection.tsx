import { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { useGrowthProjection } from "../hooks/useProjections";
import type { GrowthRow } from "../hooks/useProjections";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { formatRupees, formatIndian } from "../lib/formatIndian";

const EQUITY_COLOR = "#00895E";
const DEBT_COLOR = "#1A3A5C";
const GOLD_LINE = "#D4A843";

function formatCrLk(value: number): string {
  if (value >= 1_00_00_000) return `${(value / 1_00_00_000).toFixed(1)} Cr`;
  if (value >= 1_00_000) return `${(value / 1_00_000).toFixed(1)} L`;
  return formatIndian(value);
}

interface ChartPayloadEntry {
  name: string;
  value: number;
  color: string;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: ChartPayloadEntry[];
  label?: number;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#132E3D] border border-[#1A3A5C] rounded-lg p-3 text-sm">
      <p className="text-[#D4A843] font-semibold mb-1">Age {label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }}>
          {entry.name}: {formatRupees(entry.value)}
        </p>
      ))}
    </div>
  );
}

export default function GrowthProjection() {
  const { data, isLoading } = useGrowthProjection();
  const [showTable, setShowTable] = useState(true);

  if (isLoading) return <LoadingState message="Calculating projections..." />;
  if (!data || data.length === 0)
    return <EmptyState message="No projection data available. Configure your FIRE settings first." />;

  const lastRow = data[data.length - 1];
  const retirementAge = 50;
  const retirementRow = data.find((r) => r.age >= retirementAge);
  const corpusAtRetirement = retirementRow?.portfolio ?? lastRow.portfolio;

  return (
    <div>
      <PageHeader
        title="Growth Projection"
        subtitle="Visualise your portfolio trajectory to financial independence"
      />

      {/* Hero number */}
      <div className="bg-[#132E3D] rounded-xl p-6 border border-[#1A3A5C]/30 mb-6 text-center">
        <p className="text-sm text-[#E8ECF1]/60 mb-1">
          Corpus at Retirement (Age {retirementRow?.age ?? retirementAge})
        </p>
        <p className="text-4xl md:text-5xl font-bold text-[#D4A843]">
          {formatRupees(corpusAtRetirement)}
        </p>
      </div>

      {/* Area Chart */}
      <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
        <ResponsiveContainer width="100%" height={360}>
          <AreaChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={EQUITY_COLOR} stopOpacity={0.6} />
                <stop offset="95%" stopColor={EQUITY_COLOR} stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="debtGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={DEBT_COLOR} stopOpacity={0.6} />
                <stop offset="95%" stopColor={DEBT_COLOR} stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="age"
              stroke="#E8ECF1"
              opacity={0.4}
              tick={{ fontSize: 12 }}
              label={{ value: "Age", position: "insideBottom", offset: -2, fill: "#E8ECF1", opacity: 0.6 }}
            />
            <YAxis
              stroke="#E8ECF1"
              opacity={0.4}
              tick={{ fontSize: 12 }}
              tickFormatter={formatCrLk}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine
              x={retirementAge}
              stroke={GOLD_LINE}
              strokeDasharray="6 4"
              strokeWidth={2}
              label={{ value: "Retire", fill: GOLD_LINE, fontSize: 12, position: "top" }}
            />
            <Area
              type="monotone"
              dataKey="debt_gold_cash"
              stackId="1"
              stroke={DEBT_COLOR}
              fill="url(#debtGrad)"
              name="Debt + Gold + Cash"
            />
            <Area
              type="monotone"
              dataKey="equity_value"
              stackId="1"
              stroke={EQUITY_COLOR}
              fill="url(#equityGrad)"
              name="Equity"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Toggle table */}
      <button
        onClick={() => setShowTable((v) => !v)}
        className="mb-4 px-4 py-2 text-sm rounded-lg border border-[#1A3A5C] text-[#E8ECF1]/80 hover:bg-[#1A3A5C]/30 transition-colors"
      >
        {showTable ? "Hide" : "Show"} Data Table
      </button>

      {/* Data Table */}
      {showTable && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-[#E8ECF1]">
            <thead>
              <tr className="border-b border-[#1A3A5C]">
                {["Year", "Age", "Monthly SIP", "Annual Inv", "Cumulative", "Portfolio", "Gains"].map(
                  (h) => (
                    <th key={h} className="px-3 py-2 text-left text-[#E8ECF1]/60 font-medium">
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {data.map((row: GrowthRow) => (
                <tr
                  key={row.year}
                  className={`border-b border-[#1A3A5C]/30 ${
                    row.age === retirementAge ? "bg-[#D4A843]/10" : ""
                  }`}
                >
                  <td className="px-3 py-2">{row.year}</td>
                  <td className="px-3 py-2">{row.age}</td>
                  <td className="px-3 py-2">{formatRupees(row.monthly_sip)}</td>
                  <td className="px-3 py-2">{formatRupees(row.annual_inv)}</td>
                  <td className="px-3 py-2">{formatRupees(row.cumulative)}</td>
                  <td className="px-3 py-2 font-semibold text-[#D4A843]">
                    {formatRupees(row.portfolio)}
                  </td>
                  <td className="px-3 py-2 text-[#00895E]">{formatRupees(row.gains)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
