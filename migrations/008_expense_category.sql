BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'fixed_expenses' AND column_name = 'category'
  ) THEN
    ALTER TABLE public.fixed_expenses
      ADD COLUMN category text NOT NULL DEFAULT 'other';
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_expense_category'
  ) THEN
    ALTER TABLE public.fixed_expenses
      ADD CONSTRAINT chk_expense_category
      CHECK (category IN ('housing', 'food', 'transport', 'utilities', 'entertainment', 'health', 'education', 'insurance', 'subscriptions', 'other'));
  END IF;
END $$;

COMMIT;
