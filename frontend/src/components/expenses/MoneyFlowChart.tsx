import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { formatRupees } from "../../lib/formatIndian";

interface PieDataItem {
  name: string;
  value: number;
  color: string;
}

interface MoneyFlowChartProps {
  pieData: PieDataItem[];
  totalIncome: number;
}

export function MoneyFlowChart({ pieData, totalIncome }: MoneyFlowChartProps) {
  if (pieData.length === 0) return null;

  return (
    <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
      <h2 className="text-lg font-semibold text-[#E8ECF1] mb-6">
        Where Your Money Goes
      </h2>
      <div className="flex flex-col lg:flex-row items-center gap-8">
        <div className="w-64 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={3}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "#132E3D",
                  border: "1px solid #1A3A5C",
                  borderRadius: "8px",
                  color: "#E8ECF1",
                }}
                formatter={(value: unknown) => [formatRupees(Number(value)), ""]}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-col gap-3">
          {pieData.map((item) => (
            <div key={item.name} className="flex items-center gap-3">
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-sm text-[#E8ECF1]/80 w-32">{item.name}</span>
              <span className="text-sm font-medium text-[#E8ECF1]">
                {formatRupees(item.value)}
              </span>
              <span className="text-xs text-[#E8ECF1]/40">
                {totalIncome > 0
                  ? `${Math.round((item.value / totalIncome) * 100)}%`
                  : ""}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
