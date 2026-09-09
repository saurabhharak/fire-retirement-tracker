-- Migration 022: Fix parlour creation — trigger must bypass RLS
-- Root cause: add_owner_membership() ran as the invoking user (SECURITY
-- INVADER). Its INSERT INTO parlour_members was evaluated against
-- parlour_members' membership-based RLS, which requires the actor to ALREADY
-- be an owner member — impossible for a brand-new parlour (chicken-and-egg).
-- Every API/UI creation failed with 42501.
-- Fix: SECURITY DEFINER so the bootstrap membership row is written with the
-- function owner's privileges. Safe because the insert policy on parlours
-- (migration 021) guarantees NEW.owner_id = auth.uid(), so a user can only
-- ever bootstrap their OWN membership.
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

CREATE OR REPLACE FUNCTION public.add_owner_membership()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.parlour_members (parlour_id, member_id, role)
    VALUES (NEW.id, NEW.owner_id, 'owner')
    ON CONFLICT (parlour_id, member_id) DO NOTHING;
    RETURN NEW;
END;
$$;

COMMIT;
