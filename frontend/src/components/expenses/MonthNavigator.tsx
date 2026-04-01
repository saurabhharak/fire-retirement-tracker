const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

interface MonthNavigatorProps {
  month: number;
  year: number;
  onChange: (month: number, year: number) => void;
}

export function MonthNavigator({ month, year, onChange }: MonthNavigatorProps) {
  function prev() {
    if (month === 1) {
      onChange(12, year - 1);
    } else {
      onChange(month - 1, year);
    }
  }

  function next() {
    if (month === 12) {
      onChange(1, year + 1);
    } else {
      onChange(month + 1, year);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={prev}
        className="w-8 h-8 flex items-center justify-center rounded-lg bg-[#132E3D] border border-[#1A3A5C]/30 text-[#E8ECF1]/60 hover:text-[#E8ECF1] hover:border-[#00895E] transition-colors"
        aria-label="Previous month"
      >
        &larr;
      </button>
      <span className="text-sm font-medium text-[#E8ECF1] min-w-[140px] text-center">
        {MONTH_NAMES[month - 1]} {year}
      </span>
      <button
        onClick={next}
        className="w-8 h-8 flex items-center justify-center rounded-lg bg-[#132E3D] border border-[#1A3A5C]/30 text-[#E8ECF1]/60 hover:text-[#E8ECF1] hover:border-[#00895E] transition-colors"
        aria-label="Next month"
      >
        &rarr;
      </button>
    </div>
  );
}
