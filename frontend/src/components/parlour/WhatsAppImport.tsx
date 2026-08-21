import { useState } from "react";
import { UploadCloud } from "lucide-react";

interface WhatsAppImportProps {
  onImport: (text: string) => Promise<unknown>;
}

export function WhatsAppImport({ onImport }: WhatsAppImportProps) {
  const [chatText, setChatText] = useState("");
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<{ count?: number; skipped?: number } | null>(null);
  const [error, setError] = useState("");

  const handleImport = async () => {
    if (!chatText.trim()) {
      setError("Paste the WhatsApp chat export first");
      return;
    }
    setError("");
    setImporting(true);
    setResult(null);
    try {
      const res = (await onImport(chatText)) as { count?: number; skipped?: number };
      setResult({ count: res?.count ?? 0, skipped: res?.skipped ?? 0 });
      setChatText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
      <h3 className="text-sm font-semibold text-[#E8ECF1] mb-3">
        Import from WhatsApp Group
      </h3>
      <p className="text-xs text-[#E8ECF1]/50 mb-3">
        Paste the exported chat (WhatsApp &gt; Chat &gt; Export) — the parser finds
        &quot;Cash X Online Y&quot; messages and their sale dates automatically.
      </p>
      <textarea
        value={chatText}
        onChange={(e) => setChatText(e.target.value)}
        rows={6}
        placeholder={"16/08/26, 1:10 pm - Swapnil: 15 August \nCash 2750 \nOnline 5769\n..."}
        className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-2 text-sm text-[#E8ECF1] font-mono"
      />
      <div className="flex items-center gap-3 mt-3">
        <button
          onClick={handleImport}
          disabled={importing}
          className="flex items-center gap-1 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 transition-colors"
        >
          <UploadCloud size={16} />
          {importing ? "Importing..." : "Import Sales"}
        </button>
      </div>
      {result && (
        <p className="text-sm mt-3 text-[#E8ECF1]/80">
          Imported <span className="text-[#00895E] font-semibold">{result.count}</span>{" "}
          sales day(s)
          {result.skipped ? (
            <>
              {" "}
              (<span className="text-[#E5A100]">{result.skipped} skipped</span>)
            </>
          ) : null}
        </p>
      )}
      {error && <p className="text-sm text-[#E5A100] mt-3">{error}</p>}
    </div>
  );
}
