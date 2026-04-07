-- Migration 012: Money Ledger (personal debt tracker — contacts + transactions)
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

-- ============================================================
-- 1. ledger_contacts table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.ledger_contacts (
    id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name       text        NOT NULL CHECK (char_length(name) <= 100),
    phone      text        CHECK (phone IS NULL OR char_length(phone) <= 15),
    is_active  boolean     NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_ledger_contact_name UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_ledger_contacts_user_active
    ON public.ledger_contacts(user_id, is_active);

CREATE TRIGGER trg_ledger_contacts_updated_at
    BEFORE UPDATE ON public.ledger_contacts
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS
ALTER TABLE public.ledger_contacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.ledger_contacts
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "insert_own" ON public.ledger_contacts
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own" ON public.ledger_contacts
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own" ON public.ledger_contacts
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- 2. ledger_transactions table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.ledger_transactions (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id     uuid        NOT NULL REFERENCES public.ledger_contacts(id) ON DELETE CASCADE,
    direction      text        NOT NULL CHECK (direction IN ('gave', 'received')),
    amount         numeric     NOT NULL CHECK (amount > 0),
    date           date        NOT NULL,
    category       text        NOT NULL CHECK (category IN ('loan', 'borrowed', 'payment', 'advance', 'other')),
    payment_method text        NOT NULL CHECK (payment_method IN ('cash', 'upi', 'bank_transfer', 'other')),
    note           text        CHECK (note IS NULL OR char_length(note) <= 200),
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ledger_transactions_contact_id
    ON public.ledger_transactions(contact_id);

CREATE TRIGGER trg_ledger_transactions_updated_at
    BEFORE UPDATE ON public.ledger_transactions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS (join-based, same pattern as project_expenses / sip_log_funds)
ALTER TABLE public.ledger_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.ledger_transactions
    FOR SELECT USING (
        contact_id IN (SELECT id FROM public.ledger_contacts WHERE user_id = auth.uid())
    );
CREATE POLICY "insert_own" ON public.ledger_transactions
    FOR INSERT WITH CHECK (
        contact_id IN (SELECT id FROM public.ledger_contacts WHERE user_id = auth.uid())
    );
CREATE POLICY "update_own" ON public.ledger_transactions
    FOR UPDATE
    USING (contact_id IN (SELECT id FROM public.ledger_contacts WHERE user_id = auth.uid()))
    WITH CHECK (contact_id IN (SELECT id FROM public.ledger_contacts WHERE user_id = auth.uid()));
CREATE POLICY "delete_own" ON public.ledger_transactions
    FOR DELETE USING (
        contact_id IN (SELECT id FROM public.ledger_contacts WHERE user_id = auth.uid())
    );

COMMIT;
