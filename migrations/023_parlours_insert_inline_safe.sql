-- Migration 023: Rebuild parlours INSERT policy (inline-safe, role-scoped)
-- Symptom: inserts passed RLS in SQL-editor sessions but failed with 42501
-- under PostgREST, despite pg_policies showing the correct expression.
-- Suspected cause: auth.uid() (STABLE) being inlined into the policy
-- expression — the same inlining class of problem migration 016 fixed for
-- the parlour helper functions.
-- Fix: recreate explicitly TO authenticated and wrap auth.uid() in a
-- scalar subquery so the planner cannot inline it.
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

DROP POLICY IF EXISTS "insert_own" ON public.parlours;

CREATE POLICY "insert_own"
    ON public.parlours
    FOR INSERT
    TO authenticated
    WITH CHECK ((select auth.uid()) = owner_id);

COMMIT;
