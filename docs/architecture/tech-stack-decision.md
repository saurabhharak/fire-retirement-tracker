# Tech Stack Decision — FIRE Retirement Tracker v2

**Date:** 2026-03-31
**Status:** Approved
**Decision:** Migrate from Streamlit prototype to FastAPI + React production app

---

## Stack Summary

| Layer | Technology | Hosting | Cost |
|---|---|---|---|
| Frontend | React + Vite + Tailwind CSS + shadcn/ui | Vercel (free) | $0 |
| Backend | FastAPI + Supabase Python Client | Render (free) | $0 |
| Database | Supabase (PostgreSQL + RLS) | Supabase (free) | $0 |
| Auth | Supabase Auth (frontend) + JWT verify (FastAPI) | Supabase | $0 |
| Charts | Recharts | Bundled | $0 |
| Data Fetching | TanStack Query | Bundled | $0 |
| Offline | PWA (vite-plugin-pwa + Workbox) | N/A | $0 |
| CI/CD | GitHub Actions | GitHub (free) | $0 |
| **Total** | | | **$0/month** |

---

## Architecture Overview

```
[Browser/PWA]
    |
    |-- Supabase Auth (direct) --> JWT token
    |
    |-- FastAPI (Bearer JWT) --> Financial calculations, CRUD
    |       |
    |       |-- engine.py (unchanged, 720 tests)
    |       |-- Supabase client (per-request, user JWT for RLS)
    |
    |-- Supabase DB (RLS enforced)
```

### Auth Flow
1. React frontend calls Supabase Auth directly (OTP/password)
2. Supabase returns JWT (access_token + refresh_token)
3. Frontend stores tokens in memory + httpOnly cookie
4. Every FastAPI request includes `Authorization: Bearer <jwt>`
5. FastAPI validates JWT locally using Supabase JWT secret (no network call)
6. For DB operations, FastAPI creates per-request Supabase client with user's JWT
7. Supabase RLS policies enforce row-level access using auth.uid() from JWT

---

## Monorepo Structure

```
fire-retirement-tracker/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, CORS, lifespan, middleware
│   │   ├── config.py               # pydantic-settings: env vars, secrets
│   │   ├── dependencies.py         # get_current_user (JWT validation)
│   │   ├── exceptions.py           # Custom exception handlers
│   │   │
│   │   ├── core/                   # ZERO framework dependencies
│   │   │   ├── __init__.py
│   │   │   ├── engine.py           # Financial calculations (UNCHANGED from v1)
│   │   │   ├── constants.py        # Fund splits, bucket %, SWR (from config.py)
│   │   │   ├── formatting.py       # format_indian(), date helpers
│   │   │   └── models.py           # Pydantic v2 models (UNCHANGED from v1)
│   │   │
│   │   ├── routers/                # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # POST /auth/login, /auth/otp/send, /auth/otp/verify
│   │   │   ├── fire_inputs.py      # GET/PUT /fire-inputs
│   │   │   ├── income.py           # GET/POST/PUT/DELETE /income
│   │   │   ├── expenses.py         # GET/POST/PATCH/DELETE /expenses
│   │   │   ├── sip_log.py          # GET/POST /sip-log
│   │   │   ├── projections.py      # GET /projections/growth, /projections/retirement
│   │   │   ├── fund_allocation.py  # GET /fund-allocation
│   │   │   └── export.py           # GET /export, DELETE /account
│   │   │
│   │   └── services/               # Business logic + DB access
│   │       ├── __init__.py
│   │       ├── supabase_client.py  # get_anon_client(), get_user_client(jwt)
│   │       ├── fire_inputs_svc.py  # load, save fire inputs
│   │       ├── income_svc.py       # load, save, delete income
│   │       ├── expenses_svc.py     # load, save, update, deactivate expenses
│   │       ├── sip_log_svc.py      # load, save SIP logs
│   │       └── audit_svc.py        # log_audit()
│   │
│   ├── tests/
│   │   ├── unit/                   # Fast, no network
│   │   │   ├── test_engine.py
│   │   │   ├── test_models.py
│   │   │   ├── test_formatting.py
│   │   │   └── test_constants.py
│   │   ├── integration/            # Requires Supabase
│   │   │   ├── test_api_fire_inputs.py
│   │   │   ├── test_api_income.py
│   │   │   ├── test_api_expenses.py
│   │   │   └── test_api_auth.py
│   │   └── excel_verification/     # Existing 720 tests (UNTOUCHED)
│   │       ├── conftest.py
│   │       ├── test_01_inputs.py
│   │       ├── test_02_fund_allocation.py
│   │       ├── test_03_growth_projection.py
│   │       ├── test_04_retirement_income.py
│   │       └── test_05_sip_tracker.py
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── public/
│   │   ├── manifest.json           # PWA manifest
│   │   └── favicon.svg             # Gem icon
│   ├── src/
│   │   ├── components/             # Reusable UI
│   │   │   ├── ui/                 # shadcn/ui components
│   │   │   ├── MetricCard.tsx
│   │   │   ├── DataTable.tsx
│   │   │   ├── ProsperityChart.tsx
│   │   │   ├── PageHeader.tsx
│   │   │   ├── LoadingState.tsx
│   │   │   └── EmptyState.tsx
│   │   ├── layouts/
│   │   │   ├── AppLayout.tsx       # Sidebar + main content
│   │   │   └── AuthLayout.tsx      # Login page layout
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── IncomeExpenses.tsx
│   │   │   ├── FireSettings.tsx
│   │   │   ├── FundAllocation.tsx
│   │   │   ├── GrowthProjection.tsx
│   │   │   ├── RetirementAnalysis.tsx
│   │   │   ├── SipTracker.tsx
│   │   │   ├── SettingsPrivacy.tsx
│   │   │   └── Login.tsx
│   │   ├── hooks/
│   │   │   ├── useFireInputs.ts    # TanStack Query hook
│   │   │   ├── useIncome.ts
│   │   │   ├── useExpenses.ts
│   │   │   ├── useSipLog.ts
│   │   │   ├── useProjections.ts
│   │   │   └── useAuth.ts
│   │   ├── lib/
│   │   │   ├── supabase.ts         # Supabase client init
│   │   │   ├── api.ts              # Axios/fetch wrapper for FastAPI
│   │   │   ├── formatIndian.ts     # Indian number formatting
│   │   │   └── constants.ts        # Prosperity colors, fund names
│   │   ├── styles/
│   │   │   └── globals.css         # Tailwind base + prosperity theme
│   │   ├── App.tsx                 # Router + providers
│   │   └── main.tsx                # Entry point
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.ts          # Prosperity color tokens
│
├── .github/
│   └── workflows/
│       ├── backend-ci.yml          # Test + deploy backend
│       └── frontend-ci.yml         # Build + deploy frontend (or Vercel auto)
│
├── docs/
│   ├── architecture/
│   │   ├── tech-stack-decision.md  # This file
│   │   ├── api-reference.md        # Auto-generated from FastAPI /docs
│   │   └── auth-flow.md            # Detailed auth sequence diagram
│   ├── adr/                        # Architecture Decision Records
│   │   ├── 001-fastapi-over-streamlit.md
│   │   ├── 002-react-vite-over-nextjs.md
│   │   ├── 003-supabase-client-over-sqlalchemy.md
│   │   ├── 004-pwa-over-react-native.md
│   │   └── 005-monorepo-structure.md
│   └── superpowers/                # Existing planning docs
│
├── stitch-designs/                 # UI mockups (8 screens)
├── migrations/                     # Supabase SQL migrations
├── README.md
└── Makefile                        # dev, test, build, deploy commands
```

