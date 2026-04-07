import { useState } from "react";
import { UserPlus } from "lucide-react";
import type { LedgerContactInput } from "../../hooks/useLedgerContacts";

interface Props {
  onSave: (data: LedgerContactInput) => Promise<unknown>;
}

export function AddContactForm({ onSave }: Props) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Name is required");
      return;
    }

    setSaving(true);
    try {
      await onSave({
        name: trimmedName,
        phone: phone.trim() || null,
      });
      setName("");
      setPhone("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add contact");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mb-4">
      <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
        <div className="flex flex-col sm:flex-row gap-3 items-end">
          <div className="flex-1">
            <label
              htmlFor="contact-name"
              className="block text-xs text-[#E8ECF1]/60 mb-1"
            >
              Name <span className="text-[#E5A100]">*</span>
            </label>
            <input
              id="contact-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Person's name"
              maxLength={100}
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1] placeholder-[#E8ECF1]/30 focus:outline-none focus:border-[#00895E]/60"
            />
          </div>
          <div className="flex-1 sm:max-w-[180px]">
            <label
              htmlFor="contact-phone"
              className="block text-xs text-[#E8ECF1]/60 mb-1"
            >
              Phone (optional)
            </label>
            <input
              id="contact-phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="10-digit number"
              maxLength={15}
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1] placeholder-[#E8ECF1]/30 focus:outline-none focus:border-[#00895E]/60"
            />
          </div>
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-1.5 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded px-4 py-1.5 text-sm font-medium disabled:opacity-50 transition-colors whitespace-nowrap"
          >
            <UserPlus size={15} />
            {saving ? "Adding..." : "Add Person"}
          </button>
        </div>
        {error && <p className="text-[#E5A100] text-sm mt-2">{error}</p>}
      </div>
    </form>
  );
}
