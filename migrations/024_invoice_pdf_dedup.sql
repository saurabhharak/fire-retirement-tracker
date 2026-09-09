-- Migration 024: PDF deduplication for invoice uploads
-- The upload endpoint hashes the PDF (SHA-256) BEFORE running paid OCR and
-- skips extraction entirely when the same file was already processed for the
-- parlour. Each invoice row records the hash of the file it came from, so a
-- multi-invoice PDF stores the same hash on all of its rows (the lookup is
-- "any row with this hash", hence a plain index, not a unique one).
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

ALTER TABLE public.amul_invoices
    ADD COLUMN IF NOT EXISTS source_pdf_hash text;

CREATE INDEX IF NOT EXISTS idx_amul_invoices_pdf_hash
    ON public.amul_invoices (parlour_id, source_pdf_hash);

COMMIT;
