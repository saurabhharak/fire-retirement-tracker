import { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";

interface InvoiceUploadProps {
  onUpload: (input: { file: File; useDocling: boolean }) => Promise<unknown>;
}

export function InvoiceUpload({ onUpload }: InvoiceUploadProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [useDocling, setUseDocling] = useState(false);
  const [result, setResult] = useState<{
    credits?: number;
    status?: string;
    source?: string;
    duplicate?: boolean;
    createdCount?: number;
    skippedDuplicates?: number;
    skippedUndated?: number;
  } | null>(null);
  const [error, setError] = useState("");

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Select a PDF first");
      return;
    }
    setError("");
    setUploading(true);
    setResult(null);
    try {
      const res = (await onUpload({ file, useDocling })) as {
        credits_used?: number;
        status?: string;
        source?: string;
        duplicate?: boolean;
        created_count?: number;
        skipped_duplicates?: number;
        skipped_undated?: number;
      };
      setResult({
        credits: res?.credits_used ?? 0,
        status: res?.status,
        source: res?.source,
        duplicate: res?.duplicate,
        createdCount: res?.created_count,
        skippedDuplicates: res?.skipped_duplicates,
        skippedUndated: res?.skipped_undated,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
      <h3 className="text-sm font-semibold text-[#E8ECF1] mb-3">Upload Purchase PDF</h3>
      <div className="flex flex-wrap items-center gap-3">
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf"
          className="text-sm text-[#E8ECF1]/70 file:mr-3 file:px-3 file:py-1.5 file:rounded file:border-0 file:bg-[#00895E] file:text-white file:text-sm"
        />
        <label className="flex items-center gap-2 text-sm text-[#E8ECF1]/70">
          <input
            type="checkbox"
            checked={useDocling}
            onChange={(e) => setUseDocling(e.target.checked)}
          />
          Use free Docling OCR (no Sarvam credits)
        </label>
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="flex items-center gap-1 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 transition-colors"
        >
          <UploadCloud size={16} />
          {uploading ? "Extracting..." : "Upload & Extract"}
        </button>
      </div>
      {result && result.duplicate && (
        <p className="text-sm mt-3 text-[#E5A100]">
          This PDF was already uploaded — showing the existing invoice(s). No OCR
          rerun, 0 credits used.
        </p>
      )}
      {result && !result.duplicate && (
        <p className="text-sm mt-3 text-[#E8ECF1]/80">
          Extraction {result.status ?? "done"} via {result.source ?? "OCR"} —{" "}
          <span className="text-[#D4A843]">{result.credits ?? 0} credits used</span>
          {result.createdCount !== undefined && (
            <> · {result.createdCount} invoice(s) created</>
          )}
          {result.skippedDuplicates ? (
            <>
              {" "}
              · <span className="text-[#E5A100]">{result.skippedDuplicates} duplicate(s) skipped</span>
            </>
          ) : null}
          {result.skippedUndated ? (
            <>
              {" "}
              · <span className="text-[#E5A100]">{result.skippedUndated} page(s) skipped — no readable bill date</span>
            </>
          ) : null}
        </p>
      )}
      {error && <p className="text-sm text-[#E5A100] mt-3">{error}</p>}
    </div>
  );
}
