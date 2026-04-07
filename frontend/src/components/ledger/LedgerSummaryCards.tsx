import { MetricCard } from "../MetricCard";
import type { LedgerSummary } from "../../hooks/useLedgerContacts";

interface Props {
  summary: LedgerSummary | undefined;
  isLoading: boolean;
}

export function LedgerSummaryCards({ summary, isLoading }: Props) {
  if (isLoading || !summary) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 animate-pulse h-20"
          />
        ))}
      </div>
    );
  }

  const netColor =
    summary.net_balance > 0
      ? "success"
      : summary.net_balance < 0
      ? "warning"
      : "default";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <MetricCard label="Total Given" value={summary.total_gave} color="gold" />
      <MetricCard
        label="Total Received"
        value={summary.total_received}
        color="success"
      />
      <MetricCard
        label="Net Balance"
        value={Math.abs(summary.net_balance)}
        suffix={
          summary.net_balance > 0
            ? " (owed to you)"
            : summary.net_balance < 0
            ? " (you owe)"
            : " (settled)"
        }
        color={netColor}
      />
      <MetricCard
        label="People"
        value={summary.people_count}
        prefix=""
        color="default"
      />
    </div>
  );
}
