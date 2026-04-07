import { useState } from "react";
import { Search } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { LedgerSummaryCards } from "../components/ledger/LedgerSummaryCards";
import { AddContactForm } from "../components/ledger/AddContactForm";
import { ContactsList } from "../components/ledger/ContactsList";
import { useLedgerContacts, useLedgerSummary } from "../hooks/useLedgerContacts";

export default function MoneyLedger() {
  const { contacts, isLoading, save, deactivate } = useLedgerContacts();
  const { data: summary, isLoading: summaryLoading } = useLedgerSummary();
  const [search, setSearch] = useState("");

  if (isLoading) return <LoadingState />;

  return (
    <div>
      <PageHeader
        title="Money Ledger"
        subtitle="Track money given to and received from people"
      />

      <LedgerSummaryCards
        summary={summary}
        isLoading={summaryLoading}
      />

      <AddContactForm onSave={save} />

      {/* Search */}
      <div className="relative mb-4 max-w-xs">
        <Search
          size={15}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[#E8ECF1]/40 pointer-events-none"
        />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search people..."
          className="w-full bg-[#132E3D] border border-[#1A3A5C]/50 rounded-lg pl-8 pr-3 py-1.5 text-sm text-[#E8ECF1] placeholder-[#E8ECF1]/30 focus:outline-none focus:border-[#00895E]/60"
        />
      </div>

      <ContactsList
        contacts={contacts}
        search={search}
        onDeactivate={deactivate}
      />
    </div>
  );
}
