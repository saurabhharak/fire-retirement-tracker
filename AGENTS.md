# AGENTS.md

Personal FIRE planning app for Indian investors: React 19 + Vite + TS frontend (`frontend/`), FastAPI backend (`backend/`), Supabase (Postgres + RLS + Auth). Hosted free-tier on Vercel + Render + Supabase. No CI — verification is manual (ruff / pytest / tsc).

## Commands

### Backend (from `backend/`)
- Install: `pip install -e ".[dev]"` (the `requirements.txt` lacks pytest/ruff)
- Tests: `python -m pytest tests/unit -q` — **always scope to `tests/unit`**. Bare `python -m pytest` also collects `tests/excel_verification/`, which errors out because its conftest expects `backend/tests/fire-retirement-tracker.xlsx`, which doesn't exist (the workbook lives at repo root).
- Single test: `python -m pytest tests/unit/test_models_validation.py -k name`
- Lint: `python -m ruff check app` (line length 100)

### Frontend (from `frontend/`)
- Tests: `npm test` — this wrapper forces `NODE_ENV=test`; running vitest directly fails with "React.act is not a function" when NODE_ENV=production leaks in
- Single file: `npm test -- src/lib/__tests__/dashboardMetrics.test.ts`
- Typecheck + build: `npm run build` (`tsc -b && vite build`) — no separate typecheck script
- Lint: `npm run lint`

### Dev servers
- Backend: `uvicorn app.main:app --port 8002 --reload` — must be **8002**; the Vite dev proxy targets it
- Frontend: `npm run dev` on :5173

## Gotchas
- README is stale in places: React 18 (actual: 19), backend port 8001 (actual: 8002), old test counts. Trust package.json/pyproject over README.
- `backend/.env` currently sets `ENVIRONMENT=production`, which disables `/docs` locally. Set `ENVIRONMENT=development` for Swagger.
- Only the anon key goes in env files. Service-role key is used only via `get_service_client()` for server-side ops with no user JWT (OAuth callback, Kite nonce/claim, metal-rate cache writes) — never for normal user requests.
- Root-level `tests/` is a legacy openpyxl suite verifying formulas in `fire-retirement-tracker.xlsx` — unrelated to the FastAPI app. Don't modify the xlsx files at repo root.

## Architecture
- Auth chain: Supabase Auth issues JWT → FastAPI verifies via JWKS (`app/dependencies.py`) → every DB call builds a per-request user-scoped Supabase client (`get_user_client(access_token)`) so Postgres RLS enforces row access. Services take `(user_id, ..., access_token)`.
- Layering: thin router (Pydantic validation + slowapi `@limiter.limit` + `log_audit` on destructive ops) → `app/services/*_svc.py` (Supabase CRUD) → `app/core/engine.py` pure-Python financial math (no framework deps; mid-year compounding; debt auto-balances to 1 − equity − gold − cash).
- New feature end-to-end: Pydantic models in `core/models.py` → router in `routers/` → service `services/<name>_svc.py` → register router in `main.py` → TanStack Query hook `src/hooks/use*.ts` → page/component → SQL migration.
- DB changes: hand-written numbered migrations in `migrations/NNN_*.sql`, applied manually via Supabase SQL Editor (no migration tool). Keep them idempotent (IF NOT EXISTS guards) and include RLS policy changes when adding tables.
- Frontend data fetching goes through `src/lib/api.ts` (`api.get/post/...`), which injects the Supabase JWT and signs out + redirects to `/login` on any 401.

## Conventions
- Money is INR formatted as lakhs/crores via `backend/app/core/formatting.py` / `frontend/src/lib/formatIndian.ts`.
- UI palette: emerald primary, gold accents, navy background; warnings use amber (#E5A100) — deliberately **no red anywhere** in the UI.
- Commits follow conventional style (`feat:`, `fix:`).
- Design docs live in `docs/superpowers/specs/` and `docs/superpowers/plans/` (dated YYYY-MM-DD) — check for an existing design before large features.
