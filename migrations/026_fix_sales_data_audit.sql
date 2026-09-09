-- Fix sales data discovered by the Aug 2026 audit:
--   1. June 28: wrong values (9400/13825 was June 26 data misattributed)
--   2. Aug 12: wrong values (4620/5134 was Aug 11 data misattributed)
--   3. Missing rows: June 6, June 26, Aug 8, Aug 11, Aug 14

BEGIN;

-- Fix 1: June 28 had June 26's values (parser bug: bare "26" label → fallback to post date 28)
-- Correct June 28: Cash 6650, Online 9917 (raw: "28 june\nCash 6650\nOnline 9917\nHdfc 1007")
UPDATE public.amul_daily_sales
SET cash_amount = 6650, online_amount = 9917
WHERE sale_date = '2026-06-28'
  AND cash_amount = 9400
  AND online_amount = 13825;

-- Fix 2: Aug 12 had Aug 11's values (parser bug: "11August" no-space label → fallback to post date 12)
-- Correct Aug 12: Cash 6170, Online 5367 (raw: "12 August\nCash 6170\nOnline 5367")
UPDATE public.amul_daily_sales
SET cash_amount = 6170, online_amount = 5367
WHERE sale_date = '2026-08-12'
  AND cash_amount = 4620
  AND online_amount = 5134;

-- Add missing rows (use upsert to be idempotent)
-- June 6: Cash 16500, Online 19337 (parser bug: "Cash..16500" double-dot)
INSERT INTO public.amul_daily_sales (parlour_id, sale_date, cash_amount, online_amount, sender_name)
SELECT parlour_id, '2026-06-06', 16500, 19337, 'Swapnil 555 Harak'
FROM public.amul_daily_sales WHERE sale_date = '2026-06-07' LIMIT 1
ON CONFLICT (parlour_id, sale_date) DO UPDATE
SET cash_amount = 16500, online_amount = 19337;

-- June 26: Cash 9400, Online 13825 (was misattributed to June 28; bare "26" label)
INSERT INTO public.amul_daily_sales (parlour_id, sale_date, cash_amount, online_amount, sender_name)
SELECT parlour_id, '2026-06-26', 9400, 13825, 'Swapnil 555 Harak'
FROM public.amul_daily_sales WHERE sale_date = '2026-06-27' LIMIT 1
ON CONFLICT (parlour_id, sale_date) DO UPDATE
SET cash_amount = 9400, online_amount = 13825;

-- Aug 8: Online only, no cash (raw: "8 August\nOnline 7326")
INSERT INTO public.amul_daily_sales (parlour_id, sale_date, cash_amount, online_amount, sender_name)
SELECT parlour_id, '2026-08-08', 0, 7326, 'Swapnil 555 Harak'
FROM public.amul_daily_sales WHERE sale_date = '2026-08-07' LIMIT 1
ON CONFLICT (parlour_id, sale_date) DO UPDATE
SET cash_amount = 0, online_amount = 7326;

-- Aug 11: Cash 4620, Online 5134 (was misattributed to Aug 12; "11August" no-space label)
INSERT INTO public.amul_daily_sales (parlour_id, sale_date, cash_amount, online_amount, sender_name)
SELECT parlour_id, '2026-08-11', 4620, 5134, 'Swapnil 555 Harak'
FROM public.amul_daily_sales WHERE sale_date = '2026-08-10' LIMIT 1
ON CONFLICT (parlour_id, sale_date) DO UPDATE
SET cash_amount = 4620, online_amount = 5134;

-- Aug 14: Online only, no cash (raw: "14 August\nOnline 580")
INSERT INTO public.amul_daily_sales (parlour_id, sale_date, cash_amount, online_amount, sender_name)
SELECT parlour_id, '2026-08-14', 0, 580, 'Swapnil 555 Harak'
FROM public.amul_daily_sales WHERE sale_date = '2026-08-13' LIMIT 1
ON CONFLICT (parlour_id, sale_date) DO UPDATE
SET cash_amount = 0, online_amount = 580;

COMMIT;
