import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { formatIndian } from "../../lib/formatIndian";
import { trendChartData } from "../../lib/parlourCalculations";
import type { Trends } from "../../hooks/useAmulAnalytics";

interface PnLChartsProps {
  trends?: Trends;
  isLoading?: boolean;
}

export function PnLCharts({ trends, isLoading }: PnLChartsProps) {
  if (isLoading || !trends) return null;
  const data = trendChartData(trends);
  if (data.length === 0) return null;

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
      <h3 className="text-sm font-semibold text-[#E8ECF1] mb-4">
        Month-wise Trend — Sales vs Purchases vs Expenses vs Profit
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1A3A5C" opacity={0.3} />
          <XAxis
            dataKey="month"
            tickFormatter={(m) => m.slice(5)}
            tick={{ fill: "#E8ECF1", opacity: 0.5, fontSize: 11 }}
          />
          <YAxis
            tickFormatter={(v) => formatIndian(v)}
            tick={{ fill: "#E8ECF1", opacity: 0.5, fontSize: 11 }}
          />
          <Tooltip
            formatter={(value) => [`\u20B9${formatIndian(Number(value))}`, ""]}
            contentStyle={{ backgroundColor: "#0D1B2A", border: "1px solid #1A3A5C", borderRadius: 8 }}
            labelStyle={{ color: "#E8ECF1" }}
          />
          <Legend wrapperStyle={{ color: "#E8ECF1", opacity: 0.7 }} />
          <Line type="monotone" dataKey="sales" stroke="#00895E" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="purchases" stroke="#E5A100" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="expenses" stroke="#8B5CF6" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="profit" stroke="#D4A843" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
