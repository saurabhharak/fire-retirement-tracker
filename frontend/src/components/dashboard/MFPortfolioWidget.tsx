import { useNavigate } from "react-router-dom";
import { useKitePortfolio } from "../../hooks/useKitePortfolio";
import { MetricCard } from "../MetricCard";
import { formatRupees } from "../../lib/formatIndian";

function timeSince(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function MFPortfolioWidget() {
  const navigate = useNavigate();
  const { status, portfolio } = useKitePortfolio();

  const isConnected = status?.connected && !status?.is_expired;

  return (
    <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-[#E8ECF1]/60">
          MF Portfolio
        </h3>
        <button
          onClick={() => navigate("/mf-portfolio")}
          className="text-xs text-[#00895E] hover:text-[#00895E]/80 font-medium transition-colors"
        >
          View All &rarr;
        </button>
      </div>

      {isConnected && portfolio ? (
        <>
          {/* Row 1: Invested / Current / P&L */}
          <div className="grid grid-cols-3 gap-3 mb-3">
            <MetricCard label="Invested" value={Math.round(portfolio.total_invested)} />
            <MetricCard
              label="Current Value"
              value={Math.round(portfolio.current_value)}
              color="success"
            />
            <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
              <p className="text-sm text-[#E8ECF1]/60 mb-1">P&amp;L</p>
              <p
                className={`text-2xl font-bold ${portfolio.total_pnl >= 0 ? "text-[#00895E]" : "text-[#E5A100]"}`}
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {portfolio.total_pnl >= 0 ? "+" : ""}
                {formatRupees(Math.round(portfolio.total_pnl))}
              </p>
              <p
                className={`text-xs mt-0.5 ${portfolio.pnl_pct >= 0 ? "text-[#00895E]/70" : "text-[#E5A100]/70"}`}
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {portfolio.pnl_pct >= 0 ? "+" : ""}
                {portfolio.pnl_pct.toFixed(2)}%
              </p>
            </div>
          </div>

          {/* Row 2: Monthly SIP / Active SIPs */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <MetricCard label="Monthly SIP" value={Math.round(portfolio.total_monthly_sip)} />
            <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
              <p className="text-sm text-[#E8ECF1]/60 mb-1">Active SIPs</p>
              <p
                className="text-2xl font-bold text-[#E8ECF1]"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {portfolio.active_sip_count}
              </p>
            </div>
          </div>

          {/* Sync status */}
          <div className="pt-3 border-t border-white/5">
            <p className="text-xs text-[#E8ECF1]/40">
              Connected to Zerodha &mdash; Synced{" "}
              {timeSince(portfolio.synced_at)}
              {portfolio.is_stale && (
                <span className="ml-1 text-[#E5A100]">(stale)</span>
              )}
            </p>
          </div>
        </>
      ) : (
        /* Not connected prompt */
        <div className="flex items-center justify-between py-2">
          <p className="text-sm text-[#E8ECF1]/50">
            Connect Zerodha to see live portfolio
          </p>
          <button
            onClick={() => navigate("/mf-portfolio")}
            className="text-xs bg-[#00895E]/20 hover:bg-[#00895E]/30 text-[#00895E] px-3 py-1.5 rounded-lg font-medium transition-colors"
          >
            Connect &rarr;
          </button>
        </div>
      )}
    </section>
  );
}
