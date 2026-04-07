-- =============================================================================
-- FIRE Retirement Tracker — Supabase PostgreSQL DDL
-- =============================================================================
-- Run this in the Supabase SQL Editor (Dashboard > SQL Editor > New Query).
-- Requires: Supabase project with Auth enabled.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 0. Helper: updated_at trigger function
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- 1. fire_inputs (1:1 per user — stores ALL settings)
-- ---------------------------------------------------------------------------
CREATE TABLE public.fire_inputs (
    user_id           uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    dob               date        NOT NULL,
    retirement_age    int         NOT NULL CHECK (retirement_age > 18 AND retirement_age < 100),
    life_expectancy   int         NOT NULL CHECK (life_expectancy > retirement_age),
    your_sip          numeric     NOT NULL CHECK (your_sip >= 0),
    wife_sip          numeric     NOT NULL CHECK (wife_sip >= 0),
    step_up_pct       numeric     NOT NULL CHECK (step_up_pct >= 0 AND step_up_pct <= 0.5),
    existing_corpus   numeric     NOT NULL CHECK (existing_corpus >= 0),
    equity_return     numeric     NOT NULL CHECK (equity_return > 0 AND equity_return <= 0.3),
    debt_return       numeric     NOT NULL CHECK (debt_return > 0 AND debt_return <= 0.3),
    gold_return       numeric     NOT NULL CHECK (gold_return >= 0 AND gold_return <= 0.3),
    cash_return       numeric     NOT NULL CHECK (cash_return >= 0 AND cash_return <= 0.3),
    inflation         numeric     NOT NULL CHECK (inflation > 0 AND inflation <= 0.2),
    swr               numeric     NOT NULL CHECK (swr > 0 AND swr <= 0.10),
    equity_pct        numeric     NOT NULL CHECK (equity_pct >= 0 AND equity_pct <= 1),
    gold_pct          numeric     NOT NULL CHECK (gold_pct >= 0 AND gold_pct <= 1),
    cash_pct          numeric     NOT NULL CHECK (cash_pct >= 0 AND cash_pct <= 1),
    monthly_expense   numeric     NOT NULL CHECK (monthly_expense >= 0),
    updated_at        timestamptz NOT NULL DEFAULT now(),

    -- Table-level: allocation percentages must not exceed 100%
    CONSTRAINT chk_allocation_sum CHECK (equity_pct + gold_pct + cash_pct <= 1.0)
);

CREATE TRIGGER trg_fire_inputs_updated_at
    BEFORE UPDATE ON public.fire_inputs
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------------------------------------------------------------------------
-- 2. income_entries
-- ---------------------------------------------------------------------------
CREATE TABLE public.income_entries (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    month         int         NOT NULL CHECK (month >= 1 AND month <= 12),
    year          int         NOT NULL CHECK (year >= 2020 AND year <= 2100),
    your_income   numeric     NOT NULL CHECK (your_income >= 0),
    wife_income   numeric     NOT NULL CHECK (wife_income >= 0),
    notes         text        CHECK (char_length(notes) <= 500),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_income_user_month_year UNIQUE (user_id, month, year)
);

CREATE INDEX idx_income_entries_user_id ON public.income_entries(user_id);

