# FIRE Retirement Tracker — Streamlit Web App Design Spec (v2)

**Goal:** Convert the Excel-based FIRE retirement planner into a Streamlit web app with Supabase (PostgreSQL) backend, basic auth, income/expense tracking, and all Excel sheet functionalities plus a dashboard.

**Architecture:** Streamlit multi-page app using `st.navigation()` with sidebar. Supabase for persistence and auth. All financial calculations in a pure Python engine (extracted from verified test oracle in `conftest.py`). No Excel dependency at runtime.

**Tech Stack:** Python 3.10+, Streamlit 1.36+, Supabase (free tier), supabase-py, plotly, pydantic, python-dotenv

---

## 1. Authentication & Session Management

- Email + password login via Supabase Auth (bcrypt password hashing)
- Login page shown when not authenticated; pages conditionally registered via `st.navigation()`
- **Password policy**: minimum 12 characters (configured in Supabase dashboard)
- **Brute-force protection**: Supabase Auth rate limits (configure in dashboard: Auth > Rate Limits)
- **JWT handling**: stored in `st.session_state["access_token"]`. Refresh via `supabase.auth.get_session()` on each page load. On expiry, redirect to login.
- **Idle session timeout**: 30 minutes. Track `st.session_state["last_activity"]` timestamp; if exceeded, clear session and redirect to login.
- **Disable public signup**: After creating the initial account, disable email signups in Supabase dashboard (Auth > Settings > Enable email signups = false). App shows "Contact admin" instead of signup form when disabled.
- **HTTPS**: Mandatory in production. Streamlit Cloud provides this automatically; self-hosted requires nginx/Caddy with TLS.

---

## 2. Database Schema (Supabase PostgreSQL)

### Table: `fire_inputs` (1:1 per user — stores ALL settings)

`user_id` is both PK and FK to `auth.users.id`. No separate `profiles` table needed.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| user_id | uuid (PK, FK → auth.users) | NOT NULL | 1:1 with user |
| dob | date | NOT NULL | Date of birth |
| retirement_age | int | CHECK (retirement_age > 18 AND retirement_age < 100) | Target FIRE age |
| life_expectancy | int | CHECK (life_expectancy > retirement_age) | Planning horizon |
| your_sip | numeric | CHECK (your_sip >= 0) | Monthly SIP |
| wife_sip | numeric | CHECK (wife_sip >= 0) | Wife's monthly SIP |
| step_up_pct | numeric | CHECK (step_up_pct >= 0 AND step_up_pct <= 0.5) | Annual step-up |
| existing_corpus | numeric | CHECK (existing_corpus >= 0) | Current portfolio |
| equity_return | numeric | CHECK (equity_return > 0 AND equity_return <= 0.3) | |
| debt_return | numeric | CHECK (debt_return > 0 AND debt_return <= 0.3) | |
| gold_return | numeric | CHECK (gold_return >= 0 AND gold_return <= 0.3) | |
| cash_return | numeric | CHECK (cash_return >= 0 AND cash_return <= 0.3) | |
| inflation | numeric | CHECK (inflation > 0 AND inflation <= 0.2) | |
| swr | numeric | CHECK (swr > 0 AND swr <= 0.10) | Safe withdrawal rate |
| equity_pct | numeric | CHECK (equity_pct >= 0 AND equity_pct <= 1) | |
| gold_pct | numeric | CHECK (gold_pct >= 0 AND gold_pct <= 1) | |
| cash_pct | numeric | CHECK (cash_pct >= 0 AND cash_pct <= 1) | |
| monthly_expense | numeric | CHECK (monthly_expense >= 0) | Current expenses |
| updated_at | timestamptz | DEFAULT now() | Auto-update via trigger |

**Table-level constraint**: `CHECK (equity_pct + gold_pct + cash_pct <= 1.0)`

