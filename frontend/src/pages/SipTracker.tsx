import { useState } from "react";
import { useSipLog } from "../hooks/useSipLog";
import type { SipLogEntry } from "../hooks/useSipLog";
import { useMonthlySips } from "../hooks/useProjections";
import { PageHeader } from "../components/PageHeader";
import { MetricCard } from "../components/MetricCard";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { formatRupees } from "../lib/formatIndian";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function getNextSipDate(currentDate: Date, currentYear: number): string {
  const next = new Date(currentYear, currentDate.getMonth() + 1, 1);
  return `${MONTHS[next.getMonth()]} ${next.getFullYear()}`;
}

export default function SipTracker() {
  const currentDate = new Date();
  const currentMonth = currentDate.getMonth() + 1;
  const currentYear = currentDate.getFullYear();

  const { entries, isLoading, save } = useSipLog();
  const { data: monthlySips } = useMonthlySips();

  const [month, setMonth] = useState(currentMonth);
  const [year, setYear] = useState(currentYear);
  const [actualInvested, setActualInvested] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // monthlySips is a flat array of 192 planned values starting from the current month.
  // Use index 0 for the current month's planned SIP target.
  const monthlyTarget = monthlySips?.[0] ?? 0;
  const totalInvested = entries.reduce((s, e) => s + e.actual_invested, 0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const amount = Number(actualInvested);
    if (!amount || amount <= 0) {
      setError("Please enter a valid investment amount.");
      return;
    }

    setSaving(true);
    try {
      const entry: SipLogEntry = {
        month,
        year,
        planned_sip: monthlyTarget,
        actual_invested: amount,
        notes,
        funds: [],
      };
      await save(entry);
      setActualInvested("");
      setNotes("");
    } catch {
      setError("Failed to save entry. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (isLoading) return <LoadingState message="Loading SIP history..." />;

  return (
    <div>
      <PageHeader
        title="SIP Tracker"
        subtitle="Track monthly SIP investments against your plan"
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
        <MetricCard label="Total Invested" value={totalInvested} color="gold" />
        <MetricCard label="Monthly Target" value={monthlyTarget} color="success" />
        <MetricCard label="Next SIP Date" value={0} prefix="" suffix={getNextSipDate(currentDate, currentYear)} />
      </div>

      {/* Log Form */}
      <div className="bg-[#132E3D] rounded-xl p-5 border border-[#1A3A5C]/30 mb-6">
        <h2 className="text-lg font-semibold text-[#E8ECF1] mb-4">Log SIP Entry</h2>
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
          <div>
            <label className="block text-sm text-[#E8ECF1]/60 mb-1">Month</label>
            <select
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              className="w-full px-3 py-2 bg-[#0D1B2A] border border-[#1A3A5C] rounded-lg text-[#E8ECF1] text-sm focus:outline-none focus:border-[#00895E]"
            >
              {MONTHS.map((m, i) => (
                <option key={m} value={i + 1}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-[#E8ECF1]/60 mb-1">Year</label>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              min={2020}
              max={2050}
              className="w-full px-3 py-2 bg-[#0D1B2A] border border-[#1A3A5C] rounded-lg text-[#E8ECF1] text-sm focus:outline-none focus:border-[#00895E]"
            />
          </div>
          <div>
            <label className="block text-sm text-[#E8ECF1]/60 mb-1">Actual Invested</label>
            <input
              type="number"
              value={actualInvested}
              onChange={(e) => setActualInvested(e.target.value)}
              placeholder="e.g. 50000"
              className="w-full px-3 py-2 bg-[#0D1B2A] border border-[#1A3A5C] rounded-lg text-[#E8ECF1] text-sm focus:outline-none focus:border-[#00895E]"
            />
          </div>
          <div>
            <label className="block text-sm text-[#E8ECF1]/60 mb-1">Notes</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional notes"
              className="w-full px-3 py-2 bg-[#0D1B2A] border border-[#1A3A5C] rounded-lg text-[#E8ECF1] text-sm focus:outline-none focus:border-[#00895E]"
            />
          </div>
          <div>
            <button
              type="submit"
              disabled={saving}
              className="w-full px-4 py-2 bg-[#00895E] text-white rounded-lg hover:bg-[#00895E]/80 transition-colors disabled:opacity-50 text-sm font-medium"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
        {error && <p className="mt-2 text-sm text-[#E5A100]">{error}</p>}
      </div>

      {/* History Table */}
      {entries.length === 0 ? (
        <EmptyState message="No SIP log entries yet. Use the form above to start tracking." />
      ) : (
        <div className="bg-[#132E3D] rounded-xl border border-[#1A3A5C]/30 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-[#E8ECF1]">
              <thead>
                <tr className="border-b border-[#1A3A5C]">
                  {["Month", "Year", "Planned", "Actual", "Difference", "Notes"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-[#E8ECF1]/60 font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entries.map((entry: SipLogEntry, idx: number) => {
                  const diff = entry.actual_invested - entry.planned_sip;
                  const diffColor = diff >= 0 ? "text-[#00895E]" : "text-[#E5A100]";
                  return (
                    <tr key={idx} className="border-b border-[#1A3A5C]/20 hover:bg-[#1A3A5C]/10">
                      <td className="px-4 py-3">{MONTHS[entry.month - 1]}</td>
                      <td className="px-4 py-3">{entry.year}</td>
                      <td className="px-4 py-3">{formatRupees(entry.planned_sip)}</td>
                      <td className="px-4 py-3">{formatRupees(entry.actual_invested)}</td>
                      <td className={`px-4 py-3 font-medium ${diffColor}`}>
                        {diff >= 0 ? "+" : ""}
                        {formatRupees(diff)}
                      </td>
                      <td className="px-4 py-3 text-[#E8ECF1]/60">{entry.notes || "\u2014"}</td>
                    </tr>
                  );
                })}
                {/* Running total */}
                <tr className="border-t-2 border-[#D4A843]/30 bg-[#0D1B2A]/40">
                  <td colSpan={2} className="px-4 py-3 font-bold text-[#D4A843]">
                    Running Total
                  </td>
                  <td className="px-4 py-3 font-bold text-[#D4A843]">
                    {formatRupees(entries.reduce((s, e) => s + e.planned_sip, 0))}
                  </td>
                  <td className="px-4 py-3 font-bold text-[#D4A843]">
                    {formatRupees(totalInvested)}
                  </td>
                  <td className="px-4 py-3 font-bold text-[#D4A843]">
                    {formatRupees(totalInvested - entries.reduce((s, e) => s + e.planned_sip, 0))}
                  </td>
                  <td className="px-4 py-3" />
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
