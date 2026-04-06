-- Migration 008: Expand gold tracking to precious metals (gold, silver, platinum)
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

-- ============================================================
-- 2.1: Rename gold_purchases -> precious_metal_purchases
-- ============================================================
ALTER TABLE gold_purchases RENAME TO precious_metal_purchases;

-- Add metal_type column (default 'gold' for existing rows)
ALTER TABLE precious_metal_purchases
  ADD COLUMN metal_type TEXT NOT NULL DEFAULT 'gold';

-- Add CHECK for valid metal types
ALTER TABLE precious_metal_purchases
  ADD CONSTRAINT precious_metal_type_check
  CHECK (metal_type IN ('gold', 'silver', 'platinum'));

-- Drop old purity constraint (auto-generated name from 007 inline CHECK)
-- and add metal-specific one
ALTER TABLE precious_metal_purchases
  DROP CONSTRAINT IF EXISTS gold_purchases_purity_check;
ALTER TABLE precious_metal_purchases
  ADD CONSTRAINT precious_metal_purity_check
  CHECK (
    (metal_type = 'gold'     AND purity IN ('24K', '22K', '18K'))
    OR (metal_type = 'silver'   AND purity IN ('999', '925', '900'))
    OR (metal_type = 'platinum' AND purity IN ('999', '950', '900'))
  );

-- Add index for metal_type queries
CREATE INDEX IF NOT EXISTS idx_precious_metal_type
  ON precious_metal_purchases(user_id, metal_type, is_active);

-- Recreate RLS policies
-- 007 used short names: "select_own", "insert_own", "update_own", "delete_own"
DROP POLICY IF EXISTS "select_own" ON precious_metal_purchases;
DROP POLICY IF EXISTS "insert_own" ON precious_metal_purchases;
DROP POLICY IF EXISTS "update_own" ON precious_metal_purchases;
DROP POLICY IF EXISTS "delete_own" ON precious_metal_purchases;

CREATE POLICY "select_own"
  ON precious_metal_purchases FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "insert_own"
  ON precious_metal_purchases FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own"
  ON precious_metal_purchases FOR UPDATE
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own"
  ON precious_metal_purchases FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- 2.2: Replace gold_rate_cache with normalized precious_metal_rate_cache
-- ============================================================
DROP TABLE IF EXISTS gold_rate_cache;

CREATE TABLE precious_metal_rate_cache (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  metal_type    TEXT NOT NULL CHECK (metal_type IN ('gold', 'silver', 'platinum')),
  purity        TEXT NOT NULL,
  rate_per_gram NUMERIC NOT NULL CHECK (rate_per_gram > 0),
  currency      TEXT NOT NULL DEFAULT 'INR',
  source        TEXT NOT NULL,
  fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_metal_rate_latest
  ON precious_metal_rate_cache(metal_type, fetched_at DESC);

-- Auto-cleanup trigger: remove cache entries older than 90 days
CREATE OR REPLACE FUNCTION cleanup_old_metal_rates() RETURNS TRIGGER AS $$
BEGIN
  DELETE FROM precious_metal_rate_cache WHERE fetched_at < now() - INTERVAL '90 days';
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cleanup_metal_rates
  AFTER INSERT ON precious_metal_rate_cache
  FOR EACH STATEMENT
  EXECUTE FUNCTION cleanup_old_metal_rates();

-- ============================================================
-- 2.3: FIRE Settings column rename
-- ============================================================
ALTER TABLE fire_inputs RENAME COLUMN gold_pct TO precious_metals_pct;
ALTER TABLE fire_inputs RENAME COLUMN gold_return TO precious_metals_return;

COMMIT;
