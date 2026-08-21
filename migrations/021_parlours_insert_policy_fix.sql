-- Migration 021: Fix parlours INSERT policy (creation was impossible)
-- The old policy checked parlour_member_role(id) = 'owner', but the owner
-- membership row is added by the AFTER INSERT trigger — so on a brand-new
-- parlour the function returns NULL and WITH CHECK always failed (42501).
-- New rule: you may create a parlour that you own.
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

DROP POLICY IF EXISTS "insert_own" ON public.parlours;

CREATE POLICY "insert_own" ON public.parlours
    FOR INSERT WITH CHECK (auth.uid() = owner_id);

COMMIT;
