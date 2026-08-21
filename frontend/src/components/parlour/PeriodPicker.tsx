import { useCallback, useMemo, useState } from "react";
import { MONTH_NAMES } from "../../lib/constants";
import type { AnalyticsPeriod } from "../../hooks/useAmulAnalytics";

export interface PeriodSelection {
  period: AnalyticsPeriod;
  periodValue: string; // YYYY-MM-DD | YYYY-MM | YYYY-Qn | YYYY
}

const QUARTERS = [
  { value: "Q1", label: "Q1 (Jan–Mar)" },
  { value: "Q2", label: "Q2 (Apr–Jun)" },
  { value: "Q3", label: "Q3 (Jul–Sep)" },
  { value: "Q4", label: "Q4 (Oct–Dec)" },
];

interface PeriodPickerProps {
  value: PeriodSelection;
  onChange: (sel: PeriodSelection) => void;
}

function pad(n: number) {
  return String(n).padStart(2, "0");
}

export function PeriodPicker({ value, onChange }: PeriodPickerProps) {
  const now = new Date();
  // Default to current period: today / current month / current quarter / current year
  const [dateVal, setDateVal] = useState(now.toISOString().slice(0, 10));
  const [monthYear, setMonthYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [quarterYear, setQuarterYear] = useState(now.getFullYear());
  const [quarter, setQuarter] = useState(`Q${Math.floor(now.getMonth() / 3) + 1}`);
  const [yearVal, setYearVal] = useState(now.getFullYear());

  const period = value.period;

  const yearOptions = useMemo(() => {
    const years = [now.getFullYear(), now.getFullYear() - 1, now.getFullYear() - 2];
    return years.sort((a, b) => b - a);
  }, [now]);

  const emit = useCallback(
    (periodType: AnalyticsPeriod) => {
      let periodValue = "";
      if (periodType === "day") periodValue = dateVal;
      else if (periodType === "month") periodValue = `${monthYear}-${pad(month)}`;
      else if (periodType === "quarter") periodValue = `${quarterYear}-${quarter}`;
      else periodValue = String(yearVal);
      onChange({ period: periodType, periodValue });
    },
    [dateVal, monthYear, month, quarterYear, quarter, yearVal, onChange]
  );

  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        aria-label="Period"
        value={period}
        onChange={(e) => {
          const pt = e.target.value as AnalyticsPeriod;
          emit(pt);
        }}
        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded-lg px-3 py-1.5 text-sm text-[#E8ECF1]"
      >
        <option value="day">Daily</option>
        <option value="month">Monthly</option>
        <option value="quarter">Quarterly</option>
        <option value="year">Annual</option>
      </select>

      {period === "day" && (
        <input
          type="date"
          aria-label="Date"
          value={dateVal}
          onChange={(e) => {
            setDateVal(e.target.value);
            onChange({ period: "day", periodValue: e.target.value });
          }}
          className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded-lg px-3 py-1.5 text-sm text-[#E8ECF1]"
        />
      )}

      {period === "month" && (
        <div className="flex gap-2">
          <select
            aria-label="Month Year"
            value={monthYear}
            onChange={(e) => {
              const y = Number(e.target.value);
              setMonthYear(y);
              emit("month");
            }}
            className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded-lg px-2 py-1.5 text-sm text-[#E8ECF1]"
          >
            {yearOptions.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
          <select
            aria-label="Month"
            value={month}
            onChange={(e) => {
              setMonth(Number(e.target.value));
              emit("month");
            }}
            className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded-lg px-2 py-1.5 text-sm text-[#E8ECF1]"
          >
            {MONTH_NAMES.map((name, i) => (
              <option key={name} value={i + 1}>
                {name}
              </option>
            ))}
          </select>
        </div>
      )}

      {period === "quarter" && (
        <div className="flex gap-2">
          <select
            aria-label="Quarter Year"
            value={quarterYear}
            onChange={(e) => {
              setQuarterYear(Number(e.target.value));
              emit("quarter");
            }}
            className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded-lg px-2 py-1.5 text-sm text-[#E8ECF1]"
          >
            {yearOptions.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
          <select
            aria-label="Quarter"
            value={quarter}
            onChange={(e) => {
              setQuarter(e.target.value);
              emit("quarter");
            }}
            className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded-lg px-2 py-1.5 text-sm text-[#E8ECF1]"
          >
            {QUARTERS.map((q) => (
              <option key={q.value} value={q.value}>
                {q.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {period === "year" && (
        <select
          aria-label="Year"
          value={yearVal}
          onChange={(e) => {
            setYearVal(Number(e.target.value));
            emit("year");
          }}
          className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded-lg px-3 py-1.5 text-sm text-[#E8ECF1]"
        >
          {yearOptions.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}