# FIRE Retirement Tracker — Production Revamp Plan

## Goal
Restructure the codebase to industry-standard production quality with improved UI/UX based on Stitch designs.

## Current State
- 14 Python files, ~3000 lines, flat structure
- Working Streamlit + Supabase app deployed on Streamlit Cloud
- Security reviewed and hardened
- 720 formula verification tests

## Target State
- Industry-standard Python project structure
- Reusable UI components (Streamlit custom components pattern)
- Consistent styling across all pages matching Stitch designs
- Proper error boundaries and loading states
- Production logging and monitoring

---

## Phase 1: Project Restructuring (Industry Standard)

### Current Structure (flat)
```
fire-retirement-tracker/
├── app.py
├── auth.py, config.py, db.py, engine.py, models.py
├── pages/*.py (8 files)
├── schema.sql, requirements.txt
```

### Target Structure
```
fire-retirement-tracker/
├── src/
│   ├── __init__.py
│   ├── app.py                      # Entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Settings, constants, env loading
│   │   ├── models.py               # Pydantic models
│   │   ├── engine.py               # Financial calculations
│   │   └── formatting.py           # Indian number format, date utils
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── session.py              # Session management
│   │   ├── login.py                # Login/signup/OTP logic
│   │   └── middleware.py           # Auth checks, idle timeout
│   ├── db/
│   │   ├── __init__.py
│   │   ├── client.py               # Supabase client singleton
│   │   ├── fire_inputs.py          # FIRE settings CRUD
│   │   ├── income.py               # Income entries CRUD
│   │   ├── expenses.py             # Fixed expenses CRUD
│   │   ├── sip_log.py              # SIP tracker CRUD
│   │   └── audit.py                # Audit logging
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── theme.py                # CSS, colors, prosperity theme
│   │   ├── components.py           # Reusable: metric_card, data_table, chart
│   │   ├── sidebar.py              # Sidebar navigation component
│   │   └── layouts.py              # Page layout wrappers
│   └── pages/
│       ├── __init__.py
│       ├── dashboard.py
│       ├── income_expenses.py
│       ├── fire_settings.py
│       ├── fund_allocation.py
│       ├── growth_projection.py
│       ├── retirement_analysis.py
│       ├── sip_tracker.py
│       └── settings_privacy.py
├── tests/
│   ├── conftest.py
│   ├── test_engine.py              # Consolidated from test_01-05
│   ├── test_models.py
│   └── test_formatting.py
├── migrations/
│   ├── 001_initial_schema.sql
│   ├── 002_add_owner_column.sql
│   ├── 003_add_one_time_frequency.sql
│   └── 004_sip_log_constraints.sql
├── docs/
│   └── superpowers/
├── stitch-designs/                  # UI mockups from Stitch
├── .streamlit/
│   └── config.toml
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml                   # Modern Python packaging
└── README.md
```

---

## Phase 2: UI Component Library

### Reusable Components (`src/ui/components.py`)

```python
def metric_card(label, value, delta=None, color="default"):
    """Consistent metric card used across all pages."""

def data_table(df, columns_config=None):
    """Styled dataframe with Indian formatting, column headers, alternating rows."""

def prosperity_chart(fig):
    """Apply prosperity theme to any Plotly figure."""

def page_header(title, icon=None):
    """Consistent page header with icon."""

def loading_state(message="Loading..."):
    """Consistent loading indicator."""

def empty_state(message, action_label=None, action_page=None):
    """Consistent empty state with CTA."""
```

### Theme System (`src/ui/theme.py`)
```python
COLORS = {
    "primary": "#00895E",      # Emerald green
    "secondary": "#D4A843",    # Gold
    "tertiary": "#1A3A5C",     # Deep blue
    "background": "#0D1B2A",   # Deep navy
    "surface": "#132E3D",      # Dark teal
    "text": "#E8ECF1",         # Silver white
    "success": "#2E8B57",      # Prosperity green
    "warning": "#E5A100",      # Amber gold
    "error": "#C45B5B",        # Muted coral
}

CSS = """..."""  # All responsive CSS + prosperity theme
```

---

## Phase 3: UI Implementation (Based on Stitch Designs)

### Per-page improvements:

1. **Dashboard**: Bento grid layout, FIRE countdown with progress animation, growth chart with retirement line
2. **Income & Expenses**: Financial summary at top, pie chart, detailed breakdown, edit/delete inline
3. **FIRE Settings**: Form sections in cards, real-time preview, allocation visualization
4. **Fund Allocation**: Category-grouped table with color tags, summary cards at top
5. **Growth Projection**: Large chart with retirement marker, data table with accumulation/post-retirement styling
6. **Retirement Analysis**: Key metrics grid, horizontal bar chart for buckets, SWR comparison with highlighted recommended row
7. **SIP Tracker**: Log form in expander, history table with on-target/under badges
8. **Settings & Privacy**: Export/delete with confirmations

---

## Phase 4: Production Hardening

1. **Error boundaries**: Every page wrapped in try/except with user-friendly fallback
2. **Loading states**: Spinner while fetching from Supabase
3. **Cache strategy**: `@st.cache_data` on all engine computations, `@st.cache_resource` on Supabase client
4. **Logging**: Python `logging` module to stdout (captured by Streamlit Cloud)
5. **Health check**: Dashboard shows connection status to Supabase
6. **pyproject.toml**: Modern Python packaging with version, dependencies, metadata

---

## Implementation Order

1. Create `src/` directory structure with `__init__.py` files
2. Move and refactor `core/` modules (config, models, engine, formatting)
3. Create `ui/` component library (theme, components, sidebar, layouts)
4. Move and refactor `db/` modules (split from monolithic db.py)
5. Move and refactor `auth/` modules (split from auth.py)
6. Rebuild each page using UI components + Stitch design reference
7. Update app.py entry point with new imports
8. Move tests and update imports
9. Create migrations/ from schema.sql history
10. Update requirements.txt and create pyproject.toml
11. Test everything, push, deploy
