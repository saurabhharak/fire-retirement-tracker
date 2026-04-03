import type { GoldPurchaseEntry, GoldPurity, GoldOwner } from "../../hooks/useGoldPurchases";
import type { GoldRate } from "../../hooks/useGoldRate";
import { formatRupees } from "../../lib/formatIndian";

interface GoldHoldingsTableProps {
  entries: GoldPurchaseEntry[];
  rate: GoldRate | null;
  onDeactivate: (id: string) => void;
}

function ownerBadge(owner: GoldOwner) {
  const cls =
    owner === "you"
      ? "bg-[#D4A843]/20 text-[#D4A843]"
      : owner === "wife"
        ? "bg-[#E07A5F]/20 text-[#E07A5F]"
        : "bg-[#6B7280]/20 text-[#6B7280]";
  const label =
    owner === "you" ? "You" : owner === "wife" ? "Wife" : "Household";
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>
      {label}
    </span>
  );
}

function purityBadge(purity: GoldPurity) {
  const cls =
    purity === "24K"
      ? "bg-[#D4A843]/20 text-[#D4A843]"
      : purity === "22K"
        ? "bg-[#D4A843]/10 text-[#D4A843]/60"
        : "bg-[#6B7280]/20 text-[#6B7280]";
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>
      {purity}
    </span>
  );
}

function getRateForPurity(rate: GoldRate | null, purity: GoldPurity): number {
  if (!rate) return 0;
  if (purity === "24K") return rate.rate_24k;
  if (purity === "22K") return rate.rate_22k;
  return rate.rate_18k;
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return iso;
  }
}

export function GoldHoldingsTable({ entries, rate, onDeactivate }: GoldHoldingsTableProps) {
  if (entries.length === 0) {
    return (
      <div className="text-center py-8 text-[#E8ECF1]/40 text-sm">
        No gold purchases yet.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[#E8ECF1]/40 text-xs uppercase tracking-wider border-b border-[#1A3A5C]/30">
            <th className="text-left py-3 px-2">Date</th>
            <th className="text-left py-3 px-2">Purity</th>
            <th className="text-left py-3 px-2">Owner</th>
            <th className="text-right py-3 px-2">Weight (g)</th>
            <th className="text-right py-3 px-2">Price Paid/g</th>
            <th className="text-right py-3 px-2">Total Cost</th>
            <th className="text-right py-3 px-2">Current Value</th>
            <th className="text-right py-3 px-2">P&amp;L</th>
            <th className="text-right py-3 px-2">P&amp;L%</th>
            <th className="text-right py-3 px-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => {
            const currentRate = getRateForPurity(rate, entry.purity);
            const currentValue = entry.weight_grams * currentRate;
            const pnl = rate ? currentValue - entry.total_cost : 0;
            const pnlPct = entry.total_cost > 0 && rate ? (pnl / entry.total_cost) * 100 : 0;
            const pnlColor = pnl >= 0 ? "text-[#00895E]" : "text-[#E5A100]";

            return (
              <tr
                key={entry.id ?? entry.purchase_date}
                className="border-b border-[#1A3A5C]/20 hover:bg-[#1A3A5C]/10 transition-colors"
              >
                <td className="py-3 px-2 text-[#E8ECF1]">{formatDate(entry.purchase_date)}</td>
                <td className="py-3 px-2">{purityBadge(entry.purity)}</td>
                <td className="py-3 px-2">{ownerBadge(entry.owner)}</td>
                <td
                  className="py-3 px-2 text-right text-[#E8ECF1]"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {entry.weight_grams.toFixed(3)}
                </td>
                <td
                  className="py-3 px-2 text-right text-[#E8ECF1]/70"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {formatRupees(entry.price_per_gram)}
                </td>
                <td
                  className="py-3 px-2 text-right text-[#E8ECF1]"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {formatRupees(entry.total_cost)}
                </td>
                <td
                  className="py-3 px-2 text-right text-[#E8ECF1]"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {rate ? formatRupees(Math.round(currentValue)) : "--"}
                </td>
                <td
                  className={`py-3 px-2 text-right font-medium ${pnlColor}`}
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {rate ? `${pnl >= 0 ? "+" : ""}${formatRupees(Math.round(pnl))}` : "--"}
                </td>
                <td
                  className={`py-3 px-2 text-right font-medium ${pnlColor}`}
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {rate ? `${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%` : "--"}
                </td>
                <td className="py-3 px-2 text-right">
                  <button
                    onClick={() => entry.id && onDeactivate(entry.id)}
                    disabled={!entry.id}
                    className="text-[#E5A100] hover:text-[#E5A100]/80 text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Deactivate
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
