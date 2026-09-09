-- 028: Allow zero-placeholder sales days (team fills manually) + backfill missing calendar days
--
-- The team marks not-yet-verified days as cash 0 / online 0 so gaps are visible in the UI.
-- The old CHECK (cash_amount + online_amount > 0) blocked that; replace it with a
-- non-negative check (negatives were never allowed — Pydantic models also enforce ge=0).
--
-- Then fill every missing calendar day from 2025-08-15 through 2026-09-09 (today) for
-- 'Vrindavan Treats Real' with a 0/0 placeholder row. Idempotent: existing rows untouched.

BEGIN;

-- 1. Relax the positive-total check (drop + re-add, idempotent by name)
ALTER TABLE public.amul_daily_sales
  DROP CONSTRAINT IF EXISTS chk_amul_sale_positive_total;

ALTER TABLE public.amul_daily_sales
  ADD CONSTRAINT chk_amul_sale_non_negative
  CHECK (cash_amount >= 0 AND online_amount >= 0)
  NOT VALID;

-- 2. Zero-fill every missing day in the window for the real parlour
INSERT INTO public.amul_daily_sales (parlour_id, sale_date, cash_amount, online_amount, sender_name)
SELECT '614d2f38-1a88-4f7f-8a95-45c3b714e4a1',
       d::date, 0, 0, ''
FROM generate_series('2025-08-15'::date, '2026-09-09'::date, interval '1 day') AS d
WHERE NOT EXISTS (
  SELECT 1 FROM public.amul_daily_sales s
  WHERE s.parlour_id = '614d2f38-1a88-4f7f-8a95-45c3b714e4a1'
    AND s.sale_date = d::date
);

COMMIT;
