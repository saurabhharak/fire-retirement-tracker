import { useState, useMemo } from "react";
import { useIncome } from "../hooks/useIncome";
import { useExpenses } from "../hooks/useExpenses";
import type { FixedExpense } from "../hooks/useExpenses";
import { useFireInputs } from "../hooks/useFireInputs";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { effectiveMonthlyAmount, isExpenseInMonth } from "../lib/expenseUtils";

import { MonthNavigator } from "../components/expenses/MonthNavigator";
import { OwnerFilter } from "../components/expenses/OwnerFilter";
import type { OwnerOption } from "../components/expenses/OwnerFilter";
import { ExpenseTabs } from "../components/expenses/ExpenseTabs";
import type { ExpenseTab } from "../components/expenses/ExpenseTabs";
import { ExpenseQuickAdd } from "../components/expenses/ExpenseQuickAdd";
import { ExpenseTable } from "../components/expenses/ExpenseTable";
import { OwnerTotalsBar } from "../components/expenses/OwnerTotalsBar";
import { FinancialSummary } from "../components/expenses/FinancialSummary";
import { MoneyFlowChart } from "../components/expenses/MoneyFlowChart";
import { IncomeLog } from "../components/expenses/IncomeLog";

const PIE_COLORS = {
  sip: "#00895E",
  your: "#D4A843",
  wife: "#E07A5F",
  household: "#6B7280",
  savings: "#3B82F6",
};

