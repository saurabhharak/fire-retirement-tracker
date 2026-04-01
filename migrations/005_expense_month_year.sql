BEGIN;

ALTER TABLE public.fixed_expenses
  ADD COLUMN IF NOT EXISTS expense_month int CHECK (expense_month >= 1 AND expense_month <= 12),
  ADD COLUMN IF NOT EXISTS expense_year  int CHECK (expense_year >= 2020 AND expense_year <= 2100);

CREATE INDEX IF NOT EXISTS idx_fixed_expenses_month_year
  ON public.fixed_expenses(user_id, expense_year, expense_month);

UPDATE public.fixed_expenses
SET expense_month = EXTRACT(MONTH FROM created_at)::int,
    expense_year  = EXTRACT(YEAR FROM created_at)::int
WHERE frequency = 'one-time'
  AND expense_month IS NULL;

-- Verify owner column exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'fixed_expenses' AND column_name = 'owner'
  ) THEN
    ALTER TABLE public.fixed_expenses
      ADD COLUMN owner text NOT NULL DEFAULT 'household'
      CHECK (owner IN ('you', 'wife', 'household'));
  END IF;
END $$;

-- One-time expenses must have month/year
ALTER TABLE public.fixed_expenses
  ADD CONSTRAINT IF NOT EXISTS chk_one_time_has_month_year
  CHECK (frequency != 'one-time' OR (expense_month IS NOT NULL AND expense_year IS NOT NULL));

COMMIT;
