export type ExpenseTab = "all" | "fixed" | "one-time" | "income";

interface ExpenseTabsProps {
  activeTab: ExpenseTab;
  onChange: (tab: ExpenseTab) => void;
}

const tabs: { value: ExpenseTab; label: string }[] = [
  { value: "all", label: "All" },
  { value: "fixed", label: "Fixed" },
  { value: "one-time", label: "One-time" },
  { value: "income", label: "Income" },
];

export function ExpenseTabs({ activeTab, onChange }: ExpenseTabsProps) {
  return (
    <div className="flex gap-1 border-b border-[#1A3A5C]/30 mb-6">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange(tab.value)}
          className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
            activeTab === tab.value
              ? "border-[#00895E] text-[#00895E]"
              : "border-transparent text-[#E8ECF1]/60 hover:text-[#E8ECF1]"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
