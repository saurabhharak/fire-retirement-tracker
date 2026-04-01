<p align="center">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white" alt="React 18" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Supabase-PostgreSQL-3FCF8E?logo=supabase&logoColor=white" alt="Supabase" />
  <img src="https://img.shields.io/badge/Tests-782_passing-2E8B57" alt="Tests" />
  <img src="https://img.shields.io/badge/License-Private-gray" alt="License" />
</p>

# FIRE Retirement Tracker

A full-stack **Financial Independence, Retire Early (FIRE)** planning application for Indian investors. Track income, expenses, SIP investments, and project your path to financial freedom.

## Features

- **Dashboard** — FIRE countdown, income/expense metrics, portfolio growth chart
- **Income & Expenses** — Track monthly income, manage fixed expenses with owner tags (You/Wife/Household), pie chart breakdown
- **FIRE Settings** — Configure SIP, returns, asset allocation with auto-balancing debt
- **Fund Allocation** — 10-fund breakdown across Equity, Debt, Gold, Cash
- **Growth Projection** — Year-by-year corpus simulation with mid-year compounding, Recharts visualization
- **Retirement Analysis** — SWR comparison (2%-4%), 3-bucket strategy, funded ratio
- **SIP Tracker** — Monthly investment logging with deviation tracking
- **Email OTP + Password Authentication** — Secure login via Supabase Auth
- **Indian Number Formatting** — All amounts in lakhs/crores (₹)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   React SPA │────▸│  FastAPI     │────▸│  Supabase    │
│   (Vite)    │     │  (Python)   │     │  (PostgreSQL)│
│             │     │             │     │              │
│  Tailwind   │     │  engine.py  │     │  RLS Policies│
│  Recharts   │     │  (720 tests)│     │  Auth (JWT)  │
│  TanStack Q │     │  JWKS Auth  │     │  6 Tables    │
└─────────────┘     └─────────────┘     └──────────────┘
     Vercel              Render             Supabase
     (Free)              (Free)             (Free)
```

**Auth Flow:** React → Supabase Auth (OTP/password) → JWT → FastAPI validates via JWKS (ECC P-256) → Supabase RLS enforces row-level access

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, TanStack Query, Recharts |
| **Backend** | FastAPI, Python 3.10+, Pydantic v2, PyJWT, slowapi |
| **Database** | Supabase (PostgreSQL) with Row Level Security |
| **Auth** | Supabase Auth + JWKS asymmetric verification (ECC P-256) |
| **Hosting** | Vercel (frontend) + Render (backend) — $0/month |

## Project Structure

```
fire-retirement-tracker/
├── backend/                    # FastAPI API (26 files, ~1200 lines)
│   ├── app/
│   │   ├── main.py            # App entry, CORS, security headers, rate limiting
│   │   ├── config.py          # pydantic-settings (12-factor)
│   │   ├── dependencies.py    # JWKS JWT verification
│   │   ├── rate_limit.py      # slowapi rate limiter
│   │   ├── exceptions.py      # Custom error hierarchy
│   │   ├── core/
│   │   │   ├── engine.py      # Financial calculations (720 verified tests)
│   │   │   ├── constants.py   # Fund splits, bucket %, SWR rates
│   │   │   ├── formatting.py  # Indian number formatting
│   │   │   └── models.py      # Pydantic validation models
│   │   ├── routers/           # 18 API endpoints
│   │   └── services/          # Repository pattern CRUD
│   ├── tests/                 # 755 backend tests
│   └── Dockerfile
├── frontend/                   # React SPA (~30 files, ~3700 lines)
│   ├── src/
│   │   ├── contexts/          # AuthContext (shared auth state)
│   │   ├── hooks/             # TanStack Query hooks (6 hooks)
│   │   ├── components/        # MetricCard, PageHeader, etc.
│   │   ├── layouts/           # AppLayout, Sidebar, AuthLayout
│   │   ├── pages/             # 9 pages
│   │   └── lib/               # API client, formatting, constants
│   └── vercel.json
├── docs/                       # Architecture decisions, plans, specs
└── stitch-designs/            # UI mockups (8 screens)
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET/PUT | `/api/fire-inputs` | FIRE settings |
| GET/POST/DELETE | `/api/income` | Income entries |
| GET/POST/PATCH/DELETE | `/api/expenses` | Fixed expenses |
| GET/POST | `/api/sip-log` | SIP tracker |
| GET | `/api/projections/growth` | Year-by-year projection |
| GET | `/api/projections/retirement` | Retirement analysis |
| GET | `/api/projections/fund-allocation` | Fund breakdown |
| GET | `/api/export` | Data export (JSON) |
| DELETE | `/api/account` | Account deletion |

All write endpoints use Pydantic validation. All endpoints require JWT auth (except health). Rate limiting enforced via slowapi.

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Supabase](https://supabase.com) project (free tier)

### 1. Clone

```bash
git clone https://github.com/saurabhharak/fire-retirement-tracker.git
cd fire-retirement-tracker
```

### 2. Backend

```bash
cd backend
cp .env.example .env
# Edit .env with your Supabase URL and anon key
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 3. Frontend

```bash
cd frontend
cp .env.example .env
# Edit .env with Supabase credentials + API URL
npm install
npm run dev
```

### 4. Database

Run `backend/tests/excel_verification/` SQL files in Supabase SQL Editor to create tables with RLS.

Open http://localhost:5173 and log in.

## Testing

```bash
# Backend (755 tests)
cd backend && python -m pytest tests/ -v

# Frontend (27 tests)
cd frontend && npm test
```

**Total: 782 tests** covering financial calculations, model validation, API health, formatting, and component rendering.

## Security

- **Authentication**: JWKS asymmetric JWT verification (ECC P-256) — no shared secrets
- **Authorization**: Supabase RLS with per-operation policies on all 6 tables
- **Input Validation**: Pydantic v2 on all API write endpoints
- **Rate Limiting**: slowapi on all endpoints (30/min reads, 10/min writes, 1/hr account delete)
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- **CORS**: Explicit origins only, no wildcards
- **Docker**: Non-root user in production container
- **Secrets**: No hardcoded credentials, .env gitignored, JWKS eliminates secret management
- **Audit Logging**: Destructive actions logged to audit_log table
- **Account Deletion**: Requires explicit confirmation body (`DELETE_ALL_DATA`)

## Financial Engine

All calculations in `backend/app/core/engine.py` — pure Python, zero framework dependencies, verified against 720 tests:

- **Compounding**: Mid-year convention `prev*(1+r) + annual*(1+r/2)`
- **Real Return**: Fisher equation `(1+nominal)/(1+inflation) - 1`
- **SIP Step-up**: Year 1 = base SIP, step-up from Year 2
- **Asset Allocation**: Debt auto-balances `1 - equity% - gold% - cash%`
- **Number Formatting**: Indian notation (lakhs/crores)

## Design

Prosperity-aligned color theme based on Vastu Shastra, Feng Shui 2026, and finance UX research:

| Color | Hex | Purpose |
|---|---|---|
| Emerald Green | `#00895E` | Primary (growth, Lakshmi) |
| Gold | `#D4A843` | Accents (wealth, prosperity) |
| Deep Navy | `#0D1B2A` | Background (Water element) |
| Silver White | `#E8ECF1` | Text (Moon energy) |
| Amber | `#E5A100` | Warnings (no red — drains wealth) |

## Deployment

| Service | Platform | Cost |
|---|---|---|
| Frontend | Vercel | Free |
| Backend | Render | Free |
| Database | Supabase | Free |
| **Total** | | **$0/month** |

## License

Private — personal use only.
