BEGIN;

-- Add payment_method column (idempotent)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'fixed_expenses' AND column_name = 'payment_method'
  ) THEN
    ALTER TABLE public.fixed_expenses
      ADD COLUMN payment_method text NOT NULL DEFAULT 'cash';
  END IF;
END $$;

-- Add CHECK constraint (idempotent)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_payment_method'
  ) THEN
    ALTER TABLE public.fixed_expenses
      ADD CONSTRAINT chk_payment_method
      CHECK (payment_method IN ('upi', 'credit_card', 'cash'));
  END IF;
END $$;

COMMIT;