export default function IncomeExpenses() {
  const income = useIncome(24);
  const expenses = useExpenses({ active: true });
  const fireInputs = useFireInputs();

  /* State: month navigator, active tab, owner filter */
  const now = new Date();
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(now.getFullYear());
  const [activeTab, setActiveTab] = useState<ExpenseTab>("all");
  const [ownerFilter, setOwnerFilter] = useState<OwnerOption>("all");

  /* ---------- Derived Calculations (all hooks must run before any early return) ---------- */

  const matchedIncome = income.entries.find(
    (e) => e.month === selectedMonth && e.year === selectedYear,
  );
  const yourIncome = matchedIncome?.your_income ?? 0;
  const wifeIncome = matchedIncome?.wife_income ?? 0;
  const totalIncome = yourIncome + wifeIncome;
  const noIncomeForMonth = !matchedIncome;

  const inputs = fireInputs.data;
  const totalSip = (inputs?.your_sip ?? 0) + (inputs?.wife_sip ?? 0);

  // All expenses for this month (base for all derived memos)
  const allMonthExpenses = useMemo(
    () =>
      (expenses.entries as FixedExpense[]).filter((e) =>
        isExpenseInMonth(e, selectedMonth, selectedYear),
      ),
    [expenses.entries, selectedMonth, selectedYear],
  );

  // Month + tab filtered (no owner filter) — used for owner totals bar
  const tabFilteredExpenses = useMemo(() => {
    if (activeTab === "fixed") return allMonthExpenses.filter((e) => e.frequency !== "one-time");
    if (activeTab === "one-time") return allMonthExpenses.filter((e) => e.frequency === "one-time");
    return allMonthExpenses;
  }, [allMonthExpenses, activeTab]);

  // Full filter (month + tab + owner) — used for expense table
  const filteredExpenses = useMemo(() => {
    if (ownerFilter === "all") return tabFilteredExpenses;
    return tabFilteredExpenses.filter((e) => (e.owner ?? "household") === ownerFilter);
  }, [tabFilteredExpenses, ownerFilter]);

  const { fixedExpenseMonthly, yourExpenses, wifeExpenses, householdExpenses } = useMemo(() => {
    const total = allMonthExpenses.reduce(
      (sum: number, e: FixedExpense) => sum + effectiveMonthlyAmount(e.amount, e.frequency),
      0,
    );
    const you = allMonthExpenses
      .filter((e: FixedExpense) => e.owner === "you")
      .reduce((sum: number, e: FixedExpense) => sum + effectiveMonthlyAmount(e.amount, e.frequency), 0);
    const wife = allMonthExpenses
      .filter((e: FixedExpense) => e.owner === "wife")
      .reduce((sum: number, e: FixedExpense) => sum + effectiveMonthlyAmount(e.amount, e.frequency), 0);
    const household = allMonthExpenses
      .filter((e: FixedExpense) => e.owner === "household" || !e.owner)
      .reduce((sum: number, e: FixedExpense) => sum + effectiveMonthlyAmount(e.amount, e.frequency), 0);
    return { fixedExpenseMonthly: total, yourExpenses: you, wifeExpenses: wife, householdExpenses: household };
  }, [allMonthExpenses]);

  const totalOutflow = fixedExpenseMonthly + totalSip;
  const savings = totalIncome - totalOutflow;
  const savingsRate =
    totalIncome > 0 ? Math.round((savings / totalIncome) * 1000) / 10 : 0;

  const pieData = useMemo(
    () =>
      [
        { name: "SIP", value: Math.round(totalSip), color: PIE_COLORS.sip },
        { name: "Your Expenses", value: Math.round(yourExpenses), color: PIE_COLORS.your },
        { name: "Wife Expenses", value: Math.round(wifeExpenses), color: PIE_COLORS.wife },
        { name: "Household", value: Math.round(householdExpenses), color: PIE_COLORS.household },
        {
          name: "Savings",
          value: Math.round(Math.max(0, savings - totalSip)),
          color: PIE_COLORS.savings,
        },
      ].filter((d) => d.value > 0),
    [totalSip, yourExpenses, wifeExpenses, householdExpenses, savings],
  );

  /* Loading — after all hooks */
  if (income.isLoading || expenses.isLoading || fireInputs.isLoading) {
    return <LoadingState message="Loading income & expenses..." />;
  }

  /* Handlers */
  async function handleExpenseDeactivate(id: string) {
    if (!window.confirm("Deactivate this expense?")) return;
    await expenses.deactivate(id);
  }

  async function handleExpenseEdit(id: string, data: import("../hooks/useExpenses").FixedExpenseUpdate) {
    await expenses.update({ id, data });
  }

  function handleMonthChange(month: number, year: number) {
    setSelectedMonth(month);
    setSelectedYear(year);
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Income & Expenses"
        subtitle="Track your monthly income and fixed expenses"
      />

      {/* Financial Summary */}
      <FinancialSummary
        yourIncome={yourIncome}
        wifeIncome={wifeIncome}
        totalIncome={totalIncome}
        fixedExpenseMonthly={Math.round(fixedExpenseMonthly)}
        totalSip={totalSip}
        totalOutflow={Math.round(totalOutflow)}
        savings={Math.round(savings)}
        savingsRate={savingsRate}
        noIncomeForMonth={noIncomeForMonth}
      />

      {/* Money Flow Chart */}
      <MoneyFlowChart pieData={pieData} totalIncome={totalIncome} />

      {/* Tabs */}
      <ExpenseTabs activeTab={activeTab} onChange={setActiveTab} />

      {/* Income tab shows Income Log */}
      {activeTab === "income" ? (
        <IncomeLog
          entries={income.entries}
          onSave={income.save}
          onRemove={income.remove}
        />
      ) : (
        /* All / Fixed / One-time tabs show expenses */
        <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
          {/* Controls bar */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
            <div>
              <h2 className="text-lg font-semibold text-[#E8ECF1]">
                {activeTab === "one-time" ? "One-time Expenses" : activeTab === "fixed" ? "Fixed Expenses" : "All Expenses"}
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <MonthNavigator
                month={selectedMonth}
                year={selectedYear}
                onChange={handleMonthChange}
              />
              <OwnerFilter selected={ownerFilter} onChange={setOwnerFilter} />
            </div>
          </div>

          {/* Owner totals */}
          <OwnerTotalsBar expenses={tabFilteredExpenses} ownerFilter={ownerFilter} />

          {/* Quick Add */}
          <ExpenseQuickAdd
            selectedMonth={selectedMonth}
            selectedYear={selectedYear}
            onSave={expenses.save}
          />

          {/* Expense Table */}
          <ExpenseTable
            expenses={filteredExpenses}
            showOneTime={activeTab !== "fixed"}
            onDeactivate={handleExpenseDeactivate}
            onEdit={handleExpenseEdit}
          />
        </section>
      )}
    </div>
  );
}
