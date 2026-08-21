-- Patch: recreate RLS helper functions with SECURITY DEFINER
-- Fixes "max_stack_depth exceeded" from function inlining into RLS policies.
-- Safe to re-run (CREATE OR REPLACE).
BEGIN;

CREATE OR REPLACE FUNCTION public.parlour_member_of(p uuid) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN EXISTS(
    SELECT 1 FROM public.parlour_members
    WHERE parlour_id = p AND member_id = auth.uid()
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.parlour_member_role(p uuid) RETURNS text
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  r text;
BEGIN
  SELECT role INTO r FROM public.parlour_members
  WHERE parlour_id = p AND member_id = auth.uid();
  RETURN r;
END;
$$;

COMMIT;
