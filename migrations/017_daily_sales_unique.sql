-- Migration 017: Make daily sales idempotent on (parlour_id, sale_date)
-- Required before switching amul_sales_svc.save_daily_sale to .upsert(...)
-- so that WhatsApp re-imports update instead of duplicating a day.
-- If the constraint already exists (idempotent re-run), it is a no-op.
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_amul_sale_parlour_date'
          AND conrelid = 'public.amul_daily_sales'::regclass
    ) THEN
        ALTER TABLE public.amul_daily_sales
            ADD CONSTRAINT uq_amul_sale_parlour_date UNIQUE (parlour_id, sale_date);
    END IF;
END;
$$;

COMMIT;