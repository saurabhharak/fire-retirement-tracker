import { useNavigate } from "react-router-dom";
import { useLedgerContacts, useLedgerSummary } from "../../hooks/useLedgerContacts";
import { MetricCard } from "../MetricCard";
import { formatRupees } from "../../lib/formatIndian";

export function MoneyLedgerWidget() {
  const navigate = useNavigate();
  const summary = useLedgerSummary();
  const { contacts } = useLedgerContacts();

  const data = summary.data;

  // Top 3 contacts by absolute balance, skip settled/zero
  const topContacts = [...contacts]
    .filter((c) => c.balance_label !== "settled" && Math.abs(c.balance) > 0)
    .sort((a, b) => Math.abs(b.balance) - Math.abs(a.balance))
    .slice(0, 3);

  return (
    <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-[#E8ECF1]/60">
          Money Ledger
        </h3>
        <button
          onClick={() => navigate("/money-ledger")}
          className="text-xs text-[#00895E] hover:text-[#00895E]/80 font-medium transition-colors"
        >
          View All &rarr;
        </button>
      </div>

      {data ? (
        <>
          {/* 4 metric cards */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <MetricCard label="Total Given" value={Math.round(data.total_gave)} />
            <MetricCard label="Total Received" value={Math.round(data.total_received)} />

            {/* Net Balance */}
            <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
              <p className="text-sm text-[#E8ECF1]/60 mb-1">Net Balance</p>
              <p
                className={`text-2xl font-bold ${data.net_balance >= 0 ? "text-[#00895E]" : "text-[#E5A100]"}`}
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {formatRupees(Math.round(Math.abs(data.net_balance)))}
              </p>
              <p className={`text-xs mt-0.5 ${data.net_balance >= 0 ? "text-[#00895E]/70" : "text-[#E5A100]/70"}`}>
                {data.net_balance >= 0 ? "owes you" : "you owe"}
              </p>
            </div>

            {/* People count (no currency prefix) */}
            <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
              <p className="text-sm text-[#E8ECF1]/60 mb-1">People</p>
              <p
                className="text-2xl font-bold text-[#E8ECF1]"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {data.people_count}
              </p>
            </div>
          </div>

          {/* Top outstanding contacts */}
          {topContacts.length > 0 ? (
            <div className="pt-3 border-t border-white/5 space-y-2">
              <p className="text-[10px] text-[#E8ECF1]/40 uppercase tracking-wider mb-2">
                Top Outstanding
              </p>
              {topContacts.map((c) => (
                <div key={c.id} className="flex items-center justify-between">
                  <span className="text-sm text-[#E8ECF1]/70 truncate max-w-[60%]">
                    {c.name}
                  </span>
                  <div className="text-right">
                    <span
                      className={`text-sm font-semibold ${c.balance_label === "owes you" ? "text-[#00895E]" : "text-[#E5A100]"}`}
                      style={{ fontVariantNumeric: "tabular-nums" }}
                    >
                      {c.balance_label === "owes you" ? "+" : "-"}
                      {formatRupees(Math.round(Math.abs(c.balance)))}
                    </span>
                    <span className="text-[10px] text-[#E8ECF1]/40 ml-1">
                      {c.balance_label}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="pt-3 border-t border-white/5">
              <p className="text-xs text-[#E8ECF1]/40">All settled up</p>
            </div>
          )}
        </>
      ) : (
        /* Empty state */
        <div className="flex items-center justify-between py-2">
          <p className="text-sm text-[#E8ECF1]/50">No contacts yet</p>
          <button
            onClick={() => navigate("/money-ledger")}
            className="text-xs bg-[#00895E]/20 hover:bg-[#00895E]/30 text-[#00895E] px-3 py-1.5 rounded-lg font-medium transition-colors"
          >
            Add Contact &rarr;
          </button>
        </div>
      )}
    </section>
  );
}