---

## API Endpoints

### Auth (proxied through Supabase, not FastAPI)
Frontend calls Supabase directly. FastAPI only validates JWT.

### FIRE Inputs
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/fire-inputs` | Get user's FIRE settings |
| PUT | `/api/fire-inputs` | Upsert FIRE settings |

### Income
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/income?limit=12` | List recent income entries |
| POST | `/api/income` | Create/update income entry (upsert on month+year) |
| DELETE | `/api/income/{month}/{year}` | Delete income entry |

### Expenses
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/expenses?active=true` | List expenses |
| POST | `/api/expenses` | Create expense |
| PATCH | `/api/expenses/{id}` | Update expense |
| DELETE | `/api/expenses/{id}` | Soft-delete (deactivate) |

### SIP Log
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/sip-log?limit=60` | List SIP log entries |
| POST | `/api/sip-log` | Create/update SIP log (upsert) |

### Projections (computed, not stored)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/projections/growth` | Year-by-year growth projection |
| GET | `/api/projections/retirement` | Retirement metrics + buckets + SWR |
| GET | `/api/projections/fund-allocation` | 10-fund breakdown |
| GET | `/api/projections/monthly-sips` | 192-month SIP schedule |

### Export & Account
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/export` | Download all user data as JSON |
| DELETE | `/api/account` | Delete all user data |

---

## Migration Phases

### Phase 1: Backend (1-2 weeks)
- Set up FastAPI project structure
- Copy engine.py and constants unchanged
- Implement JWT validation dependency
- Port db.py functions to service layer
- Create all API routes
- Run 720 existing tests (must pass)
- Deploy to Render

### Phase 2: Frontend Shell (1 week)
- Scaffold React + Vite + Tailwind + shadcn/ui
- Configure prosperity theme colors in tailwind.config.ts
- Implement Supabase Auth (login page with OTP)
- Build AppLayout (sidebar navigation)
- Set up TanStack Query + API client
- Deploy to Vercel

### Phase 3: Pages (2-3 weeks)
One page at a time, using Stitch designs as reference:
1. Dashboard (metric cards + Recharts area chart)
2. FIRE Settings (form with live preview)
3. Income & Expenses (CRUD + pie chart + analysis)
4. Growth Projection (chart + table)
5. Retirement Analysis (buckets + SWR)
6. Fund Allocation (grouped table)
7. SIP Tracker (log + deviation badges)
8. Settings & Privacy (export + delete)

### Phase 4: PWA + Polish (1 week)
- Add vite-plugin-pwa with Workbox
- Implement offline expense queue
- Add install prompt for mobile
- Lighthouse performance audit
- Cut over from Streamlit to new app

---

## What We Keep From v1
- `engine.py` — unchanged, 720 tests
- `models.py` — Pydantic models, reused
- `config.py` — constants, renamed
- `schema.sql` — database schema + RLS policies
- Supabase project — all data, auth users, policies
- Stitch designs — UI reference for all 8 pages

## What We Replace
- Streamlit (frontend + routing) → React + Vite
- Streamlit session_state → JWT + httpOnly cookies
- st.cache_resource → TanStack Query (frontend) + lru_cache (backend)
- st.form() → React forms with react-hook-form
- Plotly → Recharts (lighter, React-native)
- Streamlit Cloud → Vercel (frontend) + Render (backend)
