-- Migration 013: Amul Parlour module (multi-tenant business tracking)
-- Vrindavan Treats: daily sales, invoice purchases (Sarvam OCR), P&L analytics, Sarvam credit usage.
-- Introduces membership-based RLS (owner + data_entry roles) for the first time.
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

-- ============================================================
-- RLS helper functions (used by all parlour policies)
-- plpgsql (lazy table refs) + SECURITY DEFINER to avoid inlining
-- (inlining a STABLE plpgsql fn into the RLS policy caused
--  max_stack_depth exceeded). search_path pinned to public.
-- ============================================================
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

-- ============================================================
-- 1. parlours table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.parlours (
    id                     uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name                   text        NOT NULL CHECK (char_length(name) <= 100),
    owner_id               uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    sarvam_starting_credits numeric    NOT NULL DEFAULT 0 CHECK (sarvam_starting_credits >= 0),
    is_active              boolean     NOT NULL DEFAULT true,
    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_parlours_owner
    ON public.parlours(owner_id);

CREATE TRIGGER trg_parlours_updated_at
    BEFORE UPDATE ON public.parlours
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Auto-add the owner as a member (role='owner') when a parlour is created.
CREATE OR REPLACE FUNCTION public.add_owner_membership()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.parlour_members (parlour_id, member_id, role)
    VALUES (NEW.id, NEW.owner_id, 'owner')
    ON CONFLICT (parlour_id, member_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_parlours_add_owner
    AFTER INSERT ON public.parlours
    FOR EACH ROW EXECUTE FUNCTION public.add_owner_membership();

-- RLS
ALTER TABLE public.parlours ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.parlours
    FOR SELECT USING (public.parlour_member_of(id));
CREATE POLICY "insert_own" ON public.parlours
    FOR INSERT WITH CHECK (public.parlour_member_role(id) = 'owner');
CREATE POLICY "update_own" ON public.parlours
    FOR UPDATE USING (public.parlour_member_role(id) = 'owner')
    WITH CHECK (public.parlour_member_role(id) = 'owner');
CREATE POLICY "delete_own" ON public.parlours
    FOR DELETE USING (public.parlour_member_role(id) = 'owner');

-- ============================================================
-- 2. parlour_members table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.parlour_members (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    parlour_id  uuid        NOT NULL REFERENCES public.parlours(id) ON DELETE CASCADE,
    member_id   uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role        text        NOT NULL CHECK (role IN ('owner', 'data_entry')) DEFAULT 'data_entry',
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_parlour_member UNIQUE (parlour_id, member_id)
);

CREATE INDEX IF NOT EXISTS idx_parlour_members_member
    ON public.parlour_members(member_id);

CREATE TRIGGER trg_parlour_members_updated_at
    BEFORE UPDATE ON public.parlour_members
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS
ALTER TABLE public.parlour_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.parlour_members
    FOR SELECT USING (public.parlour_member_of(parlour_id));
CREATE POLICY "insert_own" ON public.parlour_members
    FOR INSERT WITH CHECK (public.parlour_member_role(parlour_id) = 'owner');
CREATE POLICY "update_own" ON public.parlour_members
    FOR UPDATE USING (public.parlour_member_role(parlour_id) = 'owner')
    WITH CHECK (public.parlour_member_role(parlour_id) = 'owner');
CREATE POLICY "delete_own" ON public.parlour_members
    FOR DELETE USING (public.parlour_member_role(parlour_id) = 'owner');

-- ============================================================
-- 3. amul_daily_sales table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.amul_daily_sales (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    parlour_id    uuid        NOT NULL REFERENCES public.parlours(id) ON DELETE CASCADE,
    sale_date     date        NOT NULL,
    cash_amount   numeric     NOT NULL DEFAULT 0 CHECK (cash_amount >= 0),
    online_amount numeric     NOT NULL DEFAULT 0 CHECK (online_amount >= 0),
    sender_name   text        NOT NULL DEFAULT '' CHECK (char_length(sender_name) <= 100),
    entered_by    uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_amul_sale_positive_total CHECK (cash_amount + online_amount > 0)
);

CREATE INDEX IF NOT EXISTS idx_amul_sales_parlour_date
    ON public.amul_daily_sales(parlour_id, sale_date);

CREATE TRIGGER trg_amul_daily_sales_updated_at
    BEFORE UPDATE ON public.amul_daily_sales
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS (membership-based)
ALTER TABLE public.amul_daily_sales ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.amul_daily_sales
    FOR SELECT USING (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );
CREATE POLICY "insert_own" ON public.amul_daily_sales
    FOR INSERT WITH CHECK (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );
CREATE POLICY "update_own" ON public.amul_daily_sales
    FOR UPDATE
    USING (parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid()))
    WITH CHECK (parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid()));
CREATE POLICY "delete_own" ON public.amul_daily_sales
    FOR DELETE USING (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );

