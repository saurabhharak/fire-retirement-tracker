-- Migration 020: Add used_at to kite_oauth_nonces for atomic one-time claims
-- Pairs with the exchange_token rewrite: the nonce is now consumed via a
-- conditional UPDATE (SET used_at WHERE used_at IS NULL AND not expired)
-- instead of select-then-delete, closing the concurrent-replay window.
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

ALTER TABLE public.kite_oauth_nonces
    ADD COLUMN IF NOT EXISTS used_at timestamptz;

COMMIT;
