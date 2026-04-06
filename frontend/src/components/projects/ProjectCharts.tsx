import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid,
} from "recharts";
import { formatIndian } from "../../lib/formatIndian";
import type { ProjectSummary } from "../../hooks/useProjectExpenses";

interface Props {
  summary: ProjectSummary | undefined;
}

export function ProjectCharts({ summary }: Props) {
  const [open, setOpen] = useState(false);

  if (!summary) return null;

  const categoryData = Object.entries(summary.category_totals)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  const monthlyData = Object.entries(summary.monthly_totals)
    .map(([month, value]) => ({ month, value }))
    .sort((a, b) => a.month.localeCompare(b.month));

  return (
    <div className="mt-6">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm text-[#E8ECF1]/60 hover:text-[#E8ECF1] transition-colors mb-3"
      >
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        {open ? "Hide Charts" : "Show Charts"}
      </button>

      {open && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Category Bar Chart */}
          <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
            <h3 className="text-sm font-medium text-[#E8ECF1]/60 mb-3">Spending by Category</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={categoryData} layout="vertical" margin={{ left: 100 }}>
                <XAxis type="number" tickFormatter={(v) => `\u20B9${formatIndian(v)}`}
                  tick={{ fill: "#E8ECF1", opacity: 0.5, fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={90}
                  tick={{ fill: "#E8ECF1", opacity: 0.7, fontSize: 11 }} />
                <Tooltip
                  formatter={(v: number) => [`\u20B9${formatIndian(v)}`, "Spent"]}
                  contentStyle={{ backgroundColor: "#0D1B2A", border: "1px solid #1A3A5C", borderRadius: 8 }}
                  labelStyle={{ color: "#E8ECF1" }}
                  itemStyle={{ color: "#D4A843" }}
                />
                <Bar dataKey="value" fill="#D4A843" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Monthly Line Chart */}
          <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
            <h3 className="text-sm font-medium text-[#E8ECF1]/60 mb-3">Monthly Spending Trend</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1A3A5C" opacity={0.3} />
                <XAxis dataKey="month"
                  tick={{ fill: "#E8ECF1", opacity: 0.5, fontSize: 11 }}
                  tickFormatter={(m) => m.slice(5)} />
                <YAxis tickFormatter={(v) => `${formatIndian(v)}`}
                  tick={{ fill: "#E8ECF1", opacity: 0.5, fontSize: 11 }} />
                <Tooltip
                  formatter={(v: number) => [`\u20B9${formatIndian(v)}`, "Spent"]}
                  contentStyle={{ backgroundColor: "#0D1B2A", border: "1px solid #1A3A5C", borderRadius: 8 }}
                  labelStyle={{ color: "#E8ECF1" }}
                  itemStyle={{ color: "#00895E" }}
                />
                <Line type="monotone" dataKey="value" stroke="#00895E" strokeWidth={2}
                  dot={{ fill: "#00895E", r: 3 }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