**Derived values (computed in engine, NOT stored)**:
- `debt_pct = 1 - equity_pct - gold_pct - cash_pct`
- `total_sip = your_sip + wife_sip`
- `current_age = floor((today - dob) / 365.25)`
- `years_to_retirement = retirement_age - current_age`
- `retirement_duration = life_expectancy - retirement_age`

### Table: `income_entries`

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid (PK) | DEFAULT gen_random_uuid() |
| user_id | uuid (FK) | NOT NULL |
| month | int | CHECK (month >= 1 AND month <= 12) |
| year | int | CHECK (year >= 2020 AND year <= 2100) |
| your_income | numeric | CHECK (your_income >= 0) |
| wife_income | numeric | CHECK (wife_income >= 0) |
| notes | text | Max 500 chars |
| created_at | timestamptz | DEFAULT now() |
| updated_at | timestamptz | DEFAULT now() |

**Unique constraint**: `UNIQUE(user_id, month, year)`

### Table: `fixed_expenses`

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid (PK) | DEFAULT gen_random_uuid() |
| user_id | uuid (FK) | NOT NULL |
| name | text | NOT NULL, max 100 chars |
| amount | numeric | CHECK (amount > 0) |
| frequency | text | CHECK (frequency IN ('monthly', 'quarterly', 'yearly')) |
| is_active | boolean | DEFAULT true |
| created_at | timestamptz | DEFAULT now() |
| updated_at | timestamptz | DEFAULT now() |

**Index**: `CREATE INDEX idx_fixed_expenses_user_active ON fixed_expenses(user_id, is_active)`

### Table: `sip_log`

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid (PK) | DEFAULT gen_random_uuid() |
| user_id | uuid (FK) | NOT NULL |
| month | int | CHECK (month >= 1 AND month <= 12) |
| year | int | |
| planned_sip | numeric | |
| actual_invested | numeric | CHECK (actual_invested >= 0) |
| notes | text | Max 500 chars |
| created_at | timestamptz | DEFAULT now() |
| updated_at | timestamptz | DEFAULT now() |

**Unique constraint**: `UNIQUE(user_id, month, year)`

### Table: `sip_log_funds` (normalized fund breakdown)

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid (PK) | DEFAULT gen_random_uuid() |
| sip_log_id | uuid (FK → sip_log.id) | ON DELETE CASCADE |
| fund_name | text | NOT NULL |
| amount | numeric | CHECK (amount >= 0) |

### Table: `audit_log`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | |
| user_id | uuid | |
| action | text | 'login', 'logout', 'save_inputs', 'log_income', etc. |
| details | jsonb | Additional context |
| created_at | timestamptz | DEFAULT now() |

---

## 3. Row Level Security (RLS)

All tables have RLS enabled. Explicit per-operation policies:

```sql
-- fire_inputs (PK = user_id)
CREATE POLICY "select_own" ON fire_inputs FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "insert_own" ON fire_inputs FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own" ON fire_inputs FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own" ON fire_inputs FOR DELETE USING (auth.uid() = user_id);

-- income_entries, fixed_expenses, sip_log (FK = user_id)
-- Same pattern for each:
CREATE POLICY "select_own" ON <table> FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "insert_own" ON <table> FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own" ON <table> FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own" ON <table> FOR DELETE USING (auth.uid() = user_id);

-- sip_log_funds (joined via sip_log)
CREATE POLICY "select_own" ON sip_log_funds FOR SELECT
  USING (sip_log_id IN (SELECT id FROM sip_log WHERE user_id = auth.uid()));
CREATE POLICY "insert_own" ON sip_log_funds FOR INSERT
  WITH CHECK (sip_log_id IN (SELECT id FROM sip_log WHERE user_id = auth.uid()));
CREATE POLICY "update_own" ON sip_log_funds FOR UPDATE
  USING (sip_log_id IN (SELECT id FROM sip_log WHERE user_id = auth.uid()))
  WITH CHECK (sip_log_id IN (SELECT id FROM sip_log WHERE user_id = auth.uid()));
CREATE POLICY "delete_own" ON sip_log_funds FOR DELETE
  USING (sip_log_id IN (SELECT id FROM sip_log WHERE user_id = auth.uid()));

-- audit_log (insert-only for users, read via dashboard)
CREATE POLICY "insert_own" ON audit_log FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "select_own" ON audit_log FOR SELECT USING (auth.uid() = user_id);
```