-- ============================================================
-- 4. amul_invoices table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.amul_invoices (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    parlour_id          uuid        NOT NULL REFERENCES public.parlours(id) ON DELETE CASCADE,
    distributor         text        NOT NULL CHECK (char_length(distributor) <= 200),
    bill_no             text        CHECK (bill_no IS NULL OR char_length(bill_no) <= 100),
    bill_date           date        NOT NULL,
    invoice_type        text        NOT NULL CHECK (invoice_type IN ('tax_invoice', 'bill_of_supply')),
    total_amount        numeric     NOT NULL CHECK (total_amount >= 0),
    tax_amount          numeric     NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
    taxable_amount      numeric     NOT NULL DEFAULT 0 CHECK (taxable_amount >= 0),
    source_pdf          text        CHECK (source_pdf IS NULL OR char_length(source_pdf) <= 255),
    status              text        NOT NULL CHECK (status IN ('draft', 'confirmed')) DEFAULT 'draft',
    sarvam_request_id   text        CHECK (sarvam_request_id IS NULL OR char_length(sarvam_request_id) <= 100),
    sarvam_credits_used numeric     NOT NULL DEFAULT 0 CHECK (sarvam_credits_used >= 0),
    is_active           boolean     NOT NULL DEFAULT true,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_amul_invoices_parlour_date
    ON public.amul_invoices(parlour_id, bill_date);

CREATE TRIGGER trg_amul_invoices_updated_at
    BEFORE UPDATE ON public.amul_invoices
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS (membership-based)
ALTER TABLE public.amul_invoices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.amul_invoices
    FOR SELECT USING (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );
CREATE POLICY "insert_own" ON public.amul_invoices
    FOR INSERT WITH CHECK (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );
CREATE POLICY "update_own" ON public.amul_invoices
    FOR UPDATE
    USING (parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid()))
    WITH CHECK (parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid()));
CREATE POLICY "delete_own" ON public.amul_invoices
    FOR DELETE USING (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );

-- ============================================================
-- 5. amul_invoice_items table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.amul_invoice_items (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id   uuid        NOT NULL REFERENCES public.amul_invoices(id) ON DELETE CASCADE,
    parlour_id   uuid        NOT NULL REFERENCES public.parlours(id) ON DELETE CASCADE,
    sr_no        integer     NOT NULL DEFAULT 1 CHECK (sr_no >= 1),
    hsn          text        NOT NULL DEFAULT '' CHECK (char_length(hsn) <= 20),
    description  text        NOT NULL CHECK (char_length(description) <= 300),
    mrp          numeric     NOT NULL DEFAULT 0 CHECK (mrp >= 0),
    rate         numeric     NOT NULL DEFAULT 0 CHECK (rate >= 0),
    box_qty      integer     NOT NULL DEFAULT 0 CHECK (box_qty >= 0),
    pcs_qty      integer     NOT NULL DEFAULT 0 CHECK (pcs_qty >= 0),
    free_qty     integer     NOT NULL DEFAULT 0 CHECK (free_qty >= 0),
    scheme       text        NOT NULL DEFAULT '' CHECK (char_length(scheme) <= 200),
    discount     numeric     NOT NULL DEFAULT 0 CHECK (discount >= 0),
    gst_pct      numeric     NOT NULL DEFAULT 0 CHECK (gst_pct >= 0),
    gst_amount   numeric     NOT NULL DEFAULT 0 CHECK (gst_amount >= 0),
    net_amount   numeric     NOT NULL DEFAULT 0 CHECK (net_amount >= 0),
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_amul_invoice_items_invoice
    ON public.amul_invoice_items(invoice_id);

-- RLS (join through invoice -> parlour membership)
ALTER TABLE public.amul_invoice_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.amul_invoice_items
    FOR SELECT USING (
        invoice_id IN (
            SELECT id FROM public.amul_invoices
            WHERE parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
        )
    );
CREATE POLICY "insert_own" ON public.amul_invoice_items
    FOR INSERT WITH CHECK (
        invoice_id IN (
            SELECT id FROM public.amul_invoices
            WHERE parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
        )
    );
CREATE POLICY "update_own" ON public.amul_invoice_items
    FOR UPDATE
    USING (invoice_id IN (
        SELECT id FROM public.amul_invoices
        WHERE parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    ))
    WITH CHECK (invoice_id IN (
        SELECT id FROM public.amul_invoices
        WHERE parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    ));
CREATE POLICY "delete_own" ON public.amul_invoice_items
    FOR DELETE USING (
        invoice_id IN (
            SELECT id FROM public.amul_invoices
            WHERE parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
        )
    );

-- ============================================================
-- 6. sarvam_usage table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.sarvam_usage (
    id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    parlour_id         uuid        NOT NULL REFERENCES public.parlours(id) ON DELETE CASCADE,
    endpoint           text        NOT NULL CHECK (char_length(endpoint) <= 100),
    request_id         text        CHECK (request_id IS NULL OR char_length(request_id) <= 100),
    purpose            text        NOT NULL DEFAULT '' CHECK (char_length(purpose) <= 200),
    pages              integer     NOT NULL DEFAULT 1 CHECK (pages >= 1),
    credits_used       numeric     NOT NULL DEFAULT 0 CHECK (credits_used >= 0),
    cost_estimate_inr  numeric     NOT NULL DEFAULT 0 CHECK (cost_estimate_inr >= 0),
    status             text        NOT NULL CHECK (status IN ('success', 'error')) DEFAULT 'success',
    error_message      text        CHECK (error_message IS NULL OR char_length(error_message) <= 500),
    created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sarvam_usage_parlour_created
    ON public.sarvam_usage(parlour_id, created_at);

-- RLS (owner-only visibility for spend tracking)
ALTER TABLE public.sarvam_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.sarvam_usage
    FOR SELECT USING (public.parlour_member_role(parlour_id) = 'owner');
CREATE POLICY "insert_own" ON public.sarvam_usage
    FOR INSERT WITH CHECK (
        parlour_id IN (SELECT parlour_id FROM public.parlour_members WHERE member_id = auth.uid())
    );
CREATE POLICY "update_own" ON public.sarvam_usage
    FOR UPDATE
    USING (public.parlour_member_role(parlour_id) = 'owner')
    WITH CHECK (public.parlour_member_role(parlour_id) = 'owner');
CREATE POLICY "delete_own" ON public.sarvam_usage
    FOR DELETE USING (public.parlour_member_role(parlour_id) = 'owner');

COMMIT;
