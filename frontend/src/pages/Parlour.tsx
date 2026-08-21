import { useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { ParlourProvider, useParlour } from "../contexts/ParlourContext";
import { ParlourSummaryCards } from "../components/parlour/ParlourSummaryCards";
import { SalesQuickAdd } from "../components/parlour/SalesQuickAdd";
import { SalesTable } from "../components/parlour/SalesTable";
import { WhatsAppImport } from "../components/parlour/WhatsAppImport";
import { InvoiceUpload } from "../components/parlour/InvoiceUpload";
import { InvoiceList } from "../components/parlour/InvoiceList";
import { OtherExpenses } from "../components/parlour/OtherExpenses";
import { PnLCharts } from "../components/parlour/PnLCharts";
import { SarvamWidget } from "../components/parlour/SarvamWidget";
import { useParlours } from "../hooks/useParlours";
import { useAmulSales } from "../hooks/useAmulSales";
import { useAmulInvoices } from "../hooks/useAmulInvoices";
import { useAmulOtherExpenses } from "../hooks/useAmulOtherExpenses";
import { useAmulAnalytics } from "../hooks/useAmulAnalytics";
import { useSarvamUsage } from "../hooks/useSarvamUsage";
import { useParlourMembers } from "../hooks/useParlourMembers";
import { useAuth } from "../contexts/AuthContext";
import { formatPeriodValue, periodLabel } from "../lib/parlourCalculations";
import { PeriodPicker, type PeriodSelection } from "../components/parlour/PeriodPicker";
import { MembersManager } from "../components/parlour/MembersManager";

type Tab = "sales" | "purchases" | "expenses" | "analytics" | "sarvam" | "members";

const TABS: { value: Tab; label: string }[] = [
  { value: "sales", label: "Sales" },
  { value: "purchases", label: "Purchases" },
  { value: "expenses", label: "Other Expenses" },
  { value: "analytics", label: "Analytics" },
  { value: "sarvam", label: "Sarvam" },
  { value: "members", label: "Members" },
];

function ParlourInner() {
  const { parlours, isLoading: parloursLoading, save: saveParlour } = useParlours();
  const { user } = useAuth();
  const { selectedParlourId, setSelectedParlour } = useParlour();

  const activeId = selectedParlourId || parlours[0]?.id || "";
  const activeParlour = parlours.find((p) => p.id === activeId);
  // The authoritative role comes from the parlours list (API membership).
  const isOwner = activeParlour?.role === "owner";

  const [tab, setTab] = useState<Tab>("sales");
  const now = new Date();
  const [periodSel, setPeriodSel] = useState<PeriodSelection>({
    period: "month",
    periodValue: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`,
  });
  const [showNewParlour, setShowNewParlour] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCredits, setNewCredits] = useState("");

  const { sales, isLoading: salesLoading, save: saveSale, update: updateSale, remove: removeSale, importWhatsApp } =
    useAmulSales(activeId);
  const {
    invoices,
    isLoading: invoicesLoading,
    upload: uploadInvoices,
    remove: removeInvoice,
  } = useAmulInvoices(activeId);
  const {
    expenses,
    isLoading: expensesLoading,
    save: saveExpense,
    remove: removeExpense,
  } = useAmulOtherExpenses(activeId);
  const { data: analytics, isLoading: analyticsLoading } = useAmulAnalytics(
    activeId,
    { period: periodSel.period, periodValue: periodSel.periodValue }
  );
  const { data: sarvamSpend, isLoading: sarvamLoading } = useSarvamUsage(activeId);
  const membersHook = useParlourMembers(activeId);

  const handleCreateParlour = async () => {
    if (!newName.trim()) return;
    const result = (await saveParlour({
      name: newName.trim(),
      sarvam_starting_credits: newCredits ? parseFloat(newCredits) : 0,
    })) as {
      data?: { id?: string };
    };
    setNewName("");
    setNewCredits("");
    setShowNewParlour(false);
    if (result?.data?.id) {
      setSelectedParlour(result.data.id, "owner");
    }
  };

  if (parloursLoading) return <LoadingState />;

  return (
    <div>
      <PageHeader
        title="Parlour"
        subtitle="Vrindavan Treats — daily sales, purchases, and P&L"
      />

      {/* Parlour selector + New */}
      <div className="flex items-center gap-3 mb-6">
        <select
          value={activeId}
          onChange={(e) => {
            const p = parlours.find((x) => x.id === e.target.value);
            setSelectedParlour(e.target.value, p?.role ?? "data_entry");
          }}
          className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded-lg px-4 py-2 text-sm text-[#E8ECF1] min-w-[200px]"
        >
          {parlours.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} {p.role === "owner" ? "(Owner)" : ""}
            </option>
          ))}
        </select>
        <button
          onClick={() => setShowNewParlour(!showNewParlour)}
          className="flex items-center gap-1 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          New Parlour
        </button>
      </div>

      {showNewParlour && (
        <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
          <div className="flex gap-3 items-end flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">Parlour Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                maxLength={100}
                placeholder="e.g. Vrindavan Treats"
                className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
              />
            </div>
            <div className="w-40">
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">
                Sarvam Starting Credits
              </label>
              <input
                type="number"
                min="0"
                value={newCredits}
                onChange={(e) => setNewCredits(e.target.value)}
                placeholder="e.g. 500"
                className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
              />
            </div>
            <button
              onClick={handleCreateParlour}
              disabled={!newName.trim()}
              className="bg-[#D4A843] hover:bg-[#D4A843]/80 text-[#0D1B2A] rounded px-4 py-1.5 text-sm font-medium disabled:opacity-50 transition-colors"
            >
              Create
            </button>
          </div>
        </div>
      )}

      {parlours.length === 0 && !showNewParlour && (
        <EmptyState message="No parlours yet — create one to start tracking the business" />
      )}

      {activeId && (
        <>
          {/* Tabs */}
          <div className="flex gap-2 mb-6 border-b border-[#1A3A5C]/30">
            {TABS.map((t) => (
              <button
                key={t.value}
                onClick={() => setTab(t.value)}
                className={`px-4 py-2 text-sm border-b-2 transition-colors ${
                  tab === t.value
                    ? "border-[#00895E] text-[#00895E] font-medium"
                    : "border-transparent text-[#E8ECF1]/60 hover:text-[#E8ECF1]"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === "sales" && (
            <>
              <SalesQuickAdd onSave={saveSale} />
              <WhatsAppImport onImport={importWhatsApp} />
              {salesLoading ? (
                <LoadingState />
              ) : sales.length === 0 ? (
                <EmptyState message="No sales yet — add today's cash & online totals from the WhatsApp group" />
              ) : (
                <SalesTable
                  sales={sales}
                  onRemove={removeSale}
                  onUpdate={(id, data) => updateSale({ id, data })}
                />
              )}
            </>
          )}

          {tab === "purchases" && (
            <>
              <InvoiceUpload onUpload={uploadInvoices} />
              {invoicesLoading ? (
                <LoadingState />
              ) : (
                <InvoiceList
                  invoices={invoices}
                  parlourId={activeId}
                  onRemove={removeInvoice}
                />
              )}
            </>
          )}

          {tab === "expenses" && (
            <>
              {expensesLoading ? (
                <LoadingState />
              ) : (
                <OtherExpenses
                  expenses={expenses}
                  onSave={saveExpense}
                  onRemove={removeExpense}
                />
              )}
            </>
          )}

          {tab === "analytics" && (
            <>
              <div className="flex items-center gap-3 mb-4 flex-wrap">
                <PeriodPicker value={periodSel} onChange={setPeriodSel} />
                <span className="text-xs text-[#E8ECF1]/50">
                  {periodLabel(periodSel.period)} view —{" "}
                  {formatPeriodValue(analytics?.summary.period_key || periodSel.periodValue)}
                </span>
              </div>
              {analyticsLoading ? (
                <LoadingState />
              ) : (
                <>
                  <ParlourSummaryCards
                    summary={analytics?.summary}
                    isLoading={analyticsLoading}
                  />
                  <PnLCharts trends={analytics?.trends} isLoading={analyticsLoading} />
                </>
              )}
            </>
          )}

          {tab === "sarvam" && (
            <>
              {!isOwner ? (
                <EmptyState message="Only the parlour owner can view Sarvam credit usage" />
              ) : (
                <>
                  <SarvamWidget spend={sarvamSpend} isLoading={sarvamLoading} />
                  <EmptyState message="Sarvam OCR credits are tracked here — every extraction logs its usage." />
                </>
              )}
            </>
          )}

          {tab === "members" && (
            <>
              {!isOwner ? (
                <EmptyState message="Only the parlour owner can manage members" />
              ) : (
                <MembersManager
                  members={membersHook.members}
                  currentUserId={user?.id}
                  isLoading={membersHook.isLoading}
                  onAdd={membersHook.addMember}
                  onRemove={membersHook.removeMember}
                />
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

export default function Parlour() {
  return (
    <ParlourProvider>
      <ParlourInner />
    </ParlourProvider>
  );
}