---

## 4. Caching & State Management Strategy

### Supabase Client
```python
@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)
```

### User Data (loaded once on login, refreshed on save)
```python
st.session_state["fire_inputs"]    # dict, loaded on login, updated on save
st.session_state["income_cache"]   # last 12 months, refreshed on income page
st.session_state["expenses_cache"] # active fixed expenses, refreshed on expense page
st.session_state["last_activity"]  # datetime, for idle timeout
st.session_state["access_token"]   # Supabase JWT
st.session_state["user_id"]        # auth.uid()
```

### Computation Caching
```python
@st.cache_data
def cached_growth_projection(_inputs_hash, inputs):
    return compute_growth_projection(inputs)
```
Invalidated when `fire_inputs` are saved (clear cache via `cached_growth_projection.clear()`).

### Rules
- Never query Supabase inside a widget callback or on every rerun
- All input pages use `st.form()` to batch changes
- DB queries happen once per page load, results stored in `session_state`
- Computations are `@st.cache_data` keyed on inputs hash

---

## 5. Input Validation

### Pydantic Models (`models.py`)

```python
class FireInputs(BaseModel):
    dob: date
    retirement_age: int = Field(ge=19, le=99)
    life_expectancy: int = Field(ge=50, le=120)
    your_sip: float = Field(ge=0)
    wife_sip: float = Field(ge=0)
    step_up_pct: float = Field(ge=0, le=0.5)
    existing_corpus: float = Field(ge=0)
    equity_return: float = Field(gt=0, le=0.3)
    debt_return: float = Field(gt=0, le=0.3)
    gold_return: float = Field(ge=0, le=0.3)
    cash_return: float = Field(ge=0, le=0.3)
    inflation: float = Field(gt=0, le=0.2)
    swr: float = Field(gt=0, le=0.10)
    equity_pct: float = Field(ge=0, le=1.0)
    gold_pct: float = Field(ge=0, le=1.0)
    cash_pct: float = Field(ge=0, le=1.0)
    monthly_expense: float = Field(ge=0)

    @validator('life_expectancy')
    def life_after_retirement(cls, v, values):
        if v <= values.get('retirement_age', 0):
            raise ValueError('Life expectancy must exceed retirement age')
        return v

    @validator('cash_pct')
    def allocation_sum(cls, v, values):
        total = values.get('equity_pct', 0) + values.get('gold_pct', 0) + v
        if total > 1.0:
            raise ValueError('Equity + Gold + Cash cannot exceed 100%')
        return v

class IncomeEntry(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2020, le=2100)
    your_income: float = Field(ge=0)
    wife_income: float = Field(ge=0)
    notes: str = Field(max_length=500, default="")

class FixedExpense(BaseModel):
    name: str = Field(max_length=100)
    amount: float = Field(gt=0)
    frequency: Literal["monthly", "quarterly", "yearly"]
```

### UI Validation
- Sliders enforce min/max ranges
- Real-time display: "Debt auto-adjusts to X%" / "Total: 100%"
- Save button disabled if validation fails
- `st.error()` for validation messages

---

## 6. Error Handling

- All Supabase calls wrapped in try/except
- On DB error: `st.error("Could not save. Please try again.")` — no stack traces shown
- On JWT expiry: clear session, redirect to login with `st.warning("Session expired")`
- Engine functions raise `ValueError` on invalid inputs (e.g., SWR=0 causing division by zero)
- Calculation errors caught and shown as `st.error()` with generic message
- All errors logged server-side to `audit_log` table with details in `jsonb`

---

## 7. Pages

