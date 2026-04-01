import { useNavigate } from "react-router-dom";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { useFireInputs } from "../hooks/useFireInputs";
import {
  useGrowthProjection,
  useRetirementAnalysis,
} from "../hooks/useProjections";
import { useIncome } from "../hooks/useIncome";
import { useExpenses } from "../hooks/useExpenses";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { formatRupees, formatIndian } from "../lib/formatIndian";
import { toMonthlyAmount } from "../lib/expenseUtils";

export default function Dashboard() {
  const navigate = useNavigate();
  const fireInputs = useFireInputs();
  const growth = useGrowthProjection();
  const retirement = useRetirementAnalysis();
  const income = useIncome(1);
  const expenses = useExpenses({ active: true });

  // Loading state
  if (fireInputs.isLoading) {
    return <LoadingState message="Loading dashboard..." />;
  }

  // Empty state: no FIRE inputs configured
  if (!fireInputs.data) {
    return (
      <div>
        <PageHeader
          title="Dashboard"
          subtitle="Your FIRE journey at a glance"
        />
        <EmptyState
          message="Configure your FIRE settings to see your financial dashboard."
          actionLabel="Go to FIRE Settings"
          onAction={() => navigate("/fire-settings")}
        />
      </div>
    );
  }

  const inputs = fireInputs.data;

  // Compute derived values for countdown
  const dob = new Date(inputs.dob);
  const today = new Date();
  const currentAge = Math.floor(
    (today.getTime() - dob.getTime()) / (365.25 * 24 * 60 * 60 * 1000)
  );
  const yearsToRetirement = inputs.retirement_age - currentAge;
  const monthsRemaining = Math.max(0, yearsToRetirement * 12);
  const countdownYears = Math.floor(monthsRemaining / 12);
  const countdownMonths = monthsRemaining % 12;

  // Progress percentage (assume working life from age 25 to retirement)
  const totalYears = inputs.retirement_age - 25;
  const elapsed = currentAge - 25;
  const progressPct = Math.min(
    100,
    Math.max(0, Math.round((elapsed / totalYears) * 100))
  );

  // Retirement year
  const retirementYear = today.getFullYear() + yearsToRetirement;

  // Income overview
  const latestIncome =
    income.entries.length > 0 ? income.entries[0] : null;
  const totalIncome = latestIncome
    ? latestIncome.your_income + latestIncome.wife_income
    : 0;

  // Expenses: sum all active monthly-equivalent expenses
  const fixedExpenseTotal = expenses.entries.reduce(
    (sum: number, e: { amount: number; frequency: string }) =>
      sum + toMonthlyAmount(e.amount, e.frequency),
    0
  );

  const monthlySavings = totalIncome - fixedExpenseTotal - inputs.monthly_expense;
  const savingsRate =
    totalIncome > 0
      ? Math.round((monthlySavings / totalIncome) * 1000) / 10
      : 0;

  // FIRE metrics from retirement analysis
  const retData = retirement.data;
  const projectedCorpus = retData?.corpus ?? 0;
  const requiredCorpus = retData?.required_corpus ?? 0;
  const fundedRatio = retData?.funded_ratio ?? 0;
  const fundedPct = Math.round(fundedRatio * 100);
  const monthlySWP = retData?.monthly_swp ?? 0;
  const monthlyExpenseAtRetirement = retData?.monthly_expense ?? 0;
  const surplus = retData?.surplus ?? 0;

  // Funded ratio color coding
  const fundedColor: "success" | "warning" | "gold" | "default" =
    fundedPct >= 100 ? "success" : fundedPct >= 80 ? "warning" : "default";
  const fundedLabel =
    fundedPct >= 100 ? "On Track" : fundedPct >= 80 ? "Close" : "Needs Work";

  // Growth chart data
  const chartData = (growth.data ?? []).map((row) => ({
    year: today.getFullYear() + row.year,
    age: row.age,
    equity: Math.round(row.equity_value),
    debtGoldCash: Math.round(row.debt_gold_cash),
    total: Math.round(row.portfolio),
  }));

  const retirementChartYear = today.getFullYear() + yearsToRetirement;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        subtitle="Your FIRE journey at a glance"
      />

      {/* FIRE Countdown */}
      <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5 border-l-4 border-l-[#00895E]">
        <div className="flex justify-between items-end mb-4">
          <div>
            <h2 className="text-[#E8ECF1]/60 text-sm font-medium mb-1">
              Financial Independence Target
            </h2>
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-white tracking-tight">
                {countdownYears} years {countdownMonths} months
              </span>
              <span className="text-[#00895E] font-bold">to FIRE</span>
            </div>
          </div>
          <div className="text-right">
            <span className="text-[#E8ECF1]/40 text-xs font-bold uppercase tracking-wider">
              Est. Retirement: {retirementYear}
            </span>
          </div>
        </div>
        <div className="relative h-4 w-full bg-[#0D1B2A] rounded-full overflow-hidden">
          <div
            className="absolute top-0 left-0 h-full bg-gradient-to-r from-emerald-900 via-[#00895E] to-emerald-400 transition-all duration-1000"
            style={{
              width: `${progressPct}%`,
              boxShadow: "0 0 15px rgba(0, 137, 94, 0.4)",
            }}
          />
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-[10px] text-[#E8ECF1]/40 font-bold">
            START
          </span>
          <span className="text-[10px] text-[#00895E] font-bold">
            {progressPct}% ACHIEVED
          </span>
          <span className="text-[10px] text-[#E8ECF1]/40 font-bold">
            FIRE ({retirementYear})
          </span>
        </div>
      </section>

      {/* Income Overview */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard label="Latest Income" value={totalIncome} />
        <MetricCard label="Fixed Expenses" value={Math.round(fixedExpenseTotal)} />
        <MetricCard
          label="Monthly Savings"
          value={Math.round(Math.max(0, monthlySavings))}
        />
        <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 border-b-2 border-b-[#00895E]/30">
          <p className="text-sm text-[#E8ECF1]/60 mb-1">Savings Rate</p>
          <p
            className="text-2xl font-bold text-[#00895E]"
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {savingsRate}%
          </p>
          <div className="mt-2 w-full h-1 bg-[#0D1B2A] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#00895E] transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, savingsRate))}%` }}
            />
          </div>
        </div>
      </section>

      {/* FIRE Metrics */}
      {(retirement.isLoading || growth.isLoading) ? (
        <LoadingState message="Loading projections..." />
      ) : (
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-[#D4A843]/5 border border-[#D4A843]/20 p-5 rounded-xl relative overflow-hidden">
            <p className="text-[#D4A843] text-xs font-bold uppercase tracking-wider mb-2">
              Projected Corpus
            </p>
            <p
              className="text-2xl font-bold text-[#D4A843]"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {formatRupees(projectedCorpus)}
            </p>
            <p className="text-[#E8ECF1]/40 text-[10px] mt-2">
              At retirement age ({inputs.retirement_age})
            </p>
          </div>

          <MetricCard
            label="Required Corpus"
            value={requiredCorpus}
          />

          <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
            <p className="text-sm text-[#E8ECF1]/60 mb-1">Funded Ratio</p>
            <div className="flex items-center space-x-3">
              <p
                className={`text-2xl font-bold ${
                  fundedColor === "success"
                    ? "text-[#00895E]"
                    : fundedColor === "warning"
                    ? "text-[#E5A100]"
                    : "text-[#E8ECF1]"
                }`}
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {fundedPct}%
              </p>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                  fundedColor === "success"
                    ? "bg-[#2E8B57]/20 text-[#2E8B57]"
                    : fundedColor === "warning"
                    ? "bg-[#E5A100]/20 text-[#E5A100]"
                    : "bg-[#C45B5B]/20 text-[#C45B5B]"
                }`}
              >
                {fundedLabel}
              </span>
            </div>
          </div>

          <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 border-l-4 border-l-[#D4A843]/40">
            <p className="text-sm text-[#E8ECF1]/60 mb-1">Monthly SWP</p>
            <p
              className="text-2xl font-bold text-[#E8ECF1]"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {formatRupees(Math.round(monthlySWP))}
            </p>
            <div
              className={`mt-1 flex items-center text-xs font-bold ${
                surplus >= 0 ? "text-[#2E8B57]" : "text-[#C45B5B]"
              }`}
            >
              {surplus >= 0 ? "+" : "-"} {formatRupees(Math.round(Math.abs(surplus)))}{" "}
              vs expense ({formatRupees(Math.round(monthlyExpenseAtRetirement))})
            </div>
          </div>
        </section>
      )}

      {/* Portfolio Growth Chart */}
      {chartData.length > 0 && (
        <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-8 border border-white/5">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="text-xl font-bold text-white">
                Portfolio Growth Projection
              </h3>
              <p className="text-[#E8ECF1]/40 text-sm">
                Long-term wealth compounding (Equity, Debt, Gold)
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-[#00895E]" />
                <span className="text-xs text-[#E8ECF1]/60 font-medium">
                  Equity ({Math.round(inputs.equity_pct * 100)}%)
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-[#1A3A5C]" />
                <span className="text-xs text-[#E8ECF1]/60 font-medium">
                  Debt + Gold + Cash (
                  {Math.round((1 - inputs.equity_pct) * 100)}%)
                </span>
              </div>
            </div>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartData}
                margin={{ top: 10, right: 30, left: 10, bottom: 0 }}
              >
                <defs>
                  <linearGradient
                    id="colorEquity"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="5%"
                      stopColor="#00895E"
                      stopOpacity={0.6}
                    />
                    <stop
                      offset="95%"
                      stopColor="#00895E"
                      stopOpacity={0.05}
                    />
                  </linearGradient>
                  <linearGradient
                    id="colorDebt"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="5%"
                      stopColor="#1A3A5C"
                      stopOpacity={0.6}
                    />
                    <stop
                      offset="95%"
                      stopColor="#1A3A5C"
                      stopOpacity={0.05}
                    />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="year"
                  stroke="#E8ECF140"
                  tick={{ fill: "#E8ECF160", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  stroke="#E8ECF140"
                  tick={{ fill: "#E8ECF160", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v: number) =>
                    v >= 10000000
                      ? `${(v / 10000000).toFixed(1)}Cr`
                      : v >= 100000
                      ? `${(v / 100000).toFixed(0)}L`
                      : formatIndian(v)
                  }
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#132E3D",
                    border: "1px solid #1A3A5C",
                    borderRadius: "8px",
                    color: "#E8ECF1",
                  }}
                  formatter={(value: any, name: any) => [
                    formatRupees(Number(value)),
                    String(name) === "equity" ? "Equity" : "Debt+Gold+Cash",
                  ]}
                  labelFormatter={(label: any) => `Year ${label}`}
                />
                <ReferenceLine
                  x={retirementChartYear}
                  stroke="#D4A843"
                  strokeDasharray="4 4"
                  strokeWidth={2}
                  label={{
                    value: `FIRE (${retirementChartYear})`,
                    position: "top",
                    fill: "#D4A843",
                    fontSize: 11,
                    fontWeight: "bold",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="debtGoldCash"
                  stackId="1"
                  stroke="#1A3A5C"
                  fill="url(#colorDebt)"
                />
                <Area
                  type="monotone"
                  dataKey="equity"
                  stackId="1"
                  stroke="#00895E"
                  fill="url(#colorEquity)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}
    </div>
  );
}
