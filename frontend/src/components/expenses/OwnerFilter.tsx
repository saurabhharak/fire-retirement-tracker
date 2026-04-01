type OwnerOption = "all" | "you" | "wife" | "household";

interface OwnerFilterProps {
  selected: OwnerOption;
  onChange: (owner: OwnerOption) => void;
}

const options: { value: OwnerOption; label: string }[] = [
  { value: "all", label: "All" },
  { value: "you", label: "You" },
  { value: "wife", label: "Wife" },
  { value: "household", label: "Household" },
];

export type { OwnerOption };

export function OwnerFilter({ selected, onChange }: OwnerFilterProps) {
  return (
    <div className="flex gap-1 bg-[#132E3D] rounded-lg p-1 border border-[#1A3A5C]/30">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
            selected === opt.value
              ? "bg-[#00895E] text-white"
              : "text-[#E8ECF1]/60 hover:text-[#E8ECF1]"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