### 7.1 Login Page
- Email + password form using `st.form()`
- Error message on invalid credentials
- "Contact admin" note (signup disabled)
- On success: load `fire_inputs` into `session_state`, redirect to Dashboard

### 7.2 Dashboard (Home)
- **FIRE Countdown**: "X years Y months to FIRE" with progress bar
- **Income row** (4 metric cards): This month's income | Fixed expenses | Monthly savings | Savings rate %
- **FIRE row** (4 metric cards): Projected corpus | Required corpus | Funded ratio (color-coded) | Monthly SWP vs expense
- **Growth chart**: Plotly area chart (equity vs debt+gold+cash stacked)
- All numbers in Indian format (lakhs/crores)

### 7.3 Income & Expenses
- **Income section** (`st.form()`): Select month/year, enter your income + wife's income + notes. Save. Table of last 12 months via `st.dataframe()`.
- **Fixed Expenses section**: List active expenses. "Add New" form (name, amount, frequency). Edit / Deactivate per row. Total monthly outflow at bottom.
- **Summary card**: Total Income - Fixed Expenses - Total SIP = Discretionary

### 7.4 FIRE Settings
- All inputs inside `st.form("fire_settings")` to prevent reruns
- **Personal**: DOB (date_input), Retirement Age (slider 30-70), Life Expectancy (slider 60-100)
- **Investment**: Your SIP, Wife's SIP, Step-up %, Existing Corpus (number_input)
- **Returns**: Equity, Debt, Gold, Cash return sliders + Inflation
- **Allocation**: Equity %, Gold %, Cash % sliders. Debt auto-displays as `1 - sum`. Red warning if sum > 100%.
- **Preview section** (outside form, updates on save): Blended return, Real return (Fisher), Years to retirement
- Save → validate with Pydantic → upsert to Supabase → update session_state → clear computation cache

### 7.5 Fund Allocation
- Read-only `st.dataframe()` generated from settings
- 10 funds: Name, Category, % of Portfolio, Monthly SIP (amount)
- Fund splits from `config.py` constants
- Totals row

### 7.6 Growth Projection
- Year-by-year `st.dataframe()`: Year, Age, Monthly SIP, Annual Investment, Cumulative, Portfolio, Gains, Equity, Debt+Gold+Cash
- Shows all years (accumulation + post-retirement compounding without withdrawals)
- **Plotly chart**: stacked area chart
- Indian number formatting throughout

### 7.7 Retirement Analysis
- **Key Metrics** (cards): Corpus, Annual expense, Monthly SWP, Monthly expense, Surplus/deficit, Funded ratio, Required corpus
- **3-Bucket Strategy**: Plotly horizontal bar — Safety 8%, Income 27%, Growth 65% — with amounts and coverage years
- **SWR Comparison**: `st.dataframe()` — 2%, 2.5%, 3%, 3.5%, 4% with verdict column

### 7.8 SIP Tracker
- Monthly log form (`st.form()`): Month/year, actual invested, per-fund breakdown (expandable), notes
- `st.dataframe()` with planned vs actual + difference
- Color coding: green (actual >= planned), red (under)
- Running totals

### 7.9 Settings & Privacy
- **Export My Data**: Download all data as JSON
- **Delete My Account**: Confirm dialog → delete all rows from all tables → delete Supabase Auth user
- Accessible from sidebar

---

## 8. Calculation Engine (`engine.py`)

Pure Python module. **Canonical reference: `tests/conftest.py` oracle functions.** Must match exactly.

