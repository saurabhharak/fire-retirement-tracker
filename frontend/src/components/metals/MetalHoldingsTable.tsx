import { useState } from "react";
import type { PreciousMetalEntry, PreciousMetalUpdate, MetalType, MetalOwner } from "../../hooks/usePreciousMetals";
import type { MetalRates } from "../../hooks/useMetalRates";
import { formatRupees } from "../../lib/formatIndian";
import { inputCls } from "../../lib/styles";

interface MetalHoldingsTableProps {
  entries: PreciousMetalEntry[];
  rates: MetalRates | undefined;
  onDeactivate: (id: string) => void;
  onEdit: (id: string, data: PreciousMetalUpdate) => Promise<unknown>;
}

interface EditForm {
  metal_type: MetalType;
  purchase_date: string;
  weight_grams: number | "";
  price_per_gram: number | "";
  purity: string;
  owner: MetalOwner;
}

const METAL_COLORS: Record<string, string> = {
  gold: "#D4A843",
  silver: "#C0C0C0",
  platinum: "#A0B2C6",
};

const METAL_LABELS: Record<string, string> = {
  gold: "Gold",
  silver: "Silver",
  platinum: "Platinum",
};

const PURITY_OPTIONS: Record<MetalType, string[]> = {
  gold: ["24K", "22K", "18K"],
  silver: ["999", "925", "900"],
  platinum: ["999", "950", "900"],
};

function metalBadge(metal: string) {
  const color = METAL_COLORS[metal] ?? "#6B7280";
  const label = METAL_LABELS[metal] ?? metal;
  return (
    <span
      className="text-xs font-medium px-2 py-0.5 rounded-full"
      style={{
        backgroundColor: `${color}20`,
        color,
      }}
    >
      {label}
    </span>
  );
}

function ownerBadge(owner: MetalOwner) {
  const cls =
    owner === "you"
      ? "bg-[#D4A843]/20 text-[#D4A843]"
      : owner === "wife"
        ? "bg-[#E07A5F]/20 text-[#E07A5F]"
        : "bg-[#6B7280]/20 text-[#6B7280]";
  const label =
    owner === "you" ? "You" : owner === "wife" ? "Wife" : "Household";
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>
      {label}
    </span>
  );
}

function purityBadge(purity: string, metal: string) {
  const color = METAL_COLORS[metal] ?? "#6B7280";
  return (
    <span
      className="text-xs font-medium px-2 py-0.5 rounded-full"
      style={{
        backgroundColor: `${color}15`,
        color: `${color}CC`,
      }}
    >
      {purity}
    </span>
  );
}

function getRateForEntry(rates: MetalRates | undefined, metal: string, purity: string): number {
  if (!rates) return 0;
  const metalRates = rates[metal];
  if (!metalRates) return 0;
  return metalRates[purity] ?? 0;
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return iso;
  }
}

