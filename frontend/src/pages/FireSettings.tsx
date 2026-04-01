import { useState, useEffect, useMemo, useRef } from "react";
import { useFireInputs, type FireInputsData } from "../hooks/useFireInputs";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";

const DEFAULT_INPUTS: FireInputsData = {
  dob: "1990-01-01",
  retirement_age: 50,
  life_expectancy: 90,
  your_sip: 200000,
  wife_sip: 50000,
  step_up_pct: 0.1,
  existing_corpus: 0,
  equity_return: 0.11,
  debt_return: 0.07,
  gold_return: 0.09,
  cash_return: 0.035,
  inflation: 0.06,
  swr: 0.03,
  equity_pct: 0.8,
  gold_pct: 0.05,
  cash_pct: 0.02,
  monthly_expense: 125000,
};

function InputField({
  label,
  name,
  value,
  onChange,
  type = "text",
  prefix,
  suffix,
  step,
  min,
  max,
}: {
  label: string;
  name: string;
  value: string | number;
  onChange: (name: string, value: string) => void;
  type?: string;
  prefix?: string;
  suffix?: string;
  step?: string;
  min?: string;
  max?: string;
}) {
  return (
    <div className="flex flex-col">
      <label className="text-xs text-[#E8ECF1]/50 font-medium mb-1.5 uppercase tracking-wider">
        {label}
      </label>
      <div className="relative">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#00895E] font-bold text-sm">
            {prefix}
          </span>
        )}
        <input
          type={type}
          name={name}
          value={value}
          onChange={(e) => onChange(name, e.target.value)}
          step={step}
          min={min}
          max={max}
          className={`w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded-lg py-2.5 text-[#E8ECF1] text-sm focus:outline-none focus:border-[#00895E] transition-colors ${
            prefix ? "pl-8" : "pl-3"
          } ${suffix ? "pr-8" : "pr-3"}`}
        />
        {suffix && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[#E8ECF1]/40 text-sm">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}

export default function FireSettings() {
  const { data, isLoading, save, isSaving } = useFireInputs();
  const [form, setForm] = useState<FireInputsData>(DEFAULT_INPUTS);
  const [saveStatus, setSaveStatus] = useState<"idle" | "success" | "error">(
    "idle"
  );
  const timeoutRef = useRef<number>();

  useEffect(() => () => { if (timeoutRef.current) clearTimeout(timeoutRef.current); }, []);

  useEffect(() => {
    if (data) {
      setForm(data);
    }
  }, [data]);

  function handleChange(name: string, rawValue: string) {
    const numericFields = [
      "retirement_age",
      "life_expectancy",
      "your_sip",
      "wife_sip",
      "step_up_pct",
      "existing_corpus",
      "equity_return",
      "debt_return",
      "gold_return",
      "cash_return",
      "inflation",
      "swr",
      "equity_pct",
      "gold_pct",
      "cash_pct",
      "monthly_expense",
    ];

    if (numericFields.includes(name)) {
      const num = parseFloat(rawValue);
      setForm((prev) => ({
        ...prev,
        [name]: isNaN(num) ? 0 : num,
      }));
    } else {
      setForm((prev) => ({ ...prev, [name]: rawValue }));
    }
  }

  const debtPct = 1 - form.equity_pct - form.gold_pct - form.cash_pct;
  const allocationTotal = form.equity_pct + form.gold_pct + form.cash_pct + Math.max(0, debtPct);
  const allocationWarning = form.equity_pct + form.gold_pct + form.cash_pct > 1;

  // Preview calculations
  const preview = useMemo(() => {
    const blended =
      form.equity_pct * form.equity_return +
      Math.max(0, debtPct) * form.debt_return +
      form.gold_pct * form.gold_return +
      form.cash_pct * form.cash_return;
    const realReturn = (1 + blended) / (1 + form.inflation) - 1;

    const dobDate = new Date(form.dob);
    const today = new Date();
    const currentAge = Math.floor(
      (today.getTime() - dobDate.getTime()) / (365.25 * 24 * 60 * 60 * 1000)
    );
    const yearsToRetirement = Math.max(0, form.retirement_age - currentAge);

    return {
      blendedReturn: blended,
      realReturn,
      yearsToRetirement,
    };
  }, [form, debtPct]);

  async function handleSave() {
    try {
      setSaveStatus("idle");
      await save(form);
      setSaveStatus("success");
      timeoutRef.current = window.setTimeout(() => setSaveStatus("idle"), 3000);
    } catch {
      setSaveStatus("error");
      timeoutRef.current = window.setTimeout(() => setSaveStatus("idle"), 3000);
    }
  }

  if (isLoading) {
    return <LoadingState message="Loading FIRE settings..." />;
  }

  return (
    <div className="space-y-8 max-w-4xl">
      <PageHeader
        title="FIRE Settings"
        subtitle="Configure your financial independence parameters"
      />

      {/* Form */}
      <div className="space-y-8">
        {/* Personal Profile */}
        <section className="bg-[#132E3D] rounded-xl p-6 border border-[#1A3A5C]/30">
          <h3 className="text-[#00895E] font-bold text-sm mb-4 flex items-center">
            <span className="mr-2">*</span> Personal Profile
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <InputField
              label="Date of Birth"
              name="dob"
              value={form.dob}
              onChange={handleChange}
              type="date"
            />
            <InputField
              label="Retirement Age"
              name="retirement_age"
              value={form.retirement_age}
              onChange={handleChange}
              type="number"
              min="19"
              max="99"
            />
            <InputField
              label="Life Expectancy"
              name="life_expectancy"
              value={form.life_expectancy}
              onChange={handleChange}
              type="number"
              min="50"
              max="120"
            />
          </div>
        </section>

        {/* Investment */}
        <section className="bg-[#132E3D] rounded-xl p-6 border border-[#1A3A5C]/30">
          <h3 className="text-[#00895E] font-bold text-sm mb-4 flex items-center">
            <span className="mr-2">*</span> Investment
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <InputField
              label="Your Monthly SIP"
              name="your_sip"
              value={form.your_sip}
              onChange={handleChange}
              type="number"
              prefix={"\u20B9"}
              min="0"
            />
            <InputField
              label="Wife's Monthly SIP"
              name="wife_sip"
              value={form.wife_sip}
              onChange={handleChange}
              type="number"
              prefix={"\u20B9"}
              min="0"
            />
            <InputField
              label="Annual Step-Up %"
              name="step_up_pct"
              value={form.step_up_pct}
              onChange={handleChange}
              type="number"
              suffix="%"
              step="0.01"
              min="0"
              max="0.5"
            />
            <InputField
              label="Existing Corpus"
              name="existing_corpus"
              value={form.existing_corpus}
              onChange={handleChange}
              type="number"
              prefix={"\u20B9"}
              min="0"
            />
          </div>
        </section>

        {/* Monthly Expense & SWR */}
        <section className="bg-[#132E3D] rounded-xl p-6 border border-[#1A3A5C]/30">
          <h3 className="text-[#00895E] font-bold text-sm mb-4 flex items-center">
            <span className="mr-2">*</span> Monthly Expense & SWR
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <InputField
              label="Current Monthly Expense"
              name="monthly_expense"
              value={form.monthly_expense}
              onChange={handleChange}
              type="number"
              prefix={"\u20B9"}
              min="0"
            />
            <InputField
              label="Safe Withdrawal Rate"
              name="swr"
              value={form.swr}
              onChange={handleChange}
              type="number"
              step="0.005"
              min="0.01"
              max="0.10"
            />
          </div>
        </section>

        {/* Expected Returns */}
        <section className="bg-[#132E3D] rounded-xl p-6 border border-[#1A3A5C]/30">
          <h3 className="text-[#00895E] font-bold text-sm mb-4 flex items-center">
            <span className="mr-2">*</span> Expected Returns
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <InputField
              label="Equity"
              name="equity_return"
              value={form.equity_return}
              onChange={handleChange}
              type="number"
              step="0.01"
              min="0.01"
              max="0.3"
            />
            <InputField
              label="Debt"
              name="debt_return"
              value={form.debt_return}
              onChange={handleChange}
              type="number"
              step="0.01"
              min="0.01"
              max="0.3"
            />
            <InputField
              label="Gold"
              name="gold_return"
              value={form.gold_return}
              onChange={handleChange}
              type="number"
              step="0.01"
              min="0"
              max="0.3"
            />
            <InputField
              label="Cash"
              name="cash_return"
              value={form.cash_return}
              onChange={handleChange}
              type="number"
              step="0.01"
              min="0"
              max="0.3"
            />
            <InputField
              label="Inflation"
              name="inflation"
              value={form.inflation}
              onChange={handleChange}
              type="number"
              step="0.01"
              min="0.01"
              max="0.2"
            />
          </div>
        </section>

        {/* Asset Allocation */}
        <section className="bg-[#132E3D] rounded-xl p-6 border border-[#1A3A5C]/30">
          <h3 className="text-[#00895E] font-bold text-sm mb-4 flex items-center">
            <span className="mr-2">*</span> Asset Allocation
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <InputField
              label="Equity"
              name="equity_pct"
              value={form.equity_pct}
              onChange={handleChange}
              type="number"
              step="0.01"
              min="0"
              max="1"
            />
            <InputField
              label="Gold"
              name="gold_pct"
              value={form.gold_pct}
              onChange={handleChange}
              type="number"
              step="0.01"
              min="0"
              max="1"
            />
            <InputField
              label="Cash"
              name="cash_pct"
              value={form.cash_pct}
              onChange={handleChange}
              type="number"
              step="0.01"
              min="0"
              max="1"
            />
            <div className="flex flex-col">
              <label className="text-xs text-[#E8ECF1]/50 font-medium mb-1.5 uppercase tracking-wider">
                Debt (auto-calc)
              </label>
              <div className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded-lg py-2.5 px-3 text-[#E8ECF1]/60 text-sm">
                {(Math.max(0, debtPct) * 100).toFixed(0)}%
              </div>
            </div>
            <div className="flex flex-col">
              <label className="text-xs text-[#E8ECF1]/50 font-medium mb-1.5 uppercase tracking-wider">
                Total
              </label>
              <div
                className={`w-full border rounded-lg py-2.5 px-3 text-sm font-bold ${
                  allocationWarning
                    ? "bg-[#C45B5B]/10 border-[#C45B5B]/50 text-[#C45B5B]"
                    : "bg-[#00895E]/10 border-[#00895E]/50 text-[#00895E]"
                }`}
              >
                {Math.round(allocationTotal * 100)}%
              </div>
            </div>
          </div>
          {allocationWarning && (
            <p className="mt-3 text-sm text-[#C45B5B] font-medium">
              Equity + Gold + Cash exceeds 100%. Please adjust allocations.
            </p>
          )}
        </section>

        {/* Save Button */}
        <div className="flex items-center space-x-4">
          <button
            onClick={handleSave}
            disabled={isSaving || allocationWarning}
            className="px-8 py-3 bg-[#00895E] text-white rounded-lg font-bold hover:bg-[#00895E]/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? "Saving..." : "Save FIRE Settings"}
          </button>
          {saveStatus === "success" && (
            <span className="text-[#2E8B57] text-sm font-medium">
              Settings saved successfully!
            </span>
          )}
          {saveStatus === "error" && (
            <span className="text-[#C45B5B] text-sm font-medium">
              Failed to save. Please try again.
            </span>
          )}
        </div>
      </div>

      {/* Preview Section */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
        <div className="bg-[#132E3D] rounded-xl p-6 border border-[#1A3A5C]/30 text-center">
          <p className="text-[#E8ECF1]/50 text-xs font-bold uppercase tracking-wider mb-3">
            Blended Return
          </p>
          <p className="text-3xl font-extrabold text-[#D4A843]" style={{ fontVariantNumeric: "tabular-nums" }}>
            {(preview.blendedReturn * 100).toFixed(1)}%
          </p>
          <div className="mt-2 flex justify-center">
            <span className="text-[#2E8B57] text-xs">Nominal</span>
          </div>
        </div>
        <div className="bg-[#132E3D] rounded-xl p-6 border border-[#1A3A5C]/30 text-center">
          <p className="text-[#E8ECF1]/50 text-xs font-bold uppercase tracking-wider mb-3">
            Real Return
          </p>
          <p className="text-3xl font-extrabold text-[#00895E]" style={{ fontVariantNumeric: "tabular-nums" }}>
            {(preview.realReturn * 100).toFixed(1)}%
          </p>
          <div className="mt-2 flex justify-center">
            <span className="text-[#E8ECF1]/40 text-xs">After inflation</span>
          </div>
        </div>
        <div className="bg-[#132E3D] rounded-xl p-6 border border-[#1A3A5C]/30 text-center">
          <p className="text-[#E8ECF1]/50 text-xs font-bold uppercase tracking-wider mb-3">
            Years to Retirement
          </p>
          <p className="text-3xl font-extrabold text-[#E8ECF1]" style={{ fontVariantNumeric: "tabular-nums" }}>
            {preview.yearsToRetirement}
          </p>
          <div className="mt-2 flex justify-center">
            <span className="text-[#E8ECF1]/40 text-xs">
              From age {form.retirement_age - preview.yearsToRetirement} to {form.retirement_age}
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
