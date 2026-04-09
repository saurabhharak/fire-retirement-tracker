import { useNavigate } from "react-router-dom";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { useFireInputs } from "../hooks/useFireInputs";
import {
  useGrowthProjection,
  useRetirementAnalysis,
} from "../hooks/useProjections";
import { useIncome } from "../hooks/useIncome";
import { useExpenses } from "../hooks/useExpenses";
import { useMetalsSummary } from "../hooks/useMetalsSummary";
import { useSipTotal } from "../hooks/useSipTotal";
import { useKitePortfolio } from "../hooks/useKitePortfolio";
import { useLedgerContacts, useLedgerSummary } from "../hooks/useLedgerContacts";
import { useSipLog } from "../hooks/useSipLog";
import { MetricCard } from "../components/MetricCard";
import { MFPortfolioWidget } from "../components/dashboard/MFPortfolioWidget";
import { MoneyLedgerWidget } from "../components/dashboard/MoneyLedgerWidget";
import { SipDisciplineWidget } from "../components/dashboard/SipDisciplineWidget";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { formatRupees, formatIndian } from "../lib/formatIndian";
import { effectiveMonthlyAmount } from "../lib/expenseUtils";
import { MONTH_NAMES } from "../lib/constants";

export default function Dashboard() {
  const navigate = useNavigate();
  const fireInputs = useFireInputs();
  const growth = useGrowthProjection();
  const retirement = useRetirementAnalysis();
  const income = useIncome(1);
  const expenses = useExpenses({ active: true });
  const metalsSummary = useMetalsSummary();
  const sipTotal = useSipTotal();
  // Widget hooks (pre-fetched so widgets render without extra waterfall)
  useKitePortfolio();
  useLedgerContacts();
  useLedgerSummary();
  useSipLog(6);

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
  const incomeLabel = latestIncome
    ? `Income (${MONTH_NAMES[latestIncome.month - 1]} ${latestIncome.year})`
    : "Latest Income";

  // Precious metals portfolio
  const goldValue = metalsSummary.data?.current_value ?? 0;
  const existingCorpus = inputs.existing_corpus ?? 0;
  const totalSipInvested = sipTotal.data ?? 0;
  const totalNetWorth = existingCorpus + totalSipInvested + goldValue;

  // Expenses: sum all active monthly-equivalent expenses (matches IncomeExpenses page formula)
  const fixedExpenseTotal = expenses.entries.reduce(
    (sum: number, e: { amount: number; frequency: string }) =>
      sum + effectiveMonthlyAmount(e.amount, e.frequency),
    0
  );

  const totalSip = (inputs.your_sip ?? 0) + (inputs.wife_sip ?? 0);
  const totalOutflow = fixedExpenseTotal + totalSip;
  const monthlySavings = totalIncome - totalOutflow;

  // Asset allocation donut data
  const debtPct = 1 - inputs.equity_pct - inputs.precious_metals_pct - inputs.cash_pct;
  const allocationData = [
    { name: "Equity", value: Math.round(inputs.equity_pct * 100), color: "#00895E" },
    { name: "Precious Metals", value: Math.round(inputs.precious_metals_pct * 100), color: "#D4A843" },
    { name: "Cash", value: Math.round(inputs.cash_pct * 100), color: "#6B7280" },
    { name: "Debt", value: Math.round(debtPct * 100), color: "#1A3A5C" },
  ].filter((d) => d.value > 0);

  // Monthly outflow breakdown
  const outflowData = [
    { name: "Expenses", value: Math.round(fixedExpenseTotal), color: "#E07A5F" },
    { name: "SIPs", value: Math.round(totalSip), color: "#00895E" },
  ].filter((d) => d.value > 0);
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
  const fundedColor: "success" | "warning" | "alert" =
    fundedPct >= 100 ? "success" : fundedPct >= 80 ? "warning" : "alert";
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
        <MetricCard label={incomeLabel} value={totalIncome} />
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
          <div className="mt-2 w-full h-2 bg-[#0D1B2A] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#00895E] to-emerald-400 transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, savingsRate))}%` }}
            />
          </div>
        </div>
      </section>

      {/* Dashboard Widgets: MF Portfolio, Money Ledger, SIP Discipline */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MFPortfolioWidget />
        <MoneyLedgerWidget />
        <SipDisciplineWidget />
      </section>

      {/* Outflow Breakdown + Asset Allocation */}
      {(allocationData.length > 0 || outflowData.length > 0) && (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Outflow Breakdown */}
          {outflowData.length > 0 && (
            <div className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#E8ECF1]/60 mb-4">
                Monthly Outflow Breakdown
              </h3>
              <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6">
                <div className="flex-shrink-0">
                  <PieChart width={130} height={130}>
                    <Pie
                      data={outflowData}
                      cx={60}
                      cy={60}
                      innerRadius={36}
                      outerRadius={58}
                      dataKey="value"
                      strokeWidth={0}
                    >
                      {outflowData.map((entry, index) => (
                        <Cell key={index} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#132E3D",
                        border: "1px solid #1A3A5C",
                        borderRadius: "8px",
                        color: "#E8ECF1",
                        fontSize: 12,
                      }}
                      formatter={(value: any) => [formatRupees(Number(value)), ""]}
                    />
                  </PieChart>
                </div>
                <div className="flex flex-col gap-3 flex-1">
                  {outflowData.map((d, i) => {
                    const total = outflowData.reduce((s, x) => s + x.value, 0);
                    const pct = total > 0 ? Math.round((d.value / total) * 100) : 0;
                    return (
                      <div key={i} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                            style={{ backgroundColor: d.color }}
                          />
                          <span className="text-sm text-[#E8ECF1]/70">{d.name}</span>
                        </div>
                        <div className="text-right">
                          <span
                            className="text-sm font-semibold text-[#E8ECF1]"
                            style={{ fontVariantNumeric: "tabular-nums" }}
                          >
                            {formatRupees(d.value)}
                          </span>
                          <span className="text-[10px] text-[#E8ECF1]/40 ml-1.5">
                            {pct}%
                          </span>
                        </div>
                      </div>
                    );
                  })}
                  <div className="pt-2 border-t border-white/5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-[#E8ECF1]/40 uppercase tracking-wider">Total</span>
                      <span
                        className="text-sm font-bold text-[#E8ECF1]"
                        style={{ fontVariantNumeric: "tabular-nums" }}
                      >
                        {formatRupees(outflowData.reduce((s, x) => s + x.value, 0))}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Asset Allocation */}
          {allocationData.length > 0 && (
            <div className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#E8ECF1]/60 mb-4">
                Asset Allocation
              </h3>
              <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6">
                <div className="flex-shrink-0">
                  <PieChart width={130} height={130}>
                    <Pie
                      data={allocationData}
                      cx={60}
                      cy={60}
                      innerRadius={36}
                      outerRadius={58}
                      dataKey="value"
                      strokeWidth={0}
                    >
                      {allocationData.map((entry, index) => (
                        <Cell key={index} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#132E3D",
                        border: "1px solid #1A3A5C",
                        borderRadius: "8px",
                        color: "#E8ECF1",
                        fontSize: 12,
                      }}
                      formatter={(value: any) => [`${Number(value)}%`, ""]}
                    />
                  </PieChart>
                </div>
                <div className="flex flex-col gap-3 flex-1">
                  {allocationData.map((d, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: d.color }}
                        />
                        <span className="text-sm text-[#E8ECF1]/70">{d.name}</span>
                      </div>
                      <span
                        className="text-sm font-semibold text-[#E8ECF1]"
                        style={{ fontVariantNumeric: "tabular-nums" }}
                      >
                        {d.value}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Net Worth */}
      <section className="bg-[#D4A843]/5 border border-[#D4A843]/20 rounded-2xl p-6">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[#D4A843] mb-4">Net Worth</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-[#E8ECF1]/50 mb-1">Existing Corpus</p>
            <p className="text-lg font-bold text-[#E8ECF1]" style={{ fontVariantNumeric: "tabular-nums" }}>
              {formatRupees(Math.round(existingCorpus))}
            </p>
          </div>
          <div>
            <p className="text-xs text-[#E8ECF1]/50 mb-1">SIP Invested</p>
            <p className="text-lg font-bold text-[#00895E]" style={{ fontVariantNumeric: "tabular-nums" }}>
              {totalSipInvested > 0 ? formatRupees(Math.round(totalSipInvested)) : "--"}
            </p>
          </div>
          <div>
            <p className="text-xs text-[#E8ECF1]/50 mb-1">Precious Metals</p>
            <p className="text-lg font-bold text-[#D4A843]" style={{ fontVariantNumeric: "tabular-nums" }}>
              {goldValue > 0 ? formatRupees(Math.round(goldValue)) : "--"}
            </p>
            {goldValue > 0 && metalsSummary.data && (
              <p className="text-[10px] text-[#E8ECF1]/40 mt-0.5">
                {metalsSummary.data.total_weight_grams}g total metals
              </p>
            )}
          </div>
          <div>
            <p className="text-xs text-[#E8ECF1]/50 mb-1">Total Net Worth</p>
            <p className="text-lg font-bold text-[#00895E]" style={{ fontVariantNumeric: "tabular-nums" }}>
              {formatRupees(Math.round(totalNetWorth))}
            </p>
          </div>
        </div>
      </section>

      {/* FIRE Metrics */}
      {(retirement.isLoading || growth.isLoading) ? (
        <LoadingState message="Loading projections..." />
      ) : (
        <>
          {/* Warning: monthly expense not configured */}
          {requiredCorpus === 0 && (
            <div
              className="bg-[#E5A100]/10 border border-[#E5A100]/30 rounded-xl p-4 flex items-start gap-3 cursor-pointer hover:bg-[#E5A100]/15 transition-colors"
              onClick={() => navigate("/fire-settings")}
            >
              <span className="text-[#E5A100] text-lg leading-none">!</span>
              <div>
                <p className="text-sm font-medium text-[#E5A100]">
                  Monthly expense not configured
                </p>
                <p className="text-xs text-[#E8ECF1]/50 mt-0.5">
                  Required Corpus, Funded Ratio, and SWP calculations need your monthly expense.
                  {fixedExpenseTotal > 0 && (
                    <> Your tracked expenses total {formatRupees(Math.round(fixedExpenseTotal))}/mo — consider using this in FIRE Settings.</>
                  )}
                  {" "}Click here to update.
                </p>
              </div>
            </div>
          )}

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
                      : "text-[#E07A5F]"
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
                      : "bg-[#E07A5F]/20 text-[#E07A5F]"
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
              {monthlyExpenseAtRetirement > 0 ? (
                <div
                  className={`mt-1 flex items-center text-xs font-bold ${
                    surplus >= 0 ? "text-[#2E8B57]" : "text-[#E5A100]"
                  }`}
                >
                  {surplus >= 0 ? "+" : "-"} {formatRupees(Math.round(Math.abs(surplus)))}{" "}
                  vs expense ({formatRupees(Math.round(monthlyExpenseAtRetirement))})
                </div>
              ) : (
                <p className="mt-1 text-xs text-[#E8ECF1]/40">
                  Set monthly expense in FIRE Settings
                </p>
              )}
            </div>
          </section>
        </>
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
                Long-term wealth compounding (Equity, Debt, Metals)
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
                  Debt + Metals + Cash (
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
                    String(name) === "equity" ? "Equity" : "Debt+Metals+Cash",
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