```python
def compute_derived_inputs(raw: dict) -> dict:
    """Add derived fields: debt_pct, total_sip, current_age, years_to_retirement, etc."""

def blended_return(inputs: dict) -> float:
    """Weighted average: equity*eq_ret + debt*debt_ret + gold*gold_ret + cash*cash_ret"""

def real_return(nominal: float, inflation: float) -> float:
    """Fisher equation: (1+nominal)/(1+inflation) - 1"""

def compute_growth_projection(inputs: dict) -> list[dict]:
    """41 rows (year 0-40). Mid-year convention: prev*(1+r) + annual*(1+r/2).
    Year 1 uses base SIP (no step-up). Post-retirement SIP=0."""

def compute_retirement_metrics(inputs: dict, corpus: float) -> dict:
    """SWR income, funded ratio, surplus, required corpus, 3-bucket amounts"""

def compute_fund_allocation(inputs: dict) -> list[dict]:
    """10-fund breakdown using splits from config.py"""

def compute_monthly_sips(inputs: dict) -> list[float]:
    """192 months. Step-up at months 13, 25, 37... Same logic as conftest.py"""

def format_indian(amount: float) -> str:
    """Indian notation: 1,30,20,768"""
```

---

## 9. Constants (`config.py`)

```python
EQUITY_SUB_SPLITS = {"Nifty 50": 35, "Nifty Next 50": 20, "Midcap 150": 20, "Smallcap 250": 10, "Total Market": 15}
DEBT_SUB_SPLITS = {"Short Duration": 40, "Arbitrage": 30, "Liquid/Overnight": 30}
BUCKET_PERCENTAGES = {"Safety": 0.08, "Income": 0.27, "Growth": 0.65}
SWR_SCENARIOS = [0.02, 0.025, 0.03, 0.035, 0.04]
SWR_VERDICTS = {0.02: "Ultra Safe", 0.025: "Very Safe", 0.03: "Recommended", 0.035: "Moderate Risk", 0.04: "Risky (45yr)"}
IDLE_TIMEOUT_MINUTES = 30
```

---

## 10. File Structure

```
fire-retirement-tracker/
├── app.py                     # Entry point: st.navigation(), auth gate, sidebar
├── engine.py                  # Pure Python financial calculations
├── models.py                  # Pydantic models for validation
├── config.py                  # Constants (fund splits, buckets, SWR rates)
├── db.py                      # Supabase CRUD + audit logging
├── auth.py                    # Login/logout, JWT refresh, session timeout
├── pages/
│   ├── dashboard.py
│   ├── income_expenses.py
│   ├── fire_settings.py
│   ├── fund_allocation.py
│   ├── growth_projection.py
│   ├── retirement_analysis.py
│   ├── sip_tracker.py
│   └── settings_privacy.py
├── schema.sql                 # Full DDL: tables, constraints, indexes, RLS, triggers
├── requirements.txt           # streamlit, supabase, plotly, pydantic, python-dotenv
├── .env.example               # Template (anon key only, with warning)
├── .gitignore                 # .env, __pycache__, .streamlit/secrets.toml
├── .streamlit/
│   └── config.toml            # Theme, wide layout, XSRF protection
└── tests/                     # Existing test suite (720 tests)
```

---

## 11. Secrets & Deployment

- `.env` stores ONLY: `SUPABASE_URL` and `SUPABASE_KEY` (anon key)
- **NEVER** store the `service_role` key in `.env` or anywhere in the app
- `.gitignore` includes `.env`, `.env.local`, `__pycache__/`, `.streamlit/secrets.toml`
- `.env.example` includes warning comment about service_role key
- Runtime check: verify key is anon key (decode JWT, check `role` claim is `anon`)
- `.streamlit/config.toml`: `server.enableCORS = false`, `server.enableXsrfProtection = true`

---

## 12. Audit Logging

Log to `audit_log` table:
- Auth events: login success, login failure, logout, session timeout
- Data changes: save_inputs, log_income, add_expense, deactivate_expense, log_sip
- Privacy actions: export_data, delete_account
- Errors: DB failures, validation failures

---

## 13. Privacy & Data Retention

- **Export My Data**: JSON download of all user data across all tables
- **Delete My Account**: Cascading delete from all tables + Supabase Auth user deletion
- Financial data about wife (income, SIP) stored as household planning inputs with implicit consent
- No data shared with third parties
- Compliant with India's DPDP Act 2023 (personal data access + deletion rights)
