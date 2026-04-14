import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { formatIndian } from "../../lib/formatIndian";
import type { KiteSIP } from "../../hooks/useKitePortfolio";

interface Props {
  sips: KiteSIP[];
}

export function ActiveSIPs({ sips }: Props) {
  const [open, setOpen] = useState(false);
  const activeSips = sips.filter((s) => s.status === "ACTIVE");

  if (activeSips.length === 0) return null;

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls="active-sips-panel"
        className="flex items-center gap-2 text-sm text-[#E8ECF1]/60 hover:text-[#E8ECF1] transition-colors mb-3 focus-visible:ring-2 focus-visible:ring-[#00895E] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0D1B2A] rounded"
      >
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        {open ? "Hide" : "Show"} Active SIPs ({activeSips.length})
      </button>

      {open && (
        <div id="active-sips-panel" className="overflow-x-auto rounded-xl border border-[#1A3A5C]/30">
          <table className="w-full text-xs sm:text-sm">
            <thead>
              <tr className="bg-[#132E3D] text-[#E8ECF1]/60 text-left">
                <th className="px-2 sm:px-3 py-2">Fund</th>
                <th className="px-2 sm:px-3 py-2 text-right">Amount</th>
                <th className="px-2 sm:px-3 py-2 hidden sm:table-cell">Frequency</th>
                <th className="px-2 sm:px-3 py-2 whitespace-nowrap">Next Date</th>
                <th className="px-2 sm:px-3 py-2 text-right hidden sm:table-cell">Done</th>
              </tr>
            </thead>
            <tbody>
              {activeSips.map((s) => (
                <tr key={s.sip_id} className="border-t border-[#1A3A5C]/20 text-[#E8ECF1]">
                  <td className="px-2 sm:px-3 py-2 max-w-[130px] sm:max-w-[250px] truncate" title={s.fund}>{s.fund}</td>
                  <td className="px-2 sm:px-3 py-2 text-right font-medium whitespace-nowrap" style={{ fontVariantNumeric: "tabular-nums" }}>{`\u20B9${formatIndian(s.instalment_amount)}`}</td>
                  <td className="px-2 sm:px-3 py-2 hidden sm:table-cell">
                    <span className="bg-[#1A3A5C]/40 px-2 py-0.5 rounded text-xs capitalize">{s.frequency}</span>
                  </td>
                  <td className="px-2 sm:px-3 py-2 text-[#E8ECF1]/60 whitespace-nowrap">{s.next_instalment || "\u2014"}</td>
                  <td className="px-2 sm:px-3 py-2 text-right text-[#E8ECF1]/60 hidden sm:table-cell">{s.completed_instalments}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
