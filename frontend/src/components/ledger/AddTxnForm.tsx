import { useState } from "react";
import { Plus } from "lucide-react";
import type {
  LedgerTxnInput,
  LedgerDirection,
  LedgerCategory,
  LedgerPaymentMethod,
} from "../../hooks/useLedgerTxns";

interface Props {
  contactId: string;
  onSave: (data: LedgerTxnInput) => Promise<unknown>;
}

const CATEGORIES: { value: LedgerCategory; label: string }[] = [
  { value: "loan", label: "Loan" },
  { value: "borrowed", label: "Borrowed" },
  { value: "payment", label: "Payment" },
  { value: "advance", label: "Advance" },
  { value: "other", label: "Other" },
];

const PAYMENT_METHODS: { value: LedgerPaymentMethod; label: string }[] = [
  { value: "cash", label: "Cash" },
  { value: "upi", label: "UPI" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "other", label: "Other" },
];

const inputCls =
  "w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1] placeholder-[#E8ECF1]/30 focus:outline-none focus:border-[#00895E]/60";
const selectCls =
  "w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1] focus:outline-none focus:border-[#00895E]/60";
const labelCls = "block text-xs text-[#E8ECF1]/60 mb-1";

export function AddTxnForm({ contactId, onSave }: Props) {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [direction, setDirection] = useState<LedgerDirection>("gave");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState<LedgerCategory>("loan");
  const [paymentMethod, setPaymentMethod] = useState<LedgerPaymentMethod>("cash");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const parsedAmount = parseFloat(amount);
    if (!amount || isNaN(parsedAmount) || parsedAmount <= 0) {
      setError("Amount must be greater than 0");
      return;
    }

    setSaving(true);
    try {
      await onSave({
        contact_id: contactId,
        direction,
        amount: parsedAmount,
        date,
        category,
        payment_method: paymentMethod,
        note: note.trim() || null,
      });
      setAmount("");
      setNote("");
      setDate(new Date().toISOString().slice(0, 10));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save transaction");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mt-3">
      <div className="bg-[#0D1B2A] rounded-lg p-3 border border-[#1A3A5C]/30">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 items-end">
          {/* Date */}
          <div>
            <label htmlFor={`txn-date-${contactId}`} className={labelCls}>
              Date
            </label>
            <input
              id={`txn-date-${contactId}`}
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className={inputCls}
            />
          </div>

          {/* Direction toggle */}
          <div>
            <label className={labelCls}>Direction</label>
            <div className="flex rounded overflow-hidden border border-[#1A3A5C]/50">
              <button
                type="button"
                onClick={() => setDirection("gave")}
                className={`flex-1 px-2 py-1.5 text-xs font-medium transition-colors ${
                  direction === "gave"
                    ? "bg-[#E5A100] text-[#0D1B2A]"
                    : "bg-[#0D1B2A] text-[#E8ECF1]/60 hover:text-[#E8ECF1]"
                }`}
              >
                Gave
              </button>
              <button
                type="button"
                onClick={() => setDirection("received")}
                className={`flex-1 px-2 py-1.5 text-xs font-medium transition-colors ${
                  direction === "received"
                    ? "bg-[#00895E] text-white"
                    : "bg-[#0D1B2A] text-[#E8ECF1]/60 hover:text-[#E8ECF1]"
                }`}
              >
                Received
              </button>
            </div>
          </div>

          {/* Amount */}
          <div>
            <label htmlFor={`txn-amount-${contactId}`} className={labelCls}>
              Amount <span className="text-[#E5A100]">*</span>
            </label>
            <input
              id={`txn-amount-${contactId}`}
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              min="0.01"
              step="0.01"
              required
              className={inputCls}
            />
          </div>

          {/* Category */}
          <div>
            <label htmlFor={`txn-category-${contactId}`} className={labelCls}>
              Category
            </label>
            <select
              id={`txn-category-${contactId}`}
              value={category}
              onChange={(e) => setCategory(e.target.value as LedgerCategory)}
              className={selectCls}
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* Payment Method */}
          <div>
            <label htmlFor={`txn-method-${contactId}`} className={labelCls}>
              Method
            </label>
            <select
              id={`txn-method-${contactId}`}
              value={paymentMethod}
              onChange={(e) =>
                setPaymentMethod(e.target.value as LedgerPaymentMethod)
              }
              className={selectCls}
            >
              {PAYMENT_METHODS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>

          {/* Note */}
          <div>
            <label htmlFor={`txn-note-${contactId}`} className={labelCls}>
              Note
            </label>
            <input
              id={`txn-note-${contactId}`}
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Optional"
              maxLength={200}
              autoComplete="off"
              className={inputCls}
            />
          </div>
        </div>

        <div className="mt-2 flex items-center gap-3">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-1 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded px-3 py-1.5 text-sm font-medium disabled:opacity-50 transition-colors"
          >
            <Plus size={14} />
            {saving ? "Saving..." : "Add Entry"}
          </button>
          {error && <p className="text-[#E5A100] text-sm">{error}</p>}
        </div>
      </div>
    </form>
  );
}
