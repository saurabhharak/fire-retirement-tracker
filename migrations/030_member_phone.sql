-- 030: Phone-based parlour members
--
-- Members can now be added by mobile number. The service pre-creates the auth
-- user with that phone (admin API), so the team member can log in with a
-- mobile OTP once a Phone/SMS provider is enabled in the Supabase dashboard.
-- RLS is unchanged: access still flows through member_id = auth.uid().

BEGIN;

ALTER TABLE public.parlour_members
  ADD COLUMN IF NOT EXISTS phone text;

-- One phone per parlour
CREATE UNIQUE INDEX IF NOT EXISTS uq_parlour_member_phone
    ON public.parlour_members (parlour_id, phone)
    WHERE phone IS NOT NULL;

COMMIT;
