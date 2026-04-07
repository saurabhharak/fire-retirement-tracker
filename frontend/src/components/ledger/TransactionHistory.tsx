import { Trash2 } from "lucide-react";
import { formatRupees } from "../../lib/formatIndian";
import { LoadingState } from "../LoadingState";
import type { LedgerTxn } from "../../hooks/useLedgerTxns";

interface Props {
  txns: LedgerTxn[];
  isLoading: boolean;
  onDelete: (id: string) => Promise<unknown>;
}

const CATEGORY_LABELS: Record<string, string> = {
  loan: "Loan",
  borrowed: "Borrowed",
  payment: "Payment",
  advance: "Advance",
  other: "Other",
};

const METHOD_LABELS: Record<string, string> = {
  cash: "Cash",
  upi: "UPI",
  bank_transfer: "Bank Transfer",
  other: "Other",
};

export function TransactionHistory({ txns, isLoading, onDelete }: Props) {
  if (isLoading) return <LoadingState message="Loading transactions..." />;

  if (txns.length === 0) {
    return (
      <p className="text-[#E8ECF1]/40 text-sm py-4 text-center">
        No transactions yet
      </p>
    );
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm("Delete this transaction? This cannot be undone.")) return;
    await onDelete(id);
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-[#1A3A5C]/20 mt-2">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[#0D1B2A] text-[#E8ECF1]/50 text-left">
            <th className="px-3 py-2">Date</th>
            <th className="px-3 py-2">Direction</th>
            <th className="px-3 py-2 text-right">Amount</th>
            <th className="px-3 py-2">Category</th>
            <th className="px-3 py-2">Method</th>
            <th className="px-3 py-2">Note</th>
            <th className="px-3 py-2 w-10"></th>
          </tr>
        </thead>
        <tbody>
          {txns.map((txn) => (
            <tr
              key={txn.id}
              className="border-t border-[#1A3A5C]/20 hover:bg-[#132E3D]/30 text-[#E8ECF1]"
            >
              <td className="px-3 py-2 text-[#E8ECF1]/70">{txn.date}</td>
              <td className="px-3 py-2">
                <span
                  className={`text-xs font-medium ${
                    txn.direction === "gave"
                      ? "text-[#E5A100]"
                      : "text-[#00895E]"
                  }`}
                >
                  {txn.direction === "gave" ? "Gave" : "Received"}
                </span>
              </td>
              <td
                className="px-3 py-2 text-right font-medium"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {formatRupees(txn.amount)}
              </td>
              <td className="px-3 py-2 text-[#E8ECF1]/70">
                {CATEGORY_LABELS[txn.category] ?? txn.category}
              </td>
              <td className="px-3 py-2 text-[#E8ECF1]/70">
                {METHOD_LABELS[txn.payment_method] ?? txn.payment_method}
              </td>
              <td className="px-3 py-2 text-[#E8ECF1]/50 max-w-[120px] truncate">
                {txn.note || "\u2014"}
              </td>
              <td className="px-3 py-2">
                <button
                  onClick={() => handleDelete(txn.id)}
                  aria-label="Delete transaction"
                  className="p-1 text-[#E8ECF1]/30 hover:text-[#E5A100] rounded transition-colors"
                >
                  <Trash2 size={13} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
