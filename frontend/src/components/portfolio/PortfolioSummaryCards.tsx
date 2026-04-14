import { MetricCard } from "../MetricCard";
import type { KitePortfolio } from "../../hooks/useKitePortfolio";

interface Props {
  portfolio: KitePortfolio | undefined;
  isLoading: boolean;
}

export function PortfolioSummaryCards({ portfolio, isLoading }: Props) {
  if (isLoading || !portfolio) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 animate-pulse h-20" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
      <MetricCard label="Total Invested" value={portfolio.total_invested} color="default" />
      <MetricCard label="Current Value" value={portfolio.current_value} color="gold" />
      <MetricCard
        label="Total P&L"
        value={portfolio.total_pnl}
        suffix={` (${portfolio.pnl_pct >= 0 ? "+" : ""}${portfolio.pnl_pct.toFixed(1)}%)`}
        color={portfolio.total_pnl >= 0 ? "success" : "warning"}
      />
      <MetricCard label="Monthly SIP" value={portfolio.total_monthly_sip} color="default" />
      <MetricCard label="Active SIPs" value={portfolio.active_sip_count} prefix="" color="default" />
      <MetricCard
        label="Holdings Count"
        value={portfolio.holdings.length}
        prefix=""
        suffix={` funds`}
        color="default"
      />
    </div>
  );
}
