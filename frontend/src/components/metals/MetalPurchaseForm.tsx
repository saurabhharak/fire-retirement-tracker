import { useState } from "react";
import type { MetalType, MetalOwner, PreciousMetalCreate } from "../../hooks/usePreciousMetals";
import { inputCls, btnPrimary } from "../../lib/styles";

interface MetalFormState {
  metal_type: MetalType;
  purchase_date: string;
  weight_grams: number | "";
  price_per_gram: number | "";
  purity: string;
  owner: MetalOwner;
  notes: string;
}

interface MetalPurchaseFormProps {
  onSave: (data: PreciousMetalCreate) => Promise<unknown>;
  /** When set, pre-selects and locks the metal type dropdown */
  lockedMetal?: MetalType | null;
}

const PURITY_OPTIONS: Record<MetalType, string[]> = {
  gold: ["24K", "22K", "18K"],
  silver: ["999", "925", "900"],
  platinum: ["999", "950", "900"],
};

const DEFAULT_PURITY: Record<MetalType, string> = {
  gold: "24K",
  silver: "999",
  platinum: "999",
};

const METAL_LABELS: Record<MetalType, string> = {
  gold: "Gold",
  silver: "Silver",
  platinum: "Platinum",
};

function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}

export function MetalPurchaseForm({ onSave, lockedMetal }: MetalPurchaseFormProps) {
  const initialMetal: MetalType = lockedMetal ?? "gold";

  const [form, setForm] = useState<MetalFormState>({
    metal_type: initialMetal,
    purchase_date: todayISO(),
    weight_grams: "",
    price_per_gram: "",
    purity: DEFAULT_PURITY[initialMetal],
    owner: "you",
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleMetalChange(metal: MetalType) {
    setForm((prev) => ({
      ...prev,
      metal_type: metal,
      purity: DEFAULT_PURITY[metal],
    }));
  }

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
      const payload: PreciousMetalCreate = {
        metal_type: form.metal_type,
        purchase_date: form.purchase_date,
        weight_grams: weight,
        price_per_gram: price,
        purity: form.purity,
        owner: form.owner,
        ...(form.notes.trim() ? { notes: form.notes.trim() } : {}),
      };
      await onSave(payload);
      setForm({
        metal_type: lockedMetal ?? form.metal_type,
        purchase_date: todayISO(),
        weight_grams: "",
        price_per_gram: "",
        purity: DEFAULT_PURITY[lockedMetal ?? form.metal_type],
        owner: "you",
        notes: "",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save purchase");
    } finally {
      setSaving(false);
    }
  }

  const purities = PURITY_OPTIONS[form.metal_type];

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-[#132E3D] rounded-xl p-4 mb-4 border border-[#1A3A5C]/30"
    >
      <h3 className="text-sm font-medium text-[#E8ECF1]/80 mb-3">Add Purchase</h3>
      {error && (
        <div className="mb-3 px-4 py-2 bg-[#E5A100]/10 border border-[#E5A100]/30 rounded-lg text-[#E5A100] text-sm">
          {error}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-8 gap-3 items-end">
        {/* Metal type - first field */}
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Metal</label>
          <select
            value={form.metal_type}
            onChange={(e) => handleMetalChange(e.target.value as MetalType)}
            disabled={!!lockedMetal}
            className={inputCls}
          >
            {(Object.keys(METAL_LABELS) as MetalType[]).map((m) => (
              <option key={m} value={m}>
                {METAL_LABELS[m]}
              </option>
            ))}
          </select>
        </div>
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
            onChange={(e) => setForm({ ...form, purity: e.target.value })}
            className={inputCls}
          >
            {purities.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Owner</label>
          <select
            value={form.owner}
            onChange={(e) => setForm({ ...form, owner: e.target.value as MetalOwner })}
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
