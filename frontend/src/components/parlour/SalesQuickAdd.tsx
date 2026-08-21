import { useState } from "react";
import { Plus } from "lucide-react";

interface SalesQuickAddProps {
  onSave: (data: {
    sale_date: string;
    cash_amount: number;
    online_amount: number;
    sender_name?: string;
  }) => Promise<unknown>;
}

export function SalesQuickAdd({ onSave }: SalesQuickAddProps) {
  const [saleDate, setSaleDate] = useState(new Date().toISOString().slice(0, 10));
  const [cash, setCash] = useState("");
  const [online, setOnline] = useState("");
  const [sender, setSender] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    const cashNum = parseFloat(cash || "0") || 0;
    const onlineNum = parseFloat(online || "0") || 0;
    if (cashNum + onlineNum <= 0) {
      setError("Enter at least one amount (cash or online)");
      return;
    }
    if (!saleDate) {
      setError("Select a date");
      return;
    }
    setError("");
    setSaving(true);
    try {
      await onSave({
        sale_date: saleDate,
        cash_amount: cashNum,
        online_amount: onlineNum,
        sender_name: sender.trim() || undefined,
      });
      setCash("");
      setOnline("");
      setSender("");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
      <h3 className="text-sm font-semibold text-[#E8ECF1] mb-3">Add Daily Sales</h3>
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 items-end">
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Date</label>
          <input
            type="date"
            value={saleDate}
            onChange={(e) => setSaleDate(e.target.value)}
            className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Cash (₹)</label>
          <input
            type="number"
            min="0"
            value={cash}
            onChange={(e) => setCash(e.target.value)}
            placeholder="0"
            className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Online (₹)</label>
          <input
            type="number"
            min="0"
            value={online}
            onChange={(e) => setOnline(e.target.value)}
            placeholder="0"
            className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Sender (optional)</label>
          <input
            type="text"
            value={sender}
            onChange={(e) => setSender(e.target.value)}
            placeholder="e.g. Swapnil"
            maxLength={100}
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
