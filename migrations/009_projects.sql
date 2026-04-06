-- Migration 009: Project expenses module (multi-project expense tracking)
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

-- ============================================================
-- 1. projects table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.projects (
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

CREATE INDEX IF NOT EXISTS idx_projects_user_status
    ON public.projects(user_id, status);

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON public.projects
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.projects
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "insert_own" ON public.projects
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own" ON public.projects
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own" ON public.projects
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- 2. project_expenses table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.project_expenses (
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

CREATE INDEX IF NOT EXISTS idx_project_expenses_project_id
    ON public.project_expenses(project_id);

CREATE TRIGGER trg_project_expenses_updated_at
    BEFORE UPDATE ON public.project_expenses
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS (join-based, same pattern as sip_log_funds)
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
    FOR UPDATE
    USING (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()))
    WITH CHECK (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()));
CREATE POLICY "delete_own" ON public.project_expenses
    FOR DELETE USING (
        project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid())
    );

COMMIT;
