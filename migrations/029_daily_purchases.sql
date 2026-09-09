-- 029: Daily purchases (manual entry), mirroring amul_daily_sales
--
-- Purchases get the same day-by-day treatment as sales: one row per parlour+date,
-- zero rows act as "not filled yet" placeholders so the team can see gaps.
-- Complements (not replaces) OCR purchase invoices.

BEGIN;

CREATE TABLE IF NOT EXISTS public.amul_daily_purchases (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    parlour_id    uuid        NOT NULL REFERENCES public.parlours(id) ON DELETE CASCADE,
    purchase_date date        NOT NULL,
    amount        numeric(12,2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
    note          text        NOT NULL DEFAULT '',
    entered_by    uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_amul_purchase_per_day UNIQUE (parlour_id, purchase_date)
);

CREATE INDEX IF NOT EXISTS idx_amul_purchases_parlour_date
    ON public.amul_daily_purchases (parlour_id, purchase_date DESC);

-- RLS: membership-based, same shape as amul_daily_sales
ALTER TABLE public.amul_daily_purchases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.amul_daily_purchases
    FOR SELECT USING (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );

CREATE POLICY "insert_own" ON public.amul_daily_purchases
    FOR INSERT WITH CHECK (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );

CREATE POLICY "update_own" ON public.amul_daily_purchases
    FOR UPDATE USING (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    )
    WITH CHECK (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );

CREATE POLICY "delete_own" ON public.amul_daily_purchases
    FOR DELETE USING (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );

-- Zero-fill the same calendar window as sales for the real parlour
INSERT INTO public.amul_daily_purchases (parlour_id, purchase_date, amount, note)
SELECT 'bd274881-4aa7-45af-ba26-4ac434e4f7ba',
       d::date, 0, ''
FROM generate_series('2025-08-15'::date, '2026-09-09'::date, interval '1 day') AS d
WHERE NOT EXISTS (
  SELECT 1 FROM public.amul_daily_purchases s
  WHERE s.parlour_id = 'bd274881-4aa7-45af-ba26-4ac434e4f7ba'
    AND s.purchase_date = d::date
);

COMMIT;
