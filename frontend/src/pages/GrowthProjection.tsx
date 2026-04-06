import { useState, useEffect, useRef, useCallback } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { useGrowthProjection } from "../hooks/useProjections";
import type { GrowthRow, ScenarioParams } from "../hooks/useProjections";
import { useFireInputs } from "../hooks/useFireInputs";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { formatRupees, formatIndian } from "../lib/formatIndian";

const EQUITY_COLOR = "#00895E";
const DEBT_COLOR = "#1A3A5C";
const GOLD_LINE = "#D4A843";
const SCENARIO_COLOR = "#38BDF8";

function formatCrLk(value: number): string {
  if (value >= 1_00_00_000) return `${(value / 1_00_00_000).toFixed(1)} Cr`;
  if (value >= 1_00_000) return `${(value / 1_00_000).toFixed(1)} L`;
  return formatIndian(value);
}

interface ChartPayloadEntry {
  name: string;
  value: number;
  color: string;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: ChartPayloadEntry[];
  label?: number;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#132E3D] border border-[#1A3A5C] rounded-lg p-3 text-sm">
      <p className="text-[#D4A843] font-semibold mb-1">Age {label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }}>
          {entry.name}: {formatRupees(entry.value)}
        </p>
      ))}
    </div>
  );
}

// ─── Slider + number input row ─────────────────────────────────────────────

interface SliderRowProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format?: (v: number) => string;
  onChange: (v: number) => void;
}

function SliderRow({ label, value, min, max, step, format, onChange }: SliderRowProps) {
  const display = format ? format(value) : String(value);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-[#E8ECF1]/60">{label}</span>
        <span className="text-sm font-medium text-[#E8ECF1]">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
        style={{
          accentColor: EQUITY_COLOR,
          background: `linear-gradient(to right, ${EQUITY_COLOR} 0%, ${EQUITY_COLOR} ${
            ((value - min) / (max - min)) * 100
          }%, #1A3A5C ${((value - min) / (max - min)) * 100}%, #1A3A5C 100%)`,
        }}
      />
    </div>
  );
}

// ─── Merged chart data ─────────────────────────────────────────────────────

interface MergedRow {
  age: number;
  equity_value: number;
  debt_gold_cash: number;
  portfolio: number;
  sc_equity?: number;
  sc_debt_gold_cash?: number;
  sc_portfolio?: number;
  // pass-through table fields
  year: number;
  monthly_sip: number;
  annual_inv: number;
  cumulative: number;
  gains: number;
}

function mergeData(base: GrowthRow[], scenario: GrowthRow[] | undefined): MergedRow[] {
  return base.map((row) => {
    const sc = scenario?.find((r) => r.age === row.age);
    return {
      ...row,
      sc_equity: sc?.equity_value,
      sc_debt_gold_cash: sc?.debt_gold_cash,
      sc_portfolio: sc?.portfolio,
    };
  });
}

// ─── Slider state shape ─────────────────────────────────────────────────────

interface SliderState {
  your_sip: number;
  wife_sip: number;
  equity_return: number;
  inflation: number;
  step_up_pct: number;
  retirement_age: number;
}

// ─── Main page ─────────────────────────────────────────────────────────────

