-- Migration 025: Fix parlour creation failing under PostgREST (42501)
-- Root cause: supabase-py inserts send `Prefer: return=representation`, so
-- PostgREST runs INSERT ... RETURNING. Postgres applies the table's SELECT
-- policy to RETURNING rows, and parlours.select_own is
-- parlour_member_of(id) — the owner membership row is written by the AFTER
-- INSERT trigger and is not visible yet when the RETURNING rows are checked.
-- Every API/UI creation failed with 42501 while raw SQL-editor inserts
-- passed (postgres bypasses RLS there).
-- Fix: owners can always select parlours they own. auth.uid() stays wrapped
-- in a scalar subquery (the migration 016/023 inlining lesson).
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

DROP POLICY IF EXISTS "select_own" ON public.parlours;

CREATE POLICY "select_own"
    ON public.parlours
    FOR SELECT
    TO authenticated
    USING (
        public.parlour_member_of(id)
        OR owner_id = (select auth.uid())
    );

COMMIT;
