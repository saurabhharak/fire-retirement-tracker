BEGIN;

-- ---------------------------------------------------------------------------
-- 1. gold_purchases table
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.gold_purchases (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    purchase_date   date        NOT NULL,
    weight_grams    numeric     NOT NULL CHECK (weight_grams > 0),
    price_per_gram  numeric     NOT NULL CHECK (price_per_gram > 0),
    total_cost      numeric     NOT NULL GENERATED ALWAYS AS (weight_grams * price_per_gram) STORED,
    purity          text        NOT NULL CHECK (purity IN ('24K', '22K', '18K')),
    owner           text        NOT NULL DEFAULT 'household'
                                CHECK (owner IN ('you', 'wife', 'household')),
    notes           text        CHECK (char_length(notes) <= 500),
    is_active       boolean     NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Index: query pattern is always (user_id, is_active)
CREATE INDEX IF NOT EXISTS idx_gold_purchases_user_active
  ON public.gold_purchases(user_id, is_active);

-- Reuse the existing set_updated_at() trigger function from schema.sql
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgname = 'trg_gold_purchases_updated_at'
  ) THEN
    CREATE TRIGGER trg_gold_purchases_updated_at
        BEFORE UPDATE ON public.gold_purchases
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 2. gold_rate_cache table (global, no user_id)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.gold_rate_cache (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_24k        numeric     NOT NULL CHECK (rate_24k > 0),
    rate_22k        numeric     NOT NULL CHECK (rate_22k > 0),
    rate_18k        numeric     NOT NULL CHECK (rate_18k > 0),
    currency        text        NOT NULL DEFAULT 'INR',
    source          text        NOT NULL,
    fetched_at      timestamptz NOT NULL DEFAULT now()
);

-- Index: always query latest row by fetched_at
CREATE INDEX IF NOT EXISTS idx_gold_rate_cache_fetched_at
  ON public.gold_rate_cache(fetched_at DESC);

-- ---------------------------------------------------------------------------
-- 3. RLS for gold_purchases (A4: DROP POLICY IF EXISTS + CREATE POLICY)
-- ---------------------------------------------------------------------------
ALTER TABLE public.gold_purchases ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_own" ON public.gold_purchases;
CREATE POLICY "select_own" ON public.gold_purchases
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "insert_own" ON public.gold_purchases;
CREATE POLICY "insert_own" ON public.gold_purchases
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "update_own" ON public.gold_purchases;
CREATE POLICY "update_own" ON public.gold_purchases
    FOR UPDATE USING (auth.uid() = user_id)
              WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "delete_own" ON public.gold_purchases;
CREATE POLICY "delete_own" ON public.gold_purchases
    FOR DELETE USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- 4. gold_rate_cache: NO RLS (global table, backend-only via anon client)
-- ---------------------------------------------------------------------------
-- gold_rate_cache does not need RLS. The backend accesses it via the anon
-- client. The frontend never reads this table directly.

COMMIT;
