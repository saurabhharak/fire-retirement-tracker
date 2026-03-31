# FIRE Retirement Tracker

A personal Financial Independence, Retire Early (FIRE) planning application built with Streamlit and Supabase.

## Features

- **Dashboard** — FIRE countdown, income/expense summary, portfolio growth chart, funded ratio
- **Income & Expenses** — Track monthly income (variable), manage recurring fixed expenses with owner tags (You/Wife/Household)
- **FIRE Settings** — Configure SIP amounts, step-up %, asset allocation, return assumptions, inflation, SWR
- **Fund Allocation** — Auto-generated 10-fund breakdown across Equity, Debt, Gold, and Cash
- **Growth Projection** — Year-by-year corpus simulation with mid-year compounding convention and interactive chart
- **Retirement Analysis** — SWR comparison (2%-4%), 3-bucket strategy (Safety/Income/Growth), funded ratio
- **SIP Tracker** — Log actual monthly investments vs planned, per-fund breakdown, deviation tracking

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit 1.52+ |
| Backend/DB | Supabase (PostgreSQL) |
| Auth | Supabase Auth (email + password) |
| Charts | Plotly |
| Validation | Pydantic v2 |
| Language | Python 3.10+ |

## Architecture

```
app.py                  # Entry point, auth gate, st.navigation()
engine.py               # Pure Python financial calculations (no Streamlit dependency)
models.py               # Pydantic validation models
config.py               # Constants (fund splits, bucket %, SWR scenarios)
db.py                   # Supabase CRUD with RLS enforcement
auth.py                 # Login, logout, JWT refresh, idle timeout
schema.sql              # Full DDL with constraints, indexes, RLS policies
pages/
  dashboard.py          # Home — metrics, charts, FIRE countdown
  income_expenses.py    # Income logging + fixed expense management
  fire_settings.py      # All FIRE planning inputs
  fund_allocation.py    # Read-only fund breakdown table
  growth_projection.py  # Year-by-year table + stacked area chart
  retirement_analysis.py # SWR, 3-bucket, funded ratio
  sip_tracker.py        # Monthly SIP logging + deviation tracking
  settings_privacy.py   # Data export (JSON) + account deletion
```

## Financial Calculation Engine

All calculations are in `engine.py` — pure Python with no framework dependency. Verified against 720 automated tests.

Key formulas:
- **Compounding**: Mid-year convention — `prev*(1+r) + annual*(1+r/2)` (not start-of-year)
- **Real Return**: Fisher equation — `(1+nominal)/(1+inflation) - 1`
- **SIP Step-up**: Year 1 uses base SIP, step-up starts from Year 2
- **Post-retirement**: SIP = 0, portfolio compounds without withdrawals
- **Asset Allocation**: Debt auto-balances — `1 - equity% - gold% - cash%`
- **Number Formatting**: Indian notation (lakhs/crores)

## Setup

### Prerequisites
- Python 3.10+
- A [Supabase](https://supabase.com) project (free tier works)

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd fire-retirement-tracker
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your Supabase project credentials:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
```

> **Never** use the `service_role` key. Only the anon (public) key.

### 3. Create database tables

Open your Supabase dashboard > SQL Editor > paste and run the contents of `schema.sql`.

This creates 6 tables with:
- CHECK constraints on all numeric fields
- Row Level Security (RLS) with per-operation policies (SELECT/INSERT/UPDATE/DELETE)
- Indexes on frequently queried columns
- Auto-updating `updated_at` triggers

### 4. Run the app

```bash
streamlit run app.py
```

### 5. First-time setup

1. Open `http://localhost:8501`
2. Click **Sign Up** tab — create your account
3. Go to Supabase dashboard > Auth > Settings > disable **"Allow new users to sign up"**
4. Navigate to **FIRE Settings** and enter your financial inputs

## Security

- **Authentication**: Supabase Auth with bcrypt password hashing, 30-minute idle timeout
- **Authorization**: Row Level Security on all 6 tables with per-operation policies
- **Input Validation**: Pydantic v2 models with field-level constraints
- **SQL Injection**: All queries via supabase-py parameterized API (no raw SQL)
- **XSS**: Streamlit's built-in escaping; no user data in `unsafe_allow_html`
- **CSRF**: Streamlit XSRF protection enabled
- **Rate Limiting**: Login attempt throttling (5 attempts max) + Supabase Auth rate limits
- **Secrets**: `.env` excluded via `.gitignore`; anon key only (never service_role)
- **Error Handling**: Generic user-facing messages; detailed errors logged server-side only
- **Privacy**: Data export (JSON) and account deletion available in Settings & Privacy

## Database Schema

| Table | Purpose |
|-------|---------|
| `fire_inputs` | All FIRE planning settings (1:1 per user, user_id as PK) |
| `income_entries` | Monthly income log (variable, yours + wife's) |
| `fixed_expenses` | Recurring expenses with owner, frequency, soft-delete |
| `sip_log` | Monthly actual vs planned SIP |
| `sip_log_funds` | Per-fund breakdown (normalized child of sip_log) |
| `audit_log` | Auth events + data change tracking |

## Currency

All amounts are in Indian Rupees (INR) with Indian number formatting:
- `1,25,000` (not 125,000)
- `10,84,40,302` (not 108,440,302)

## License

Private — personal use only.
