-- Migration 019: Lock down kite_oauth_nonces
-- The table was created in 011 without RLS ("service-role only" comment),
-- but disabling RLS does not restrict PostgREST access: anyone with the
-- anon key could read pending nonces, consume them (DoS), or insert rows
-- that poison the stateless fallback in exchange_token().
-- Enabling RLS with NO policies denies all anon/authenticated access via
-- PostgREST while service_role continues to bypass RLS unchanged — no
-- backend changes required (all access already uses get_service_client()).
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

ALTER TABLE public.kite_oauth_nonces ENABLE ROW LEVEL SECURITY;

-- Defense-in-depth at the grants layer (redundant once RLS is enabled,
-- but makes the service-role-only intent explicit).
REVOKE ALL ON public.kite_oauth_nonces FROM anon, authenticated;

COMMIT;
