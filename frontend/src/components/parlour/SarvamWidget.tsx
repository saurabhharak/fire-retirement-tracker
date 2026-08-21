import { formatIndian } from "../../lib/formatIndian";
import type { SarvamSpend } from "../../hooks/useSarvamUsage";

interface SarvamWidgetProps {
  spend?: SarvamSpend;
  isLoading?: boolean;
}

export function SarvamWidget({ spend, isLoading }: SarvamWidgetProps) {
  if (isLoading || !spend) return null;
  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
      <h3 className="text-sm font-semibold text-[#E8ECF1] mb-3">Sarvam AI Credits</h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div>
          <p className="text-xs text-[#E8ECF1]/60 mb-1">Starting</p>
          <p className="text-lg font-bold text-[#E8ECF1]">{formatIndian(spend.starting)}</p>
        </div>
        <div>
          <p className="text-xs text-[#E8ECF1]/60 mb-1">Used</p>
          <p className="text-lg font-bold text-[#E5A100]">{formatIndian(spend.used)}</p>
        </div>
        <div>
          <p className="text-xs text-[#E8ECF1]/60 mb-1">Remaining</p>
          <p
            className={`text-lg font-bold ${
              spend.remaining < 0 ? "text-[#E5A100]" : "text-[#00895E]"
            }`}
          >
            {formatIndian(spend.remaining)}
          </p>
        </div>
        <div>
          <p className="text-xs text-[#E8ECF1]/60 mb-1">Calls</p>
          <p className="text-lg font-bold text-[#E8ECF1]">{spend.call_count}</p>
        </div>
      </div>
      {spend.remaining < 0 && (
        <p className="text-xs text-[#E5A100] mt-2">
          Credits exceeded — use the free Docling OCR toggle for re-extraction.
        </p>
      )}
    </div>
  );
}
