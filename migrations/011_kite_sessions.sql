-- Migration 011: Kite Connect MF portfolio integration
-- Tables for OAuth sessions, portfolio snapshots, and OAuth nonces
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

-- ============================================================
-- 1. kite_sessions (one per user, stores daily access token)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.kite_sessions (
    user_id      uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    access_token text        NOT NULL CHECK (char_length(access_token) > 0),
    connected_at timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_kite_sessions_updated_at
    BEFORE UPDATE ON public.kite_sessions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.kite_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.kite_sessions
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "insert_own" ON public.kite_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own" ON public.kite_sessions
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own" ON public.kite_sessions
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- 2. mf_portfolio_snapshots (cached portfolio, one per user)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.mf_portfolio_snapshots (
    user_id       uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    snapshot_data jsonb       NOT NULL,
    synced_at     timestamptz NOT NULL DEFAULT now(),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_mf_portfolio_snapshots_updated_at
    BEFORE UPDATE ON public.mf_portfolio_snapshots
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.mf_portfolio_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.mf_portfolio_snapshots
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "insert_own" ON public.mf_portfolio_snapshots
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own" ON public.mf_portfolio_snapshots
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own" ON public.mf_portfolio_snapshots
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- 3. kite_oauth_nonces (replay protection, service-role only)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.kite_oauth_nonces (
    nonce      uuid        PRIMARY KEY,
    user_id    uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kite_oauth_nonces_expires
    ON public.kite_oauth_nonces(expires_at);

-- No RLS on nonces — only accessed via service-role client

COMMIT;
