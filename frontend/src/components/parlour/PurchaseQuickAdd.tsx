import { useState } from "react";
import { Plus } from "lucide-react";

interface PurchaseQuickAddProps {
  onSave: (data: {
    purchase_date: string;
    amount: number;
    note?: string;
  }) => Promise<unknown>;
}

export function PurchaseQuickAdd({ onSave }: PurchaseQuickAddProps) {
  const [purchaseDate, setPurchaseDate] = useState(
    new Date().toISOString().slice(0, 10)
  );
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    const amountNum = parseFloat(amount);
    if (isNaN(amountNum) || amountNum < 0) {
      setError("Enter a valid amount (0 or more)");
      return;
    }
    if (!purchaseDate) {
      setError("Select a date");
      return;
    }
    setError("");
    setSaving(true);
    try {
      await onSave({
        purchase_date: purchaseDate,
        amount: amountNum,
        note: note.trim() || undefined,
      });
      setAmount("");
      setNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the purchase");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
      <h3 className="text-sm font-semibold text-[#E8ECF1] mb-3">Add Daily Purchase</h3>
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Date</label>
          <input
            type="date"
            value={purchaseDate}
            onChange={(e) => setPurchaseDate(e.target.value)}
            className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Amount (₹)</label>
          <input
            type="number"
            min="0"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0"
            className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Note (optional)</label>
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. Mahavir stock"
            maxLength={200}
            className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={saving}
          className="flex items-center justify-center gap-1 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 transition-colors"
        >
          <Plus size={16} />
          {saving ? "Saving..." : "Add"}
        </button>
      </div>
      {error && <p className="text-sm text-[#E5A100] mt-2">{error}</p>}
    </div>
  );
}
