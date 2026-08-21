-- Migration 018: Enable RLS on precious_metal_rate_cache
-- The table was created in 008 without RLS, leaving it readable AND writable
-- by anyone holding the anon key via PostgREST (cache poisoning / wiping).
-- Rates are public market data, so anon keeps read access via a SELECT-all
-- policy; writes require the service-role client (bypasses RLS).
-- Backend pairing: _save_db_cached_rates / _cleanup_old_cache_rows must use
-- get_service_client() (see app/services/precious_metals_svc.py).
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

ALTER TABLE public.precious_metal_rate_cache ENABLE ROW LEVEL SECURITY;

-- Public market data: anyone (incl. anon) may read cached rates.
-- No INSERT/UPDATE/DELETE policies: anon/authenticated writes are denied;
-- only service_role bypasses RLS.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'precious_metal_rate_cache'
          AND policyname = 'rate_cache_select_all'
    ) THEN
        CREATE POLICY "rate_cache_select_all"
            ON public.precious_metal_rate_cache
            FOR SELECT
            USING (true);
    END IF;
END;
$$;

COMMIT;
