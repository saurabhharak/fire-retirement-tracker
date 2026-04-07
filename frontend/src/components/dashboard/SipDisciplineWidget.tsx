import { useNavigate } from "react-router-dom";
import { useSipLog } from "../../hooks/useSipLog";
import { formatRupees } from "../../lib/formatIndian";
import { MONTH_NAMES } from "../../lib/constants";

export function SipDisciplineWidget() {
  const navigate = useNavigate();
  // Fetch last 6 months
  const { entries, isLoading } = useSipLog(6);

  if (isLoading) return null;

  if (entries.length === 0) {
    return (
      <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-[#E8ECF1]/60">
            SIP Discipline
          </h3>
          <button
            onClick={() => navigate("/sip-tracker")}
            className="text-xs text-[#00895E] hover:text-[#00895E]/80 font-medium transition-colors"
          >
            View All &rarr;
          </button>
        </div>
        <div className="flex items-center justify-between py-2">
          <p className="text-sm text-[#E8ECF1]/50">Start tracking SIPs</p>
          <button
            onClick={() => navigate("/sip-tracker")}
            className="text-xs bg-[#00895E]/20 hover:bg-[#00895E]/30 text-[#00895E] px-3 py-1.5 rounded-lg font-medium transition-colors"
          >
            Set Up &rarr;
          </button>
        </div>
      </section>
    );
  }

  // Sort entries ascending by date (oldest first for chart)
  const sorted = [...entries].sort((a, b) =>
    a.year !== b.year ? a.year - b.year : a.month - b.month
  );

  // Current month = most recent entry
  const current = sorted[sorted.length - 1];

  // Discipline score: months where actual >= planned / total months
  const disciplinePct =
    sorted.length > 0
      ? Math.round(
          (sorted.filter((e) => e.actual_invested >= e.planned_sip).length /
            sorted.length) *
            100
        )
      : 0;

  // Max value for bar scaling
  const maxVal = sorted.reduce(
    (m, e) => Math.max(m, e.planned_sip, e.actual_invested),
    1
  );

  return (
    <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-[#E8ECF1]/60">
          SIP Discipline
        </h3>
        <button
          onClick={() => navigate("/sip-tracker")}
          className="text-xs text-[#00895E] hover:text-[#00895E]/80 font-medium transition-colors"
        >
          View All &rarr;
        </button>
      </div>

      {/* Current month summary + score */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
          <p className="text-sm text-[#E8ECF1]/60 mb-1">
            This Month ({MONTH_NAMES[current.month - 1]})
          </p>
          <p
            className="text-lg font-bold text-[#E8ECF1]"
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {formatRupees(Math.round(current.actual_invested))}
          </p>
          <p className="text-xs text-[#E8ECF1]/40 mt-0.5" style={{ fontVariantNumeric: "tabular-nums" }}>
            of {formatRupees(Math.round(current.planned_sip))} planned
          </p>
        </div>

        <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
          <p className="text-sm text-[#E8ECF1]/60 mb-1">Discipline Score</p>
          <p
            className={`text-2xl font-bold ${disciplinePct >= 80 ? "text-[#00895E]" : "text-[#E5A100]"}`}
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {disciplinePct}%
          </p>
        </div>
      </div>

      {/* Mini bar chart: last 6 months */}
      <div className="pt-3 border-t border-white/5">
        <p className="text-[10px] text-[#E8ECF1]/40 uppercase tracking-wider mb-3">
          Last {sorted.length} Months
        </p>
        <div className="space-y-2">
          {sorted.map((e, i) => {
            const plannedPct = Math.round((e.planned_sip / maxVal) * 100);
            const actualPct = Math.round((e.actual_invested / maxVal) * 100);
            const hit = e.actual_invested >= e.planned_sip;
            return (
              <div key={i} className="flex items-center gap-2">
                <span className="text-[10px] text-[#E8ECF1]/40 w-8 shrink-0 text-right">
                  {MONTH_NAMES[e.month - 1].slice(0, 3)}
                </span>
                <div className="flex-1 space-y-0.5">
                  {/* Planned bar */}
                  <div className="h-1.5 w-full bg-[#0D1B2A] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#1A3A5C] rounded-full"
                      style={{ width: `${plannedPct}%` }}
                    />
                  </div>
                  {/* Actual bar */}
                  <div className="h-1.5 w-full bg-[#0D1B2A] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${hit ? "bg-[#00895E]" : "bg-[#E5A100]"}`}
                      style={{ width: `${actualPct}%` }}
                    />
                  </div>
                </div>
                <span
                  className={`text-[10px] w-2 shrink-0 ${hit ? "text-[#00895E]" : "text-[#E5A100]"}`}
                >
                  {hit ? "+" : "-"}
                </span>
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 mt-3">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1.5 bg-[#1A3A5C] rounded-full inline-block" />
            <span className="text-[10px] text-[#E8ECF1]/40">Planned</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1.5 bg-[#00895E] rounded-full inline-block" />
            <span className="text-[10px] text-[#E8ECF1]/40">Actual (met)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1.5 bg-[#E5A100] rounded-full inline-block" />
            <span className="text-[10px] text-[#E8ECF1]/40">Actual (short)</span>
          </div>
        </div>
      </div>
    </section>
  );
}
