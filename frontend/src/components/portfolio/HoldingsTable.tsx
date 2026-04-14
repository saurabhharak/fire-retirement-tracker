import { formatIndian } from "../../lib/formatIndian";
import type { KiteHolding } from "../../hooks/useKitePortfolio";

interface Props {
  holdings: KiteHolding[];
}

export function HoldingsTable({ holdings }: Props) {
  return (
    <div className="overflow-x-auto rounded-xl border border-[#1A3A5C]/30 mb-6">
      <table className="w-full text-xs sm:text-sm">
        <thead>
          <tr className="bg-[#132E3D] text-[#E8ECF1]/60 text-left">
            <th className="px-2 sm:px-3 py-2">Fund</th>
            <th className="px-2 sm:px-3 py-2 text-right">Invested</th>
            <th className="px-2 sm:px-3 py-2 text-right">Current</th>
            <th className="px-2 sm:px-3 py-2 text-right">P&L</th>
            <th className="px-2 sm:px-3 py-2 text-right hidden sm:table-cell">P&L %</th>
            <th className="px-2 sm:px-3 py-2 text-right">SIP</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => (
            <tr key={h.tradingsymbol} className="border-t border-[#1A3A5C]/20 hover:bg-[#132E3D]/50 text-[#E8ECF1]">
              <td className="px-2 sm:px-3 py-2">
                <div className="max-w-[150px] sm:max-w-[250px]">
                  <p className="truncate font-medium text-xs sm:text-sm">{h.fund}</p>
                  <p className="text-[10px] sm:text-xs text-[#E8ECF1]/40">{h.quantity.toFixed(3)} units</p>
                </div>
              </td>
              <td className="px-2 sm:px-3 py-2 text-right" style={{ fontVariantNumeric: "tabular-nums" }}>{`\u20B9${formatIndian(h.invested)}`}</td>
              <td className="px-2 sm:px-3 py-2 text-right font-medium" style={{ fontVariantNumeric: "tabular-nums" }}>
                {h.last_price > 0 ? `\u20B9${formatIndian(h.current_value)}` : <span className="text-[#E8ECF1]/30 text-xs">Awaiting NAV</span>}
              </td>
              <td className={`px-2 sm:px-3 py-2 text-right ${h.pnl >= 0 ? "text-[#00895E]" : "text-[#E5A100]"}`} style={{ fontVariantNumeric: "tabular-nums" }}>
                {h.last_price > 0 ? <>{h.pnl >= 0 ? "+" : "-"}{`\u20B9${formatIndian(Math.abs(h.pnl))}`}</> : <span className="text-[#E8ECF1]/30">{"\u2014"}</span>}
              </td>
              <td className={`px-2 sm:px-3 py-2 text-right hidden sm:table-cell ${h.pnl_pct >= 0 ? "text-[#00895E]" : "text-[#E5A100]"}`} style={{ fontVariantNumeric: "tabular-nums" }}>
                {h.last_price > 0 ? <>{h.pnl_pct >= 0 ? "+" : ""}{h.pnl_pct.toFixed(1)}%</> : <span className="text-[#E8ECF1]/30">{"\u2014"}</span>}
              </td>
              <td className="px-2 sm:px-3 py-2 text-right text-[#E8ECF1]/60" style={{ fontVariantNumeric: "tabular-nums" }}>
                {h.sip_amount ? `\u20B9${formatIndian(h.sip_amount)}` : "\u2014"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {holdings.length === 0 && (
        <p className="text-center text-[#E8ECF1]/40 py-8">No holdings found</p>
      )}
    </div>
  );
}
