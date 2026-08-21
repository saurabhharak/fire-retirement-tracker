-- Migration 014: Other business expenses for the Amul parlour module
-- Non-purchase operating costs (rent, electricity, wages, etc.) so the
-- P&L reflects true expenses, not just Amul purchases.
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

-- ============================================================
-- amul_other_expenses table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.amul_other_expenses (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    parlour_id    uuid        NOT NULL REFERENCES public.parlours(id) ON DELETE CASCADE,
    expense_date  date        NOT NULL,
    category      text        NOT NULL CHECK (char_length(category) <= 50),
    description   text        NOT NULL DEFAULT '' CHECK (char_length(description) <= 200),
    amount        numeric     NOT NULL CHECK (amount > 0),
    is_active     boolean     NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_amul_other_expenses_parlour_date
    ON public.amul_other_expenses(parlour_id, expense_date);

CREATE TRIGGER trg_amul_other_expenses_updated_at
    BEFORE UPDATE ON public.amul_other_expenses
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS (membership-based, same as amul_daily_sales)
ALTER TABLE public.amul_other_expenses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.amul_other_expenses
    FOR SELECT USING (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );
CREATE POLICY "insert_own" ON public.amul_other_expenses
    FOR INSERT WITH CHECK (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );
CREATE POLICY "update_own" ON public.amul_other_expenses
    FOR UPDATE
    USING (parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid()))
    WITH CHECK (parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid()));
CREATE POLICY "delete_own" ON public.amul_other_expenses
    FOR DELETE USING (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );

COMMIT;
