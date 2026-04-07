import { memo, useState, useCallback } from "react";
import { ChevronDown, ChevronRight, Trash2 } from "lucide-react";
import { formatRupees } from "../../lib/formatIndian";
import { TransactionHistory } from "./TransactionHistory";
import { AddTxnForm } from "./AddTxnForm";
import { useLedgerTxns } from "../../hooks/useLedgerTxns";
import type { LedgerContact } from "../../hooks/useLedgerContacts";
import type { LedgerTxnInput } from "../../hooks/useLedgerTxns";

interface ContactRowProps {
  contact: LedgerContact;
  isExpanded: boolean;
  onToggle: (id: string) => void;
  onDeactivate: (id: string) => Promise<unknown>;
}

const ContactRow = memo(function ContactRow({
  contact,
  isExpanded,
  onToggle,
  onDeactivate,
}: ContactRowProps) {
  const { txns, isLoading, save, deleteTxn } = useLedgerTxns(
    isExpanded ? contact.id : ""
  );

  const balanceColor =
    contact.balance > 0
      ? "text-[#00895E]"
      : contact.balance < 0
      ? "text-[#E5A100]"
      : "text-[#E8ECF1]/60";

  const balancePrefix = contact.balance > 0 ? "+" : "";

  const handleDeactivate = async () => {
    if (
      !window.confirm(
        `Remove ${contact.name} from your ledger? Their transaction history will be hidden.`
      )
    )
      return;
    await onDeactivate(contact.id);
  };

  const handleSaveTxn = useCallback(
    (data: LedgerTxnInput) => save(data),
    [save]
  );

  return (
    <>
      <tr
        className="border-t border-[#1A3A5C]/20 hover:bg-[#132E3D]/40 cursor-pointer text-[#E8ECF1] transition-colors"
        onClick={() => onToggle(contact.id)}
        aria-expanded={isExpanded}
        aria-label={`View transactions for ${contact.name}`}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggle(contact.id);
          }
        }}
      >
        <td className="px-4 py-3 font-medium">
          <span className="flex items-center gap-2">
            {isExpanded ? (
              <ChevronDown size={15} className="text-[#E8ECF1]/40 shrink-0" />
            ) : (
              <ChevronRight size={15} className="text-[#E8ECF1]/40 shrink-0" />
            )}
            {contact.name}
            {contact.phone && (
              <span className="text-xs text-[#E8ECF1]/40">{contact.phone}</span>
            )}
          </span>
        </td>
        <td
          className="px-4 py-3 text-right text-[#E8ECF1]/70"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {formatRupees(contact.total_gave)}
        </td>
        <td
          className="px-4 py-3 text-right text-[#E8ECF1]/70"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {formatRupees(contact.total_received)}
        </td>
        <td className="px-4 py-3 text-right">
          <span
            className={`font-medium ${balanceColor}`}
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {balancePrefix}
            {formatRupees(Math.abs(contact.balance))}
          </span>
          <span className="ml-1.5 text-xs text-[#E8ECF1]/40">
            {contact.balance_label}
          </span>
        </td>
        <td className="px-3 py-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDeactivate();
            }}
            aria-label={`Remove ${contact.name}`}
            className="p-1 text-[#E8ECF1]/20 hover:text-[#E5A100] rounded transition-colors"
          >
            <Trash2 size={14} />
          </button>
        </td>
      </tr>

      {isExpanded && (
        <tr className="border-t border-[#1A3A5C]/10">
          <td colSpan={5} className="px-4 py-3 bg-[#0D1B2A]/60">
            <div className="border-l-2 border-[#1A3A5C]/40 pl-4">
              <TransactionHistory
                txns={txns}
                isLoading={isLoading}
                onDelete={deleteTxn}
              />
              <AddTxnForm contactId={contact.id} onSave={handleSaveTxn} />
            </div>
          </td>
        </tr>
      )}
    </>
  );
});

interface Props {
  contacts: LedgerContact[];
  search: string;
  onDeactivate: (id: string) => Promise<unknown>;
}

export function ContactsList({ contacts, search, onDeactivate }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleToggle = useCallback((id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  const filtered = search
    ? contacts.filter((c) =>
        c.name.toLowerCase().includes(search.toLowerCase())
      )
    : contacts;

  if (filtered.length === 0) {
    return (
      <p className="text-center text-[#E8ECF1]/40 py-8">
        {search ? "No contacts match your search" : "No contacts yet — add someone above"}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-[#1A3A5C]/30">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[#132E3D] text-[#E8ECF1]/60 text-left">
            <th className="px-4 py-2">Name</th>
            <th className="px-4 py-2 text-right">Given</th>
            <th className="px-4 py-2 text-right">Received</th>
            <th className="px-4 py-2 text-right">Balance</th>
            <th className="px-3 py-2 w-10"></th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((contact) => (
            <ContactRow
              key={contact.id}
              contact={contact}
              isExpanded={expandedId === contact.id}
              onToggle={handleToggle}
              onDeactivate={onDeactivate}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
