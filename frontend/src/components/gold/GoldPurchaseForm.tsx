import { useState } from "react";
import type { GoldPurchaseCreate, GoldPurity, GoldOwner } from "../../hooks/useGoldPurchases";
import { inputCls, btnPrimary } from "../../lib/styles";

interface GoldFormState {
  purchase_date: string;
  weight_grams: number | "";
  price_per_gram: number | "";
  purity: GoldPurity;
  owner: GoldOwner;
  notes: string;
}

interface GoldPurchaseFormProps {
  onSave: (data: GoldPurchaseCreate) => Promise<unknown>;
}

function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}

export function GoldPurchaseForm({ onSave }: GoldPurchaseFormProps) {
  const [form, setForm] = useState<GoldFormState>({
    purchase_date: todayISO(),
    weight_grams: "",
    price_per_gram: "",
    purity: "24K",
    owner: "you",
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const weight = Number(form.weight_grams);
    const price = Number(form.price_per_gram);

    if (!weight || weight <= 0) {
      setError("Weight must be greater than 0");
      return;
    }
    if (!price || price <= 0) {
      setError("Price per gram must be greater than 0");
      return;
    }

    setSaving(true);
    try {
      const payload: GoldPurchaseCreate = {
        purchase_date: form.purchase_date,
        weight_grams: weight,
        price_per_gram: price,
        purity: form.purity,
        owner: form.owner,
        ...(form.notes.trim() ? { notes: form.notes.trim() } : {}),
      };
      await onSave(payload);
      setForm({
        purchase_date: todayISO(),
        weight_grams: "",
        price_per_gram: "",
        purity: "24K",
        owner: "you",
        notes: "",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save purchase");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-[#132E3D] rounded-xl p-4 mb-4 border border-[#1A3A5C]/30"
    >
      <h3 className="text-sm font-medium text-[#E8ECF1]/80 mb-3">Add Gold Purchase</h3>
      {error && (
        <div className="mb-3 px-4 py-2 bg-[#E5A100]/10 border border-[#E5A100]/30 rounded-lg text-[#E5A100] text-sm">
          {error}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-7 gap-3 items-end">
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Date</label>
          <input
            type="date"
            value={form.purchase_date}
            onChange={(e) => setForm({ ...form, purchase_date: e.target.value })}
            required
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Weight (g)</label>
          <input
            type="number"
            placeholder="e.g. 10"
            value={form.weight_grams}
            onChange={(e) =>
              setForm({ ...form, weight_grams: e.target.value === "" ? "" : Number(e.target.value) })
            }
            required
            min={0.001}
            step="any"
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Price/g (INR)</label>
          <input
            type="number"
            placeholder="e.g. 6500"
            value={form.price_per_gram}
            onChange={(e) =>
              setForm({ ...form, price_per_gram: e.target.value === "" ? "" : Number(e.target.value) })
            }
            required
            min={1}
            step="any"
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Purity</label>
          <select
            value={form.purity}
            onChange={(e) => setForm({ ...form, purity: e.target.value as GoldPurity })}
            className={inputCls}
          >
            <option value="24K">24K</option>
            <option value="22K">22K</option>
            <option value="18K">18K</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Owner</label>
          <select
            value={form.owner}
            onChange={(e) => setForm({ ...form, owner: e.target.value as GoldOwner })}
            className={inputCls}
          >
            <option value="you">You</option>
            <option value="wife">Wife</option>
            <option value="household">Household</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Notes</label>
          <input
            type="text"
            placeholder="Optional"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            maxLength={500}
            className={inputCls}
          />
        </div>
        <button type="submit" disabled={saving} className={btnPrimary}>
          {saving ? "Saving..." : "Add"}
        </button>
      </div>
    </form>
  );
}