export function MetalHoldingsTable({ entries, rates, onDeactivate, onEdit }: MetalHoldingsTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm | null>(null);
  const [saving, setSaving] = useState(false);

  function startEdit(entry: PreciousMetalEntry) {
    if (!entry.id) return;
    setEditingId(entry.id);
    setEditForm({
      metal_type: entry.metal_type,
      purchase_date: entry.purchase_date,
      weight_grams: entry.weight_grams,
      price_per_gram: entry.price_per_gram,
      purity: entry.purity,
      owner: entry.owner,
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setEditForm(null);
  }

  function handleMetalChange(metal: MetalType) {
    if (!editForm) return;
    const purities = PURITY_OPTIONS[metal];
    setEditForm({
      ...editForm,
      metal_type: metal,
      purity: purities[0],
    });
  }

  const [editError, setEditError] = useState("");

  async function saveEdit() {
    if (!editingId || !editForm) return;
    setEditError("");
    const weight = Number(editForm.weight_grams);
    const price = Number(editForm.price_per_gram);
    if (!weight || weight <= 0 || !price || price <= 0) {
      setEditError("Weight and price must be greater than 0");
      return;
    }
    setSaving(true);
    try {
      await onEdit(editingId, {
        metal_type: editForm.metal_type,
        purchase_date: editForm.purchase_date,
        weight_grams: weight,
        price_per_gram: price,
        purity: editForm.purity,
        owner: editForm.owner,
      });
      setEditingId(null);
      setEditForm(null);
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Failed to save changes");
    } finally {
      setSaving(false);
    }
  }

  if (entries.length === 0) {
    return (
      <div className="text-center py-8 text-[#E8ECF1]/40 text-sm">
        No precious metal purchases yet.
      </div>
    );
  }

  const hasRates = rates && Object.keys(rates).length > 0;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[#E8ECF1]/40 text-xs uppercase tracking-wider border-b border-[#1A3A5C]/30">
            <th className="text-left py-3 px-2">Date</th>
            <th className="text-left py-3 px-2">Metal</th>
            <th className="text-left py-3 px-2">Purity</th>
            <th className="text-left py-3 px-2">Owner</th>
            <th className="text-right py-3 px-2">Weight (g)</th>
            <th className="text-right py-3 px-2">Price Paid/g</th>
            <th className="text-right py-3 px-2">Total Cost</th>
            <th className="text-right py-3 px-2">Current Value</th>
            <th className="text-right py-3 px-2">P&amp;L</th>
            <th className="text-right py-3 px-2">P&amp;L%</th>
            <th className="text-right py-3 px-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => {
            const isEditing = editingId === entry.id;
            const currentRate = getRateForEntry(rates, entry.metal_type, entry.purity);
            const totalCost = entry.total_cost ?? entry.weight_grams * entry.price_per_gram;
            const currentValue = entry.weight_grams * currentRate;
            const pnl = hasRates ? currentValue - totalCost : 0;
            const pnlPct = totalCost > 0 && hasRates ? (pnl / totalCost) * 100 : 0;
            const pnlColor = pnl >= 0 ? "text-[#00895E]" : "text-[#E5A100]";

            if (isEditing && editForm) {
              const editPurities = PURITY_OPTIONS[editForm.metal_type];
              return (
                <tr
                  key={entry.id ?? entry.purchase_date}
                  className="border-b border-[#1A3A5C]/20 bg-[#1A3A5C]/10"
                >
                  <td className="py-2 px-2">
                    <input
                      type="date"
                      value={editForm.purchase_date}
                      onChange={(e) => setEditForm({ ...editForm, purchase_date: e.target.value })}
                      className={`${inputCls} w-32`}
                    />
                  </td>
                  <td className="py-2 px-2">
                    <select
                      value={editForm.metal_type}
                      onChange={(e) => handleMetalChange(e.target.value as MetalType)}
                      className={`${inputCls} w-24`}
                    >
                      <option value="gold">Gold</option>
                      <option value="silver">Silver</option>
                      <option value="platinum">Platinum</option>
                    </select>
                  </td>
                  <td className="py-2 px-2">
                    <select
                      value={editForm.purity}
                      onChange={(e) => setEditForm({ ...editForm, purity: e.target.value })}
                      className={`${inputCls} w-20`}
                    >
                      {editPurities.map((p) => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 px-2">
                    <select
                      value={editForm.owner}
                      onChange={(e) => setEditForm({ ...editForm, owner: e.target.value as MetalOwner })}
                      className={`${inputCls} w-24`}
                    >
                      <option value="you">You</option>
                      <option value="wife">Wife</option>
                      <option value="household">Household</option>
                    </select>
                  </td>
                  <td className="py-2 px-2">
                    <input
                      type="number"
                      value={editForm.weight_grams}
                      onChange={(e) =>
                        setEditForm({ ...editForm, weight_grams: e.target.value === "" ? "" : Number(e.target.value) })
                      }
                      min={0.001}
                      step={0.001}
                      className={`${inputCls} w-20 text-right`}
                    />
                  </td>
                  <td className="py-2 px-2">
                    <input
                      type="number"
                      value={editForm.price_per_gram}
                      onChange={(e) =>
                        setEditForm({ ...editForm, price_per_gram: e.target.value === "" ? "" : Number(e.target.value) })
                      }
                      min={1}
                      className={`${inputCls} w-24 text-right`}
                    />
                  </td>
                  <td className="py-2 px-2 text-right text-[#E8ECF1]/40">--</td>
                  <td className="py-2 px-2 text-right text-[#E8ECF1]/40">--</td>
                  <td className="py-2 px-2 text-right text-[#E8ECF1]/40">--</td>
                  <td className="py-2 px-2 text-right text-[#E8ECF1]/40">--</td>
                  <td className="py-2 px-2 text-right space-x-2">
                    <button
                      onClick={saveEdit}
                      disabled={saving}
                      className="text-[#00895E] hover:text-[#00895E]/80 text-xs font-medium disabled:opacity-50"
                    >
                      Save
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="text-[#E8ECF1]/40 hover:text-[#E8ECF1]/60 text-xs font-medium"
                    >
                      Cancel
                    </button>
                    {editError && (
                      <p className="text-[10px] text-[#E5A100] mt-1">{editError}</p>
                    )}
                  </td>
                </tr>
              );
            }

            return (
              <tr
                key={entry.id ?? entry.purchase_date}
                className="border-b border-[#1A3A5C]/20 hover:bg-[#1A3A5C]/10 transition-colors"
              >
                <td className="py-3 px-2 text-[#E8ECF1]">{formatDate(entry.purchase_date)}</td>
                <td className="py-3 px-2">{metalBadge(entry.metal_type)}</td>
                <td className="py-3 px-2">{purityBadge(entry.purity, entry.metal_type)}</td>
                <td className="py-3 px-2">{ownerBadge(entry.owner)}</td>
                <td
                  className="py-3 px-2 text-right text-[#E8ECF1]"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {entry.weight_grams.toFixed(3)}
                </td>
                <td
                  className="py-3 px-2 text-right text-[#E8ECF1]/70"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {formatRupees(entry.price_per_gram)}
                </td>
                <td
                  className="py-3 px-2 text-right text-[#E8ECF1]"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {formatRupees(totalCost)}
                </td>
                <td
                  className="py-3 px-2 text-right text-[#E8ECF1]"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {hasRates ? formatRupees(Math.round(currentValue)) : "--"}
                </td>
                <td
                  className={`py-3 px-2 text-right font-medium ${pnlColor}`}
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {hasRates ? `${pnl >= 0 ? "+" : ""}${formatRupees(Math.round(pnl))}` : "--"}
                </td>
                <td
                  className={`py-3 px-2 text-right font-medium ${pnlColor}`}
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {hasRates ? `${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%` : "--"}
                </td>
                <td className="py-3 px-2 text-right space-x-2">
                  <button
                    onClick={() => startEdit(entry)}
                    disabled={!entry.id}
                    className="text-[#3B82F6] hover:text-[#3B82F6]/80 text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => entry.id && onDeactivate(entry.id)}
                    disabled={!entry.id}
                    className="text-[#E5A100] hover:text-[#E5A100]/80 text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Deactivate
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
