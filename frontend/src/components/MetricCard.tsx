import { formatIndian } from "../lib/formatIndian";

interface MetricCardProps {
  label: string;
  value: number;
  prefix?: string;
  suffix?: string;
  delta?: number;
  deltaLabel?: string;
  color?: "default" | "success" | "warning" | "gold";
}

const colorMap = {
  default: "text-[#E8ECF1]",
  success: "text-[#00895E]",
  warning: "text-[#E5A100]",
  gold: "text-[#D4A843]",
};

export function MetricCard({
  label,
  value,
  prefix = "\u20B9",
  suffix,
  delta,
  deltaLabel,
  color = "default",
}: MetricCardProps) {
  const formattedValue = `${prefix}${formatIndian(value)}${suffix || ""}`;

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
      <p className="text-sm text-[#E8ECF1]/60 mb-1">{label}</p>
      <p
        className={`text-lg sm:text-2xl font-bold ${colorMap[color]} break-all`}
        style={{ fontVariantNumeric: "tabular-nums" }}
      >
        {formattedValue}
      </p>
      {delta !== undefined && (
        <p
          className={`text-sm mt-1 ${delta >= 0 ? "text-[#00895E]" : "text-[#E5A100]"}`}
        >
          {delta >= 0 ? "\u2191" : "\u2193"} {prefix}
          {formatIndian(Math.abs(delta))} {deltaLabel || ""}
        </p>
      )}
    </div>
  );
}
