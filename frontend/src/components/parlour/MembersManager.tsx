import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import type { ParlourMember } from "../../hooks/useParlourMembers";

interface MembersManagerProps {
  members: ParlourMember[];
  currentUserId?: string | null;
  isLoading?: boolean;
  onAdd: (input: { email: string; role: "owner" | "data_entry" }) => Promise<unknown>;
  onRemove: (memberId: string) => Promise<unknown>;
}

export function MembersManager({
  members,
  currentUserId,
  isLoading,
  onAdd,
  onRemove,
}: MembersManagerProps) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"data_entry" | "owner">("data_entry");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const handleAdd = async () => {
    if (!email.trim()) {
      setError("Enter an email address");
      return;
    }
    setError("");
    setBusy(true);
    try {
      await onAdd({ email: email.trim(), role });
      setEmail("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add member");
    } finally {
      setBusy(false);
    }
  };

  if (isLoading) return null;

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
      <h3 className="text-sm font-semibold text-[#E8ECF1] mb-3">Members</h3>

      {/* Add member */}
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="swapnil@example.com"
            className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Role</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as "owner" | "data_entry")}
            className="bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
          >
            <option value="data_entry">Data Entry</option>
            <option value="owner">Owner</option>
          </select>
        </div>
        <button
          onClick={handleAdd}
          disabled={busy}
          className="flex items-center gap-1 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 transition-colors"
        >
          <Plus size={16} />
          {busy ? "Adding..." : "Add"}
        </button>
      </div>
      {error && <p className="text-sm text-[#E5A100] mb-2">{error}</p>}

      {/* Members table */}
      {members.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-[#E8ECF1]">
            <thead>
              <tr className="text-left text-[#E8ECF1]/50 border-b border-[#1A3A5C]/30">
                <th className="py-2 pr-3 font-medium">Member ID</th>
                <th className="py-2 pr-3 font-medium">Role</th>
                <th className="py-2 pr-3 font-medium">You?</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id} className="border-b border-[#1A3A5C]/20">
                  <td className="py-2 pr-3 font-mono text-xs">{m.member_id}</td>
                  <td className="py-2 pr-3 capitalize">{m.role}</td>
                  <td className="py-2 pr-3">
                    {m.member_id === currentUserId ? "Yes" : ""}
                  </td>
                  <td className="py-2 text-right">
                    {m.member_id !== currentUserId ? (
                      <button
                        onClick={() => onRemove(m.id)}
                        className="text-[#E5A100]/70 hover:text-[#E5A100] transition-colors"
                        aria-label={`Remove member ${m.member_id}`}
                      >
                        <Trash2 size={16} />
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}