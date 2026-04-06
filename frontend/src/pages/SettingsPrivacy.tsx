import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { PageHeader } from "../components/PageHeader";

export default function SettingsPrivacy() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [confirmText, setConfirmText] = useState("");
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [message, setMessage] = useState("");

  async function handleExport() {
    setExporting(true);
    setMessage("");
    try {
      const data = await api.get<unknown>("/api/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `fire-tracker-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setMessage("Data exported successfully.");
    } catch {
      setMessage("Failed to export data. Please try again.");
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete() {
    if (confirmText !== "DELETE_ALL_DATA") return;
    setDeleting(true);
    setMessage("");
    try {
      await api.delete("/api/account", { confirm: "DELETE_ALL_DATA" });
      await logout();
      navigate("/login");
    } catch {
      setMessage("Failed to delete account. Please try again.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Settings & Privacy"
        subtitle="Manage your data and account preferences"
      />

      {/* Export Section */}
      <div className="bg-[#132E3D] rounded-xl p-5 border border-[#1A3A5C]/30 mb-6">
        <h2 className="text-lg font-semibold text-[#E8ECF1] mb-2">Export My Data</h2>
        <p className="text-sm text-[#E8ECF1]/60 mb-4">
          Download all your FIRE tracker data as a JSON file. This includes your income,
          expenses, fund allocations, SIP logs, and projections.
        </p>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="px-6 py-2 bg-[#00895E] text-white rounded-lg hover:bg-[#00895E]/80 transition-colors disabled:opacity-50 text-sm font-medium"
        >
          {exporting ? "Exporting..." : "Export Data"}
        </button>
      </div>

      {/* Delete Account Section */}
      <div className="bg-[#132E3D] rounded-xl p-5 border border-[#E5A100]/30">
        <h2 className="text-lg font-semibold text-[#E8ECF1] mb-2">Delete Account</h2>
        <p className="text-sm text-[#E5A100] mb-4">
          This action is irreversible. All your data, including income, expenses, fund
          allocations, SIP logs, and projections will be permanently deleted. This cannot be
          undone.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
          <div className="flex-1 w-full sm:w-auto">
            <label className="block text-sm text-[#E8ECF1]/60 mb-1">
              Type <span className="font-mono text-[#E5A100]">DELETE_ALL_DATA</span> to confirm
            </label>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="Type here to confirm"
              autoComplete="off"
              className="w-full px-3 py-2 bg-[#0D1B2A] border border-[#1A3A5C] rounded-lg text-[#E8ECF1] text-sm focus:outline-none focus:border-[#E5A100] font-mono"
            />
          </div>
          <button
            onClick={handleDelete}
            disabled={confirmText !== "DELETE_ALL_DATA" || deleting}
            className="px-6 py-2 bg-[#E5A100] text-white rounded-lg hover:bg-[#E5A100]/80 transition-colors disabled:opacity-30 text-sm font-medium whitespace-nowrap"
          >
            {deleting ? "Deleting..." : "Delete All Data"}
          </button>
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div className="mt-4 p-3 rounded-lg bg-[#132E3D] border border-[#1A3A5C]/30">
          <p className="text-sm text-[#E8ECF1]">{message}</p>
        </div>
      )}
    </div>
  );
}
