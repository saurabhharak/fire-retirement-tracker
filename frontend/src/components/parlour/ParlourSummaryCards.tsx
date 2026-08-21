import { MetricCard } from "../MetricCard";
import type { PnLSummary } from "../../hooks/useAmulAnalytics";

interface ParlourSummaryCardsProps {
  summary?: PnLSummary;
  isLoading?: boolean;
}

export function ParlourSummaryCards({ summary, isLoading }: ParlourSummaryCardsProps) {
  if (isLoading || !summary) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <MetricCard label="Total Sales" value={summary.total_sales} color="success" />
      <MetricCard label="Total Purchases" value={summary.total_purchases} color="warning" />
      <MetricCard label="Other Expenses" value={summary.total_expenses ?? 0} color="warning" />
      <MetricCard
        label="Profit"
        value={summary.profit}
        color={summary.profit >= 0 ? "success" : "warning"}
      />
    </div>
  );
}