export default function GrowthProjection() {
  const { data: fireInputs } = useFireInputs();

  // Scenario local state — defaults populated once fireInputs loads
  const [scenario, setScenario] = useState<ScenarioParams>({});
  const [panelOpen, setPanelOpen] = useState(false);
  const [debouncedScenario, setDebouncedScenario] = useState<ScenarioParams>({});
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [showTable, setShowTable] = useState(true);

  // Local slider values (live, before debounce)
  const [sliders, setSliders] = useState<SliderState | null>(null);

  // Populate sliders once FIRE inputs load
  useEffect(() => {
    if (fireInputs && sliders === null) {
      setSliders({
        your_sip: fireInputs.your_sip,
        wife_sip: fireInputs.wife_sip,
        equity_return: Math.round(fireInputs.equity_return * 1000) / 10, // store as %
        inflation: Math.round(fireInputs.inflation * 1000) / 10,
        step_up_pct: Math.round(fireInputs.step_up_pct * 1000) / 10,
        retirement_age: fireInputs.retirement_age,
      });
    }
  }, [fireInputs, sliders]);

  // Compute whether any slider differs from saved inputs
  const isScenarioActive = fireInputs !== undefined && fireInputs !== null && sliders !== null && (
    sliders.your_sip !== fireInputs.your_sip ||
    sliders.wife_sip !== fireInputs.wife_sip ||
    Math.abs(sliders.equity_return / 100 - fireInputs.equity_return) > 0.0001 ||
    Math.abs(sliders.inflation / 100 - fireInputs.inflation) > 0.0001 ||
    Math.abs(sliders.step_up_pct / 100 - fireInputs.step_up_pct) > 0.0001 ||
    sliders.retirement_age !== fireInputs.retirement_age
  );

  // Debounce slider changes -> update debouncedScenario
  const handleSliderChange = useCallback(
    (key: keyof SliderState & keyof ScenarioParams, value: number) => {
      setSliders((prev) => (prev ? { ...prev, [key]: value } : prev));
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      debounceTimer.current = setTimeout(() => {
        setDebouncedScenario((prev) => ({ ...prev, [key]: value }));
      }, 500);
    },
    []
  );

  // Cleanup debounce timer on unmount
  useEffect(() => () => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
  }, []);

  // Convert debounced slider values -> API params (all read from debouncedScenario)
  const scenarioApiParams: ScenarioParams = (() => {
    if (!isScenarioActive || !fireInputs) return {};
    const ds = debouncedScenario;
    const params: ScenarioParams = {};
    if (ds.your_sip !== undefined && ds.your_sip !== fireInputs.your_sip) params.your_sip = ds.your_sip;
    if (ds.wife_sip !== undefined && ds.wife_sip !== fireInputs.wife_sip) params.wife_sip = ds.wife_sip;
    if (ds.equity_return !== undefined && Math.abs(ds.equity_return / 100 - fireInputs.equity_return) > 0.0001)
      params.equity_return = ds.equity_return / 100;
    if (ds.inflation !== undefined && Math.abs(ds.inflation / 100 - fireInputs.inflation) > 0.0001)
      params.inflation = ds.inflation / 100;
    if (ds.step_up_pct !== undefined && Math.abs(ds.step_up_pct / 100 - fireInputs.step_up_pct) > 0.0001)
      params.step_up_pct = ds.step_up_pct / 100;
    if (ds.retirement_age !== undefined && ds.retirement_age !== fireInputs.retirement_age)
      params.retirement_age = ds.retirement_age;
    return params;
  })();

  // Effect: keep scenario state in sync with scenarioApiParams
  useEffect(() => {
    setScenario(scenarioApiParams);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(scenarioApiParams)]);

  const { data: baseData, isLoading: baseLoading } = useGrowthProjection();
  const { data: scenarioData, isLoading: scenarioLoading } = useGrowthProjection(
    isScenarioActive ? scenario : undefined
  );

  const resetScenario = () => {
    if (!fireInputs) return;
    const defaults = {
      your_sip: fireInputs.your_sip,
      wife_sip: fireInputs.wife_sip,
      equity_return: Math.round(fireInputs.equity_return * 1000) / 10,
      inflation: Math.round(fireInputs.inflation * 1000) / 10,
      step_up_pct: Math.round(fireInputs.step_up_pct * 1000) / 10,
      retirement_age: fireInputs.retirement_age,
    };
    setSliders(defaults);
    setDebouncedScenario({});
    setScenario({});
  };

  if (baseLoading) return <LoadingState message="Calculating projections..." />;
  if (!baseData || baseData.length === 0)
    return (
      <EmptyState message="No projection data available. Configure your FIRE settings first." />
    );

  const retirementAge = sliders?.retirement_age ?? fireInputs?.retirement_age ?? 50;
  const savedRetirementAge = fireInputs?.retirement_age ?? 50;

  // Choose active data for hero + table
  const activeData = isScenarioActive && scenarioData ? scenarioData : baseData;
  const lastRow = activeData[activeData.length - 1];
  const retirementRow = activeData.find((r) => r.age >= retirementAge);
  const corpusAtRetirement = retirementRow?.portfolio ?? lastRow.portfolio;

  // Merge base + scenario for chart
  const chartData = mergeData(baseData, isScenarioActive ? (scenarioData ?? undefined) : undefined);

  return (
    <div>
      <PageHeader
        title="Growth Projection"
        subtitle="Visualise your portfolio trajectory to financial independence"
      />

      {/* ── What-If Panel ── */}
      <div className="bg-[#132E3D] rounded-xl border border-[#1A3A5C]/30 mb-6 overflow-hidden">
        {/* Panel header */}
        <div className="flex items-center justify-between px-4 py-3">
          <button
            onClick={() => setPanelOpen((v) => !v)}
            className="flex items-center gap-2 text-sm font-medium text-[#E8ECF1]/80 hover:text-[#E8ECF1] transition-colors"
          >
            <span
              className="inline-block transition-transform duration-200"
              style={{ transform: panelOpen ? "rotate(90deg)" : "rotate(0deg)" }}
            >
              ▶
            </span>
            What-If Scenarios
            {isScenarioActive && (
              <span className="bg-[#00895E]/20 text-[#00895E] text-xs px-2 py-0.5 rounded-full ml-1">
                Scenario active
              </span>
            )}
          </button>
          {isScenarioActive && (
            <button
              onClick={resetScenario}
              className="text-xs text-[#E8ECF1]/50 hover:text-[#E8ECF1]/80 transition-colors border border-[#1A3A5C] rounded-md px-3 py-1"
            >
              Reset to Saved
            </button>
          )}
        </div>

        {/* Collapsible body */}
        {panelOpen && sliders !== null && (
          <div className="px-4 pb-4 border-t border-[#1A3A5C]/30 pt-4 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-5">
            <SliderRow
              label="Your Monthly SIP (₹)"
              value={sliders.your_sip}
              min={0}
              max={200000}
              step={1000}
              format={(v) => `₹${v.toLocaleString("en-IN")}`}
              onChange={(v) => handleSliderChange("your_sip", v)}
            />
            <SliderRow
              label="Equity Return (%)"
              value={sliders.equity_return}
              min={5}
              max={20}
              step={0.5}
              format={(v) => `${v.toFixed(1)}%`}
              onChange={(v) => handleSliderChange("equity_return", v)}
            />
            <SliderRow
              label="Wife's Monthly SIP (₹)"
              value={sliders.wife_sip}
              min={0}
              max={200000}
              step={1000}
              format={(v) => `₹${v.toLocaleString("en-IN")}`}
              onChange={(v) => handleSliderChange("wife_sip", v)}
            />
            <SliderRow
              label="Inflation (%)"
              value={sliders.inflation}
              min={1}
              max={12}
              step={0.5}
              format={(v) => `${v.toFixed(1)}%`}
              onChange={(v) => handleSliderChange("inflation", v)}
            />
            <SliderRow
              label="Annual Step-Up (%)"
              value={sliders.step_up_pct}
              min={0}
              max={30}
              step={0.5}
              format={(v) => `${v.toFixed(1)}%`}
              onChange={(v) => handleSliderChange("step_up_pct", v)}
            />
            <SliderRow
              label="Retirement Age"
              value={sliders.retirement_age}
              min={30}
              max={70}
              step={1}
              format={(v) => `Age ${v}`}
              onChange={(v) => handleSliderChange("retirement_age", v)}
            />
          </div>
        )}
      </div>

      {/* ── Hero number ── */}
      <div className="bg-[#132E3D] rounded-xl p-6 border border-[#1A3A5C]/30 mb-6 text-center relative">
        {isScenarioActive && scenarioLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#132E3D]/70 rounded-xl">
            <span className="text-xs text-[#E8ECF1]/50 animate-pulse">Recalculating…</span>
          </div>
        )}
        <p className="text-sm text-[#E8ECF1]/60 mb-1">
          Corpus at Retirement (Age {retirementRow?.age ?? retirementAge})
          {isScenarioActive && (
            <span className="ml-2 bg-[#00895E]/20 text-[#00895E] text-xs px-2 py-0.5 rounded-full">
              Scenario
            </span>
          )}
        </p>
        <p className="text-4xl md:text-5xl font-bold text-[#D4A843]">
          {formatRupees(corpusAtRetirement)}
        </p>
      </div>

      {/* ── Area Chart ── */}
      <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-4">
        {/* Legend */}
        <div className="flex flex-wrap gap-4 mb-3 px-1">
          <div className="flex items-center gap-1.5 text-xs text-[#E8ECF1]/60">
            <span className="w-3 h-1 rounded-full inline-block" style={{ background: EQUITY_COLOR }} />
            Equity (saved)
          </div>
          <div className="flex items-center gap-1.5 text-xs text-[#E8ECF1]/60">
            <span className="w-3 h-1 rounded-full inline-block" style={{ background: DEBT_COLOR }} />
            Debt+Gold+Cash (saved)
          </div>
          {isScenarioActive && (
            <div className="flex items-center gap-1.5 text-xs text-[#38BDF8]/80">
              <span className="w-3 h-1 rounded-full inline-block" style={{ background: SCENARIO_COLOR }} />
              Scenario projection
            </div>
          )}
        </div>

        <ResponsiveContainer width="100%" height={360}>
          <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
            <defs>
              {/* Base layers — faded when scenario active */}
              <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={EQUITY_COLOR} stopOpacity={isScenarioActive ? 0.15 : 0.6} />
                <stop offset="95%" stopColor={EQUITY_COLOR} stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="debtGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={DEBT_COLOR} stopOpacity={isScenarioActive ? 0.25 : 0.6} />
                <stop offset="95%" stopColor={DEBT_COLOR} stopOpacity={0.02} />
              </linearGradient>
              {/* Scenario layers */}
              <linearGradient id="scEquityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={SCENARIO_COLOR} stopOpacity={0.5} />
                <stop offset="95%" stopColor={SCENARIO_COLOR} stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="scDebtGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1E4A8C" stopOpacity={0.5} />
                <stop offset="95%" stopColor="#1E4A8C" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="age"
              stroke="#E8ECF1"
              opacity={0.4}
              tick={{ fontSize: 12 }}
              label={{
                value: "Age",
                position: "insideBottom",
                offset: -2,
                fill: "#E8ECF1",
                opacity: 0.6,
              }}
            />
            <YAxis
              stroke="#E8ECF1"
              opacity={0.4}
              tick={{ fontSize: 12 }}
              tickFormatter={formatCrLk}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Saved retirement age reference line */}
            <ReferenceLine
              x={savedRetirementAge}
              stroke={GOLD_LINE}
              strokeDasharray="6 4"
              strokeWidth={isScenarioActive && retirementAge !== savedRetirementAge ? 1 : 2}
              label={{
                value: isScenarioActive && retirementAge !== savedRetirementAge ? "Saved" : "Retire",
                fill: GOLD_LINE,
                fontSize: 11,
                position: "top",
              }}
            />
            {/* Scenario retirement age reference line (if different) */}
            {isScenarioActive && retirementAge !== savedRetirementAge && (
              <ReferenceLine
                x={retirementAge}
                stroke={SCENARIO_COLOR}
                strokeDasharray="6 4"
                strokeWidth={2}
                label={{
                  value: "Retire (sc)",
                  fill: SCENARIO_COLOR,
                  fontSize: 11,
                  position: "top",
                }}
              />
            )}

            {/* Base areas (always shown, faded when scenario active) */}
            <Area
              type="monotone"
              dataKey="debt_gold_cash"
              stackId="base"
              stroke={isScenarioActive ? DEBT_COLOR : DEBT_COLOR}
              strokeOpacity={isScenarioActive ? 0.3 : 1}
              fill="url(#debtGrad)"
              name="Debt + Gold + Cash"
            />
            <Area
              type="monotone"
              dataKey="equity_value"
              stackId="base"
              stroke={isScenarioActive ? EQUITY_COLOR : EQUITY_COLOR}
              strokeOpacity={isScenarioActive ? 0.3 : 1}
              fill="url(#equityGrad)"
              name="Equity"
            />

            {/* Scenario overlay areas */}
            {isScenarioActive && (
              <>
                <Area
                  type="monotone"
                  dataKey="sc_debt_gold_cash"
                  stackId="scenario"
                  stroke="#1E4A8C"
                  fill="url(#scDebtGrad)"
                  name="Debt+Gold+Cash (Sc)"
                  dot={false}
                  activeDot={false}
                />
                <Area
                  type="monotone"
                  dataKey="sc_equity"
                  stackId="scenario"
                  stroke={SCENARIO_COLOR}
                  fill="url(#scEquityGrad)"
                  name="Equity (Sc)"
                  dot={false}
                  activeDot={false}
                />
              </>
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* ── Toggle table ── */}
      <button
        onClick={() => setShowTable((v) => !v)}
        className="mb-4 px-4 py-2 text-sm rounded-lg border border-[#1A3A5C] text-[#E8ECF1]/80 hover:bg-[#1A3A5C]/30 transition-colors"
      >
        {showTable ? "Hide" : "Show"} Data Table
      </button>

      {/* ── Data Table ── */}
      {showTable && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-[#E8ECF1]">
            <thead>
              <tr className="border-b border-[#1A3A5C]">
                {["Year", "Age", "Monthly SIP", "Annual Inv", "Cumulative", "Portfolio", "Gains"].map(
                  (h) => (
                    <th key={h} className="px-3 py-2 text-left text-[#E8ECF1]/60 font-medium">
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {activeData.map((row: GrowthRow) => (
                <tr
                  key={row.year}
                  className={`border-b border-[#1A3A5C]/30 ${
                    row.age === retirementAge ? "bg-[#D4A843]/10" : ""
                  }`}
                >
                  <td className="px-3 py-2">{row.year}</td>
                  <td className="px-3 py-2">{row.age}</td>
                  <td className="px-3 py-2" style={{ fontVariantNumeric: "tabular-nums" }}>{formatRupees(row.monthly_sip)}</td>
                  <td className="px-3 py-2" style={{ fontVariantNumeric: "tabular-nums" }}>{formatRupees(row.annual_inv)}</td>
                  <td className="px-3 py-2" style={{ fontVariantNumeric: "tabular-nums" }}>{formatRupees(row.cumulative)}</td>
                  <td className="px-3 py-2 font-semibold text-[#D4A843]" style={{ fontVariantNumeric: "tabular-nums" }}>
                    {formatRupees(row.portfolio)}
                  </td>
                  <td className="px-3 py-2 text-[#00895E]" style={{ fontVariantNumeric: "tabular-nums" }}>{formatRupees(row.gains)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
