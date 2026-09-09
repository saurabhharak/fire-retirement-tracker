-- 027: Sales data confidence cleanup for 'Vrindavan Treats Real' (614d2f38-1a88-4f7f-8a95-45c3b714e4a1)
--
-- Every remaining row in amul_daily_sales for this parlour is verified against the raw
-- WhatsApp chat (production parser output + labeled posts, incl. the manually-verified
-- pairs from migration 026). Unverifiable or contradicted rows are removed so the team
-- can re-enter them manually from source records.
--
-- Applied to the live DB on 2026-09-09 via service client; kept here for the record.
-- Removed rows are backed up in the session scratchpad (backup_deleted_sales.json).
--
-- Also supersedes 026 for this parlour: 026 was written but never applied, and its
-- INSERT ... SELECT parlour_id FROM another row pattern was ambiguous with two
-- seeded parlour copies. Here the parlour_id is explicit.

BEGIN;

-- 1. Remove unverifiable / contradicted rows (exact old values guarded, idempotent)
DELETE FROM public.amul_daily_sales
WHERE parlour_id = '614d2f38-1a88-4f7f-8a95-45c3b714e4a1'
  AND (
       (sale_date = '2026-05-02' AND cash_amount = 16000 AND online_amount = 20315)
    OR (sale_date = '2026-05-03' AND cash_amount = 18000 AND online_amount = 15420)
    OR (sale_date = '2026-05-04' AND cash_amount = 14400 AND online_amount = 11009)
    OR (sale_date = '2026-05-06' AND cash_amount = 15300 AND online_amount = 18405)
    OR (sale_date = '2026-05-07' AND cash_amount = 15000 AND online_amount = 18587)
    OR (sale_date = '2026-05-08' AND cash_amount = 16200 AND online_amount = 17992)
    OR (sale_date = '2026-05-12' AND cash_amount = 17100 AND online_amount = 19184)
    OR (sale_date = '2026-05-16' AND cash_amount = 15500 AND online_amount = 15025)
  );

-- 2. Replace misattributed values with verified ones (026 fixes, explicit parlour_id)
UPDATE public.amul_daily_sales
SET cash_amount = 6650, online_amount = 9917
WHERE parlour_id = '614d2f38-1a88-4f7f-8a95-45c3b714e4a1'
  AND sale_date = '2026-06-28' AND cash_amount = 9400 AND online_amount = 13825;

UPDATE public.amul_daily_sales
SET cash_amount = 6170, online_amount = 5367
WHERE parlour_id = '614d2f38-1a88-4f7f-8a95-45c3b714e4a1'
  AND sale_date = '2026-08-12' AND cash_amount = 4620 AND online_amount = 5134;

-- 3. Insert verified missing days
INSERT INTO public.amul_daily_sales (parlour_id, sale_date, cash_amount, online_amount, sender_name)
VALUES
  ('614d2f38-1a88-4f7f-8a95-45c3b714e4a1', '2026-06-06', 16500, 19337, 'Swapnil 555 Harak'),
  ('614d2f38-1a88-4f7f-8a95-45c3b714e4a1', '2026-06-26', 9400, 13825, 'Swapnil 555 Harak'),
  ('614d2f38-1a88-4f7f-8a95-45c3b714e4a1', '2026-08-08', 0, 7326, 'Swapnil 555 Harak'),
  ('614d2f38-1a88-4f7f-8a95-45c3b714e4a1', '2026-08-11', 4620, 5134, 'Swapnil 555 Harak'),
  ('614d2f38-1a88-4f7f-8a95-45c3b714e4a1', '2026-08-14', 0, 580, 'Swapnil 555 Harak')
ON CONFLICT (parlour_id, sale_date) DO NOTHING;

COMMIT;