CREATE TRIGGER trg_income_entries_updated_at
    BEFORE UPDATE ON public.income_entries
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------------------------------------------------------------------------
-- 3. fixed_expenses
-- ---------------------------------------------------------------------------
CREATE TABLE public.fixed_expenses (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name          text        NOT NULL CHECK (char_length(name) <= 100),
    amount        numeric     NOT NULL CHECK (amount > 0),
    frequency     text        NOT NULL CHECK (frequency IN ('monthly', 'quarterly', 'yearly', 'one-time')),
    is_active     boolean     NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_fixed_expenses_user_active ON public.fixed_expenses(user_id, is_active);

CREATE TRIGGER trg_fixed_expenses_updated_at
    BEFORE UPDATE ON public.fixed_expenses
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------------------------------------------------------------------------
-- 4. sip_log
-- ---------------------------------------------------------------------------
CREATE TABLE public.sip_log (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    month           int         NOT NULL CHECK (month >= 1 AND month <= 12),
    year            int         NOT NULL CHECK (year >= 2020 AND year <= 2100),
    planned_sip     numeric,
    actual_invested numeric     NOT NULL CHECK (actual_invested >= 0),
    notes           text        CHECK (char_length(notes) <= 500),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_sip_log_user_month_year UNIQUE (user_id, month, year)
);

CREATE INDEX idx_sip_log_user_id ON public.sip_log(user_id);

CREATE TRIGGER trg_sip_log_updated_at
    BEFORE UPDATE ON public.sip_log
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------------------------------------------------------------------------
-- 5. sip_log_funds (normalized fund breakdown per SIP log entry)
-- ---------------------------------------------------------------------------
CREATE TABLE public.sip_log_funds (
    id          uuid    PRIMARY KEY DEFAULT gen_random_uuid(),
    sip_log_id  uuid    NOT NULL REFERENCES public.sip_log(id) ON DELETE CASCADE,
    fund_name   text    NOT NULL,
    amount      numeric CHECK (amount >= 0)
);

CREATE INDEX idx_sip_log_funds_sip_log_id ON public.sip_log_funds(sip_log_id);

-- ---------------------------------------------------------------------------
-- 6. audit_log
-- ---------------------------------------------------------------------------
CREATE TABLE public.audit_log (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    action      text        NOT NULL,
    details     jsonb,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_log_user_id ON public.audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON public.audit_log(created_at);

-- ---------------------------------------------------------------------------
-- 7. projects
-- ---------------------------------------------------------------------------
CREATE TABLE public.projects (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name        text        NOT NULL CHECK (char_length(name) <= 100),
    status      text        NOT NULL CHECK (status IN ('active', 'completed')) DEFAULT 'active',
    budget      numeric     CHECK (budget IS NULL OR budget > 0),
    start_date  date        NOT NULL,
    end_date    date        CHECK (end_date IS NULL OR end_date >= start_date),
    is_active   boolean     NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_projects_user_status ON public.projects(user_id, status);

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON public.projects
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------------------------------------------------------------------------
-- 8. project_expenses
-- ---------------------------------------------------------------------------
CREATE TABLE public.project_expenses (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   uuid        NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    date         date        NOT NULL,
    category     text        NOT NULL CHECK (char_length(category) <= 50),
    description  text        NOT NULL CHECK (char_length(description) <= 200),
    total_amount numeric     CHECK (total_amount IS NULL OR total_amount >= 0),
    paid_amount  numeric     NOT NULL CHECK (paid_amount >= 0),
    paid_by      text        NOT NULL CHECK (char_length(paid_by) <= 100),
    is_active    boolean     NOT NULL DEFAULT true,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_project_expenses_project_id ON public.project_expenses(project_id);

CREATE TRIGGER trg_project_expenses_updated_at
    BEFORE UPDATE ON public.project_expenses
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------------------------------------------------------------------------
-- 9. kite_sessions (one per user, stores daily Kite Connect access token)
-- ---------------------------------------------------------------------------
CREATE TABLE public.kite_sessions (
    user_id      uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    access_token text        NOT NULL CHECK (char_length(access_token) > 0),
    connected_at timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 10. mf_portfolio_snapshots (cached MF portfolio, one per user)
-- ---------------------------------------------------------------------------
CREATE TABLE public.mf_portfolio_snapshots (
    user_id       uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    snapshot_data jsonb       NOT NULL,
    synced_at     timestamptz NOT NULL DEFAULT now(),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 11. kite_oauth_nonces (replay protection for Kite OAuth flow)
-- ---------------------------------------------------------------------------
CREATE TABLE public.kite_oauth_nonces (
    nonce      uuid        PRIMARY KEY,
    user_id    uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_kite_oauth_nonces_expires ON public.kite_oauth_nonces(expires_at);

-- ===========================================================================
-- Row Level Security (RLS)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- fire_inputs — per-operation policies
-- ---------------------------------------------------------------------------
ALTER TABLE public.fire_inputs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.fire_inputs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "insert_own" ON public.fire_inputs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own" ON public.fire_inputs
    FOR UPDATE USING (auth.uid() = user_id)
              WITH CHECK (auth.uid() = user_id);

CREATE POLICY "delete_own" ON public.fire_inputs
    FOR DELETE USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- income_entries — per-operation policies
-- ---------------------------------------------------------------------------
ALTER TABLE public.income_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.income_entries
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "insert_own" ON public.income_entries
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own" ON public.income_entries
    FOR UPDATE USING (auth.uid() = user_id)
              WITH CHECK (auth.uid() = user_id);

CREATE POLICY "delete_own" ON public.income_entries
    FOR DELETE USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- fixed_expenses — per-operation policies
-- ---------------------------------------------------------------------------
ALTER TABLE public.fixed_expenses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.fixed_expenses
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "insert_own" ON public.fixed_expenses
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own" ON public.fixed_expenses
    FOR UPDATE USING (auth.uid() = user_id)
              WITH CHECK (auth.uid() = user_id);

CREATE POLICY "delete_own" ON public.fixed_expenses
    FOR DELETE USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- sip_log — per-operation policies
-- ---------------------------------------------------------------------------
ALTER TABLE public.sip_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.sip_log
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "insert_own" ON public.sip_log
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own" ON public.sip_log
    FOR UPDATE USING (auth.uid() = user_id)
              WITH CHECK (auth.uid() = user_id);

CREATE POLICY "delete_own" ON public.sip_log
    FOR DELETE USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- sip_log_funds — policies via join to sip_log
-- ---------------------------------------------------------------------------
ALTER TABLE public.sip_log_funds ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.sip_log_funds
    FOR SELECT USING (
        sip_log_id IN (SELECT id FROM public.sip_log WHERE user_id = auth.uid())
    );

CREATE POLICY "insert_own" ON public.sip_log_funds
    FOR INSERT WITH CHECK (
        sip_log_id IN (SELECT id FROM public.sip_log WHERE user_id = auth.uid())
    );

CREATE POLICY "update_own" ON public.sip_log_funds
    FOR UPDATE USING (
        sip_log_id IN (SELECT id FROM public.sip_log WHERE user_id = auth.uid())
    )
    WITH CHECK (
        sip_log_id IN (SELECT id FROM public.sip_log WHERE user_id = auth.uid())
    );

CREATE POLICY "delete_own" ON public.sip_log_funds
    FOR DELETE USING (
        sip_log_id IN (SELECT id FROM public.sip_log WHERE user_id = auth.uid())
    );

-- ---------------------------------------------------------------------------
-- audit_log — insert + select only (users cannot update or delete)
-- ---------------------------------------------------------------------------
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "insert_own" ON public.audit_log
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "select_own" ON public.audit_log
    FOR SELECT USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- projects — per-operation policies
-- ---------------------------------------------------------------------------
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.projects
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "insert_own" ON public.projects
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own" ON public.projects
    FOR UPDATE USING (auth.uid() = user_id)
              WITH CHECK (auth.uid() = user_id);

CREATE POLICY "delete_own" ON public.projects
    FOR DELETE USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- project_expenses — policies via join to projects
-- ---------------------------------------------------------------------------
ALTER TABLE public.project_expenses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.project_expenses
    FOR SELECT USING (
        project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid())
    );

CREATE POLICY "insert_own" ON public.project_expenses
    FOR INSERT WITH CHECK (
        project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid())
    );

CREATE POLICY "update_own" ON public.project_expenses
    FOR UPDATE USING (
        project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid())
    )
    WITH CHECK (
        project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid())
    );

CREATE POLICY "delete_own" ON public.project_expenses
    FOR DELETE USING (
        project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid())
    );
