# Project Expenses Module — Design Spec

**Date:** 2026-04-06
**Status:** Draft
**Scope:** New module for tracking project-based expenses (construction, renovation, etc.) — separate from recurring household expenses.

## Context

Saurabh tracked house construction expenses (Nov 2024 - Jan 2026, 109 entries, Rs. 22,03,212 total) in SQLite Cloud. This data needs to live in the FIRE Tracker app with the ability to add future project expenses. This is completely separate from the existing `fixed_expenses` table which tracks recurring monthly/quarterly/yearly household expenses.

## Requirements

1. **Multi-project support** — Track expenses across multiple projects (house construction now, car purchase or renovation later).
2. **Simple add form** — Date, category (from project's existing categories or new), description, total_amount, paid_amount, paid_by.
3. **Summary cards + table-first UI** — Total spent, budget vs spent, top category, entry count at top. Searchable/filterable table as the main view. Collapsible charts secondary.
4. **Data migration** — Seed 109 cleaned construction expense rows via SQL migration.
5. **Separate page** — New "Projects" entry in sidebar, not mixed into Income & Expenses.

## Database Schema

### Table: `projects`

```sql
CREATE TABLE public.projects (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name        text        NOT NULL CHECK (char_length(name) <= 100),
    status      text        NOT NULL CHECK (status IN ('active', 'completed')) DEFAULT 'active',
    budget      numeric     CHECK (budget IS NULL OR budget > 0),
    start_date  date        NOT NULL,
    end_date    date        CHECK (end_date IS NULL OR end_date >= start_date),
    is_active   boolean     NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_projects_user_status ON public.projects(user_id, status);

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON public.projects
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

**RLS policies** (4 standard per-operation policies matching existing pattern):
- `select_own`: `auth.uid() = user_id`
- `insert_own`: `auth.uid() = user_id`
- `update_own`: `auth.uid() = user_id` (both USING and WITH CHECK)
- `delete_own`: `auth.uid() = user_id`

### Table: `project_expenses`

```sql
CREATE TABLE public.project_expenses (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   uuid        NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    date         date        NOT NULL,
    category     text        NOT NULL CHECK (char_length(category) <= 50),
    description  text        NOT NULL CHECK (char_length(description) <= 200),
    total_amount numeric     CHECK (total_amount IS NULL OR total_amount >= 0),
    paid_amount  numeric     NOT NULL CHECK (paid_amount >= 0),
    paid_by      text        NOT NULL CHECK (char_length(paid_by) <= 100),
    is_active    boolean     NOT NULL DEFAULT true,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_project_expenses_project_id ON public.project_expenses(project_id);

CREATE TRIGGER trg_project_expenses_updated_at
    BEFORE UPDATE ON public.project_expenses
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

**RLS policies** (join-based, matching `sip_log_funds` pattern):
- `select_own`: `project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid())`
- `insert_own`: same subquery in WITH CHECK
- `update_own`: same subquery in both USING and WITH CHECK
- `delete_own`: same subquery in USING

### Design decisions

- **`total_amount` is nullable**: `NULL` = installment payment (contract total recorded elsewhere). `0` is not used as a sentinel.
- **`is_active` on both tables**: Soft-delete pattern matching `fixed_expenses`. DELETE endpoints set `is_active = false`, never hard delete.
- **Categories are free text**: No category table. The 10 construction categories are seeded with data. New projects define their own. Frontend derives distinct categories from existing expenses.
- **No `user_id` on `project_expenses`**: RLS joins through `project_id -> projects.user_id`. Same proven pattern as `sip_log_funds`.
- **`paid_by` default in app layer**: Default "Saurabh Harak" set in Pydantic model, not DB schema.

## API Design

### Flat routes (matching codebase pattern — no nested resources)

Two routers registered separately in `main.py`:

**`/api/projects` router:**

| Method | Path | Rate Limit | Purpose |
|---|---|---|---|
| GET | `/api/projects` | 60/min | List projects. Query: `?status=active&active=true` |
| POST | `/api/projects` | 30/min | Create project |
| PATCH | `/api/projects/{project_id}` | 30/min | Update project |
| DELETE | `/api/projects/{project_id}` | 10/min | Soft-delete (is_active=false) + audit log |

**`/api/project-expenses` router:**

| Method | Path | Rate Limit | Purpose |
|---|---|---|---|
| GET | `/api/project-expenses` | 60/min | List expenses. Query: `?project_id=X&category=Y&active=true` |
| POST | `/api/project-expenses` | 30/min | Add expense (project_id in request body) |
| PATCH | `/api/project-expenses/{expense_id}` | 30/min | Update expense |
| DELETE | `/api/project-expenses/{expense_id}` | 10/min | Soft-delete + audit log |
| GET | `/api/project-expenses/summary` | 30/min | Aggregated category + monthly totals. Query: `?project_id=X` |

**Path parameters:** `project_id: UUID`, `expense_id: UUID` (matching `precious_metals.py` pattern).

**Response envelope:** `{"data": ...}` for reads, `{"data": ..., "message": ...}` for writes, `{"message": ...}` for deletes. Matches all existing routers.

**Error handling:** Service layer raises `DataNotFoundError` (-> 404) when entity not found or doesn't belong to user. Same pattern as `precious_metals_svc.py`.

### Pydantic Models (in `models.py`)

```python
class ProjectCreate(BaseModel):
    name: str = Field(max_length=100)
    status: Literal["active", "completed"] = "active"
    budget: Optional[float] = Field(None, gt=0)
    start_date: date
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    status: Optional[Literal["active", "completed"]] = None
    budget: Optional[float] = Field(None, gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class ProjectExpenseCreate(BaseModel):
    project_id: str  # UUID as string, matching existing pattern
    date: date
    category: str = Field(max_length=50)
    description: str = Field(max_length=200)
    total_amount: Optional[float] = Field(None, ge=0)
    paid_amount: float = Field(ge=0)
    paid_by: str = Field(default="Saurabh Harak", max_length=100)

class ProjectExpenseUpdate(BaseModel):
    date: Optional[date] = None
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    total_amount: Optional[float] = Field(None, ge=0)
    paid_amount: Optional[float] = Field(None, ge=0)
    paid_by: Optional[str] = Field(None, max_length=100)
```

## Frontend Design

### Navigation

New sidebar entry: **"Projects"** with `Briefcase` icon at position after "Precious Metals", route `/projects`.

Update `NAV_ITEMS` in `constants.ts` and add route in React Router config.

### Page Layout: `Projects.tsx`

```
+----------------------------------------------------------+
| [Project Dropdown: House Construction v]  [+ New Project] |
+----------------------------------------------------------+
| Summary Cards Row                                         |
| [Total Spent]  [Budget vs Spent]  [Top Category]  [#Entries] |
+----------------------------------------------------------+
| [+ Quick Add Expense Form]                                |
| [Category Filter] [Search]                                |
+----------------------------------------------------------+
| Expense Table (main content)                              |
| Date | Category | Description | Total | Paid | Paid By   |
| ...sortable, inline-editable...                           |
+----------------------------------------------------------+
| [v Charts (collapsible)]                                  |
|   Category bar chart  |  Monthly trend line chart         |
+----------------------------------------------------------+
```

### Components

| File | Purpose |
|---|---|
| `pages/Projects.tsx` | Page container, project selector, orchestrates child components |
| `components/projects/ProjectExpenseTable.tsx` | Sortable/filterable expense table with inline edit (pattern from MetalHoldingsTable) |
| `components/projects/ProjectExpenseQuickAdd.tsx` | Quick-add form row (pattern from ExpenseQuickAdd) |
| `components/projects/ProjectSummaryCards.tsx` | 4 metric cards using existing MetricCard component |
| `components/projects/ProjectCharts.tsx` | Collapsible section with Recharts bar + line charts |

### React Query Hooks

| File | Purpose |
|---|---|
| `hooks/useProjects.ts` | CRUD for projects. `useQuery` for list, `useMutation` for create/update/delete. |
| `hooks/useProjectExpenses.ts` | CRUD + summary for project expenses. Queries filtered by `project_id`. |

### Styling

Follow existing app theme from `constants.ts`:
- Background: `#0D1B2A`, Surface: `#132E3D`, Primary: `#00895E`, Accent: `#D4A843`
- No red colors (per user design feedback — prosperity/Vastu colors)
- Use existing component patterns (MetricCard, EmptyState, LoadingState)

## Data Migration

### Migration `009_projects.sql`
- CREATE both tables with all constraints, indexes, triggers, RLS policies
- Idempotent (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`)
- Wrapped in `BEGIN;`/`COMMIT;`

### Migration `010_seed_construction.sql`
- INSERT the "House Construction" project (status: completed, budget: null, start: 2024-11-09, end: 2026-01-03)
- INSERT 109 cleaned expense rows from `construction_expenses_clean.csv`
- Convert `total_amount = 0` rows to `NULL` during insert
- Idempotent (check if project exists before inserting)
- **Note:** This migration is user-specific. It uses a placeholder `user_id` (`'REPLACE_WITH_YOUR_USER_ID'`) that must be replaced with the actual Supabase auth user UUID before running. Get it from Supabase Dashboard > Authentication > Users.

## Files to Create/Modify

### New files:
- `migrations/009_projects.sql` — Schema migration
- `migrations/010_seed_construction.sql` — Data seed
- `backend/app/routers/projects.py` — Projects router
- `backend/app/routers/project_expenses.py` — Project expenses router
- `backend/app/services/projects_svc.py` — Projects service
- `backend/app/services/project_expenses_svc.py` — Project expenses service
- `frontend/src/pages/Projects.tsx` — Projects page
- `frontend/src/components/projects/ProjectExpenseTable.tsx`
- `frontend/src/components/projects/ProjectExpenseQuickAdd.tsx`
- `frontend/src/components/projects/ProjectSummaryCards.tsx`
- `frontend/src/components/projects/ProjectCharts.tsx`
- `frontend/src/hooks/useProjects.ts`
- `frontend/src/hooks/useProjectExpenses.ts`

### Modified files:
- `backend/app/core/models.py` — Add 4 new Pydantic models
- `backend/app/main.py` — Register 2 new routers
- `frontend/src/lib/constants.ts` — Add "Projects" to NAV_ITEMS
- `frontend/src/layouts/Sidebar.tsx` — Already has Briefcase icon, no change needed
- `frontend/src/App.tsx` (or router config) — Add `/projects` route
- `schema.sql` — Add both tables for reference

## Testing Strategy

- Backend: Test CRUD endpoints for both routers, verify RLS isolation, test soft-delete cascade behavior
- Frontend: Verify project selector, expense table rendering, quick-add form, summary computation
- Data: Verify all 109 seed rows load correctly with proper category mapping
