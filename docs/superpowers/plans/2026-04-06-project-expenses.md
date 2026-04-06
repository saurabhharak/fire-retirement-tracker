# Project Expenses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a multi-project expense tracking module (separate from recurring household expenses) with data migration of 109 house construction entries.

**Architecture:** Two new Supabase tables (`projects`, `project_expenses`) with RLS, two FastAPI routers with service layers, a React page with summary cards + filterable table + collapsible charts. Follows existing codebase patterns exactly (flat routes, soft-delete, service layer, React Query hooks).

**Tech Stack:** Supabase PostgreSQL, FastAPI, Pydantic v2, React 19, TanStack React Query v5, Recharts, TailwindCSS 4.2

**Spec:** `docs/superpowers/specs/2026-04-06-project-expenses-design.md`

---

## File Map

### New files:
| File | Responsibility |
|---|---|
| `migrations/009_projects.sql` | Schema: both tables, indexes, triggers, RLS |
| `migrations/010_seed_construction.sql` | Seed 109 construction expenses |
| `backend/app/services/projects_svc.py` | Projects CRUD service |
| `backend/app/services/project_expenses_svc.py` | Project expenses CRUD + summary service |
| `backend/app/routers/projects.py` | Projects API routes |
| `backend/app/routers/project_expenses.py` | Project expenses API routes |
| `frontend/src/hooks/useProjects.ts` | Projects React Query hook |
| `frontend/src/hooks/useProjectExpenses.ts` | Project expenses + summary hook |
| `frontend/src/pages/Projects.tsx` | Main page component |
| `frontend/src/components/projects/ProjectExpenseTable.tsx` | Sortable/filterable table with inline edit |
| `frontend/src/components/projects/ProjectExpenseQuickAdd.tsx` | Quick-add expense form |
| `frontend/src/components/projects/ProjectSummaryCards.tsx` | 4 metric cards |
| `frontend/src/components/projects/ProjectCharts.tsx` | Collapsible bar + line charts |

### Modified files:
| File | Change |
|---|---|
| `backend/app/core/models.py` | Add 4 Pydantic models |
| `backend/app/main.py` | Register 2 new routers |
| `frontend/src/lib/constants.ts` | Add "Projects" to NAV_ITEMS |
| `frontend/src/App.tsx` | Add `/projects` route |
| `frontend/src/layouts/Sidebar.tsx` | Add `Hammer` icon to import and iconMap |
| `schema.sql` | Add both tables for reference |

---

### Task 1: Database Migration — Schema

**Files:**
- Create: `migrations/009_projects.sql`

- [ ] **Step 1: Write the migration SQL**

Create `migrations/009_projects.sql`:

```sql
-- Migration 009: Project expenses module (multi-project expense tracking)
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

-- ============================================================
-- 1. projects table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.projects (
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

CREATE INDEX IF NOT EXISTS idx_projects_user_status
    ON public.projects(user_id, status);

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON public.projects
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.projects
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "insert_own" ON public.projects
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own" ON public.projects
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own" ON public.projects
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- 2. project_expenses table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.project_expenses (
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

CREATE INDEX IF NOT EXISTS idx_project_expenses_project_id
    ON public.project_expenses(project_id);

CREATE TRIGGER trg_project_expenses_updated_at
    BEFORE UPDATE ON public.project_expenses
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS (join-based, same pattern as sip_log_funds)
ALTER TABLE public.project_expenses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.project_expenses
    FOR SELECT USING (
        project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid())
    );
CREATE POLICY "insert_own" ON public.project_expenses
    FOR INSERT WITH CHECK (
        project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid())
    );
CREATE POLICY "update_own" ON public.project_expenses
    FOR UPDATE
    USING (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()))
    WITH CHECK (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()));
CREATE POLICY "delete_own" ON public.project_expenses
    FOR DELETE USING (
        project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid())
    );

COMMIT;
```

- [ ] **Step 2: Update schema.sql reference**

Append the two table definitions (without RLS) to the end of `schema.sql` as section 7 and 8, following the existing numbering pattern (sections 1-6 exist).

- [ ] **Step 3: Commit**

```bash
git add migrations/009_projects.sql schema.sql
git commit -m "feat: add projects and project_expenses schema migration"
```

---

### Task 2: Database Migration — Seed Construction Data

**Files:**
- Create: `migrations/010_seed_construction.sql`
- Reference: `xlsx_extract/construction_expenses_clean.csv`

- [ ] **Step 1: Write the seed migration**

Create `migrations/010_seed_construction.sql`. This inserts the "House Construction" project and all 109 expense rows. Use the cleaned CSV data from `xlsx_extract/construction_expenses_clean.csv`.

The migration must:
- Use a placeholder user_id: `'REPLACE_WITH_YOUR_USER_ID'`
- Create the project with status `'completed'`, start `'2024-11-09'`, end `'2026-01-03'`
- Insert each expense row, converting `total_amount = 0` to `NULL`
- Be wrapped in `BEGIN;`/`COMMIT;`
- Use a DO block to check if the project already exists (idempotent)

```sql
-- Migration 010: Seed house construction expenses
-- IMPORTANT: Replace 'REPLACE_WITH_YOUR_USER_ID' with your actual Supabase user UUID
-- Find it at: Supabase Dashboard > Authentication > Users

BEGIN;

DO $$
DECLARE
    v_user_id uuid := 'REPLACE_WITH_YOUR_USER_ID';
    v_project_id uuid;
BEGIN
    -- Skip if project already exists
    SELECT id INTO v_project_id
    FROM public.projects
    WHERE user_id = v_user_id AND name = 'House Construction';

    IF v_project_id IS NOT NULL THEN
        RAISE NOTICE 'House Construction project already exists, skipping seed';
        RETURN;
    END IF;

    -- Create project
    INSERT INTO public.projects (user_id, name, status, start_date, end_date)
    VALUES (v_user_id, 'House Construction', 'completed', '2024-11-09', '2026-01-03')
    RETURNING id INTO v_project_id;

    -- Insert all 109 expenses (total_amount=0 becomes NULL)
    INSERT INTO public.project_expenses (project_id, date, category, description, total_amount, paid_amount, paid_by) VALUES
    (v_project_id, '2024-11-09', 'Architect & Structural Consulting', 'Advance payment', 50400, 10000, 'Saurabh Harak'),
    (v_project_id, '2024-12-16', 'RCC Contractor', 'Advance Payment', 659999.98, 15000, 'Saurabh Harak'),
    (v_project_id, '2024-12-24', 'RCC Contractor', '2nd installment', NULL, 15000, 'Saurabh Harak'),
    (v_project_id, '2024-12-25', 'Architect & Structural Consulting', '1st stage payment', NULL, 15000, 'Saurabh Harak'),
    (v_project_id, '2024-12-31', 'RCC Contractor', '3rd payment', NULL, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-01-06', 'Materials', '25MM and 40MM Cover block', 1000, 1000, 'Saurabh Harak'),
    (v_project_id, '2025-01-07', 'RCC Contractor', '4th payment', NULL, 40000, 'Saurabh Harak'),
    (v_project_id, '2025-01-14', 'RCC Contractor', '4th payment', NULL, 15000, 'Saurabh Harak'),
    (v_project_id, '2025-01-28', 'RCC Contractor', '5th payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-02-04', 'RCC Contractor', '6th payment', NULL, 50000, 'Saurabh Harak'),
    (v_project_id, '2025-02-11', 'RCC Contractor', '7th payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-02-17', 'RCC Contractor', '8th payment', NULL, 50000, 'Saurabh Harak'),
    (v_project_id, '2025-02-19', 'Electrical', 'Slab electricals', 4625, 4625, 'Saurabh Harak'),
    (v_project_id, '2025-02-23', 'Materials', 'Construction tape', 800, 800, 'Saurabh Harak'),
    (v_project_id, '2025-02-25', 'RCC Contractor', '9th payment', NULL, 40000, 'Saurabh Harak'),
    (v_project_id, '2025-02-28', 'Electrical', 'First slab electricals', 2885, 2885, 'Saurabh Harak'),
    (v_project_id, '2025-03-02', 'Electrical', 'Cable tie', 270, 0, 'Saurabh Harak'),
    (v_project_id, '2025-03-02', 'Electrical', 'Cable tie', NULL, 270, 'Saurabh Harak'),
    (v_project_id, '2025-03-03', 'RCC Contractor', '10th payment', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-03-04', 'RCC Contractor', '12th payment', NULL, 36000, 'Saurabh Harak'),
    (v_project_id, '2025-03-05', 'Architect & Structural Consulting', '1st slab payment', NULL, 15000, 'Saurabh Harak'),
    (v_project_id, '2025-03-11', 'RCC Contractor', '13th payment', NULL, 12000, 'Saurabh Harak'),
    (v_project_id, '2025-03-18', 'RCC Contractor', '13th payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-03-25', 'RCC Contractor', '15th payment', NULL, 50000, 'Saurabh Harak'),
    (v_project_id, '2025-03-31', 'Electrical', 'Second slab electricals', 2425, 2425, 'Saurabh Harak'),
    (v_project_id, '2025-03-31', 'Electrical', 'Electrician payment', 6000, 6000, 'Saurabh Harak'),
    (v_project_id, '2025-04-01', 'RCC Contractor', 'Payment', NULL, 50000, 'Saurabh Harak'),
    (v_project_id, '2025-04-02', 'RCC Contractor', 'Payment', NULL, 16000, 'Saurabh Harak'),
    (v_project_id, '2025-04-03', 'Electrical', '10 Pipes + Edge Fittings', 1280, 0, 'Saurabh Harak'),
    (v_project_id, '2025-04-08', 'RCC Contractor', 'Payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-04-15', 'RCC Contractor', 'Payment', NULL, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-04-22', 'RCC Contractor', 'Payment', NULL, 40000, 'Saurabh Harak'),
    (v_project_id, '2025-04-29', 'RCC Contractor', 'Payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-05-06', 'RCC Contractor', 'Payment', NULL, 35000, 'Saurabh Harak'),
    (v_project_id, '2025-05-13', 'RCC Contractor', 'Payment', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-05-21', 'Windows', 'Windows', 21305, 21305, 'Saurabh Harak'),
    (v_project_id, '2025-05-23', 'Electrical', 'Metal box for ground floor', 7800, 7800, 'Saurabh Harak'),
    (v_project_id, '2025-05-27', 'RCC Contractor', 'Payment', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-06-07', 'Flooring', 'Granite and transportation', 94001, 94001, 'Saurabh Harak'),
    (v_project_id, '2025-06-10', 'RCC Contractor', 'Payment', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-06-11', 'Windows', 'Window Craftsman - First payment', 8000, 8000, 'Saurabh Harak'),
    (v_project_id, '2025-06-11', 'Windows', 'Window grill paint', 580, 580, 'Saurabh Harak'),
    (v_project_id, '2025-06-24', 'RCC Contractor', 'Payment', NULL, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-07-16', 'Windows', 'Steel', 25148, 25148, 'Saurabh Harak'),
    (v_project_id, '2025-07-16', 'Windows', 'Grill labour charges', 7000, 7000, 'Saurabh Harak'),
    (v_project_id, '2025-07-20', 'Electrical', 'Remaining materials', NULL, 2716, 'Saurabh Harak'),
    (v_project_id, '2025-07-21', 'Windows', 'Window Steel Frame', 9630, 9630, 'Saurabh Harak'),
    (v_project_id, '2025-07-21', 'Transport', 'Grill Steel Transport (Vehicle Rent)', 500, 500, 'Saurabh Harak'),
    (v_project_id, '2025-07-24', 'Materials', 'Chicken mesh', 1330, 1330, 'Saurabh Harak'),
    (v_project_id, '2025-07-24', 'Electrical', 'Electrician (Barkale) Labour', 10000, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-07-24', 'Flooring', 'Window grill labour', 10000, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-07-29', 'RCC Contractor', 'Payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-07-31', 'Windows', 'Granite window frame labour payment', 10000, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-08-05', 'RCC Contractor', 'Plaster payment 1', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-08-12', 'RCC Contractor', 'Plaster payment 2', NULL, 25000, 'Saurabh Harak'),
    (v_project_id, '2025-08-19', 'RCC Contractor', 'Payment', NULL, 25000, 'Saurabh Harak'),
    (v_project_id, '2025-08-26', 'RCC Contractor', 'Payment', NULL, 25000, 'Saurabh Harak'),
    (v_project_id, '2025-08-26', 'Plumbing', 'Water tank advance', 35000, 5000, 'Saurabh Harak'),
    (v_project_id, '2025-08-26', 'Plumbing', 'Diverter and flush valve', NULL, 31172, 'Saurabh Harak'),
    (v_project_id, '2025-08-27', 'Architect & Structural Consulting', 'Payment', NULL, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-08-30', 'Flooring', 'Advance payment', 11111, 11111, 'Saurabh Harak'),
    (v_project_id, '2025-09-03', 'Flooring', 'Remaining payment', 77969, 77969, 'Saurabh Harak'),
    (v_project_id, '2025-09-04', 'Plumbing', 'Morya Hardware Store', 1740, 1740, 'Saurabh Harak'),
    (v_project_id, '2025-09-09', 'RCC Contractor', 'Brick Waterproofing (Coba)', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-09-13', 'Plumbing', 'Ankush Plumber - Payment', 5000, 5000, 'Saurabh Harak'),
    (v_project_id, '2025-09-15', 'Flooring', 'Ram Bhai - Tile Labour', 15000, 15000, 'Saurabh Harak'),
    (v_project_id, '2025-09-15', 'Plumbing', 'Toilet seat', 9889, 9889, 'Saurabh Harak'),
    (v_project_id, '2025-09-16', 'RCC Contractor', 'Brick Waterproofing (Coba)', NULL, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-09-21', 'Plumbing', 'Darshan Plumber - 1st Payment', 24000, 24000, 'Saurabh Harak'),
    (v_project_id, '2025-09-21', 'Plumbing', 'Darshan Plumber - 2nd Payment', 45000, 45000, 'Saurabh Harak'),
    (v_project_id, '2025-09-21', 'Plumbing', 'Wash basin and kitchen sink', 9264, 9264, 'Saurabh Harak'),
    (v_project_id, '2025-10-06', 'Flooring', 'Flooring labour payment', 10000, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-10-07', 'RCC Contractor', 'Brick Bed Waterproofing (Coba) final payment', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-10-10', 'Flooring', 'Tiles purchase', 58655, 58655, 'Saurabh Harak'),
    (v_project_id, '2025-10-11', 'Flooring', 'Labour payment', 20000, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-10-13', 'Electrical', 'Wire', 65945, 65945, 'Saurabh Harak'),
    (v_project_id, '2025-10-13', 'Interior', 'POP (Plaster of Paris)', 30000, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-10-16', 'Flooring', 'Labour payment', 30000, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-10-18', 'Electrical', 'Labour payment', 20000, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-10-28', 'Flooring', 'Labour payment', 20000, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-10-28', 'Flooring', 'Granite and porch tiles', 13000, 13000, 'Saurabh Harak'),
    (v_project_id, '2025-11-05', 'Doors & Frames', 'Advance', 156104, 88000, 'Saurabh Harak'),
    (v_project_id, '2025-11-05', 'Windows', 'Advance', 130000, 5000, 'Saurabh Harak'),
    (v_project_id, '2025-11-05', 'Interior', 'POP Bags + Labour Petrol Expense', 350, 350, 'Saurabh Harak'),
    (v_project_id, '2025-11-06', 'Flooring', 'POP (Plaster of Paris)', 15000, 15000, 'Saurabh Harak'),
    (v_project_id, '2025-11-06', 'Interior', 'Gypsum labour payment', 1300, 1300, 'Saurabh Harak'),
    (v_project_id, '2025-11-06', 'Windows', 'First payment', NULL, 62000, 'Saurabh Harak'),
    (v_project_id, '2025-11-07', 'Flooring', 'Tiles labour payment', 40000, 40000, 'Saurabh Harak'),
    (v_project_id, '2025-11-11', 'Doors & Frames', 'Final payment done which was 156104', NULL, 68000, 'Saurabh Harak'),
    (v_project_id, '2025-11-11', 'Transport', 'Door transportation', 1200, 1200, 'Saurabh Harak'),
    (v_project_id, '2025-11-16', 'Flooring', 'Tiles labour payment', 30000, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-11-16', 'Electrical', 'Switch and socket', 39751, 39751, 'Saurabh Harak'),
    (v_project_id, '2025-11-16', 'Flooring', 'Acid wash items', 680, 680, 'Saurabh Harak'),
    (v_project_id, '2025-11-30', 'Plumbing', 'Tap and shower and other items', NULL, 9895, 'Saurabh Harak'),
    (v_project_id, '2025-11-30', 'Electrical', 'Geyser and home made geyser items', 3565, 3565, 'Saurabh Harak'),
    (v_project_id, '2025-11-30', 'Electrical', 'Geyser and home made geyser items', 1001, 1001, 'Saurabh Harak'),
    (v_project_id, '2025-11-30', 'Plumbing', 'Jaguar fittings', NULL, 7754, 'Saurabh Harak'),
    (v_project_id, '2025-12-01', 'Flooring', 'Tiles labour payment', 4178, 4178, 'Saurabh Harak'),
    (v_project_id, '2025-12-04', 'Interior', 'POP payment', 5000, 5000, 'Saurabh Harak'),
    (v_project_id, '2025-12-23', 'Interior', 'Paint payment', 10000, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-12-23', 'Interior', 'Paint labour', 11000, 11000, 'Saurabh Harak'),
    (v_project_id, '2025-12-23', 'Electrical', 'Electrical plates and dimmer', 10304, 10304, 'Saurabh Harak'),
    (v_project_id, '2025-12-23', 'Electrical', 'Lights', 24535, 24535, 'Saurabh Harak'),
    (v_project_id, '2025-12-23', 'Doors & Frames', 'Main door', 38850, 38850, 'Saurabh Harak'),
    (v_project_id, '2026-01-01', 'Doors & Frames', 'Main door accessories', 2000, 2000, 'Saurabh Harak'),
    (v_project_id, '2026-01-01', 'Doors & Frames', 'Main door labour payment', 3689, 3689, 'Saurabh Harak'),
    (v_project_id, '2026-01-01', 'Plumbing', 'Sewage tank labour payment', 7400, 7400, 'Saurabh Harak'),
    (v_project_id, '2026-01-03', 'Interior', 'Paint material payment', 15000, 15000, 'Saurabh Harak'),
    (v_project_id, '2026-01-03', 'Electrical', 'Labour payment', 10000, 10000, 'Saurabh Harak');

END $$;

COMMIT;
```

- [ ] **Step 2: Commit**

```bash
git add migrations/010_seed_construction.sql
git commit -m "feat: add construction expense seed migration (109 rows)"
```

---

### Task 3: Pydantic Models

**Files:**
- Modify: `backend/app/core/models.py`

- [ ] **Step 1: Add the 4 new models**

Append to the end of `backend/app/core/models.py`:

```python
# ---------------------------------------------------------------------------
# Project Expenses Models (multi-project expense tracking)
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    """Create a new project."""
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
    """Partial update for a project."""
    name: Optional[str] = Field(None, max_length=100)
    status: Optional[Literal["active", "completed"]] = None
    budget: Optional[float] = Field(None, gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectExpenseCreate(BaseModel):
    """Create a new project expense."""
    project_id: str
    date: date
    category: str = Field(max_length=50)
    description: str = Field(max_length=200)
    total_amount: Optional[float] = Field(None, ge=0)
    paid_amount: float = Field(ge=0)
    paid_by: str = Field(default="Saurabh Harak", max_length=100)


class ProjectExpenseUpdate(BaseModel):
    """Partial update for a project expense."""
    date: Optional[date] = None
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    total_amount: Optional[float] = Field(None, ge=0)
    paid_amount: Optional[float] = Field(None, ge=0)
    paid_by: Optional[str] = Field(None, max_length=100)
```

- [ ] **Step 2: Verify models parse correctly**

Run: `cd backend && python -c "from app.core.models import ProjectCreate, ProjectUpdate, ProjectExpenseCreate, ProjectExpenseUpdate; print('All models imported OK')"`

Expected: `All models imported OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/models.py
git commit -m "feat: add Pydantic models for projects and project expenses"
```

---

### Task 4: Projects Service Layer

**Files:**
- Create: `backend/app/services/projects_svc.py`

- [ ] **Step 1: Write the projects service**

Create `backend/app/services/projects_svc.py`:

```python
"""Projects CRUD service."""
import logging
from typing import Optional

from app.exceptions import DatabaseError, DataNotFoundError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


def load_projects(
    user_id: str,
    access_token: str,
    status: Optional[str] = None,
    active_only: bool = True,
) -> list[dict]:
    """Fetch all projects for the user."""
    try:
        client = get_user_client(access_token)
        query = client.table("projects").select("*").eq("user_id", user_id)
        if active_only:
            query = query.eq("is_active", True)
        if status:
            query = query.eq("status", status)
        response = query.order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error("Could not load projects: %s", e)
        raise DatabaseError("Could not load projects") from e


def save_project(user_id: str, data: dict, access_token: str) -> Optional[dict]:
    """Create a new project."""
    try:
        client = get_user_client(access_token)
        payload = {**data, "user_id": user_id}
        response = client.table("projects").insert(payload).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Could not save project: %s", e)
        raise DatabaseError("Could not save project") from e


def update_project(
    project_id: str, user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Update a project by ID."""
    try:
        client = get_user_client(access_token)
        response = (
            client.table("projects")
            .update(data)
            .eq("id", project_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Project not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update project: %s", e)
        raise DatabaseError("Could not update project") from e


def deactivate_project(
    project_id: str, user_id: str, access_token: str
) -> None:
    """Soft-delete a project."""
    update_project(project_id, user_id, {"is_active": False}, access_token)
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.services.projects_svc import load_projects, save_project, update_project, deactivate_project; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/projects_svc.py
git commit -m "feat: add projects service layer"
```

---

### Task 5: Project Expenses Service Layer

**Files:**
- Create: `backend/app/services/project_expenses_svc.py`

- [ ] **Step 1: Write the project expenses service**

Create `backend/app/services/project_expenses_svc.py`:

```python
"""Project expenses CRUD + summary service."""
import logging
from typing import Optional

from app.exceptions import DatabaseError, DataNotFoundError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


def _verify_project_ownership(project_id: str, user_id: str, access_token: str) -> None:
    """Check that project_id belongs to user_id. Raises DataNotFoundError if not."""
    client = get_user_client(access_token)
    response = (
        client.table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        raise DataNotFoundError("Project not found")


def load_project_expenses(
    user_id: str,
    access_token: str,
    project_id: Optional[str] = None,
    category: Optional[str] = None,
    active_only: bool = True,
) -> list[dict]:
    """Fetch project expenses. Requires project_id for scoping."""
    try:
        if project_id:
            _verify_project_ownership(project_id, user_id, access_token)

        client = get_user_client(access_token)
        query = client.table("project_expenses").select("*")
        if project_id:
            query = query.eq("project_id", project_id)
        if active_only:
            query = query.eq("is_active", True)
        if category:
            query = query.eq("category", category)
        response = query.order("date", desc=True).execute()
        return response.data or []
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not load project expenses: %s", e)
        raise DatabaseError("Could not load project expenses") from e


def save_project_expense(
    user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Create a new project expense."""
    try:
        _verify_project_ownership(data["project_id"], user_id, access_token)
        client = get_user_client(access_token)
        response = client.table("project_expenses").insert(data).execute()
        return response.data[0] if response.data else None
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not save project expense: %s", e)
        raise DatabaseError("Could not save project expense") from e


def update_project_expense(
    expense_id: str, user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Update a project expense by ID."""
    try:
        client = get_user_client(access_token)
        # RLS on project_expenses already enforces ownership via project_id join
        response = (
            client.table("project_expenses")
            .update(data)
            .eq("id", expense_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Project expense not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update project expense: %s", e)
        raise DatabaseError("Could not update project expense") from e


def deactivate_project_expense(
    expense_id: str, user_id: str, access_token: str
) -> None:
    """Soft-delete a project expense."""
    update_project_expense(expense_id, user_id, {"is_active": False}, access_token)


def compute_project_summary(
    user_id: str, access_token: str, project_id: str
) -> dict:
    """Compute category totals and monthly totals for a project."""
    expenses = load_project_expenses(user_id, access_token, project_id=project_id)

    category_totals: dict[str, float] = {}
    monthly_totals: dict[str, float] = {}
    total_paid = 0.0

    for e in expenses:
        paid = float(e.get("paid_amount", 0))
        total_paid += paid

        cat = e.get("category", "Other")
        category_totals[cat] = category_totals.get(cat, 0) + paid

        month = e.get("date", "")[:7]  # YYYY-MM
        if month:
            monthly_totals[month] = monthly_totals.get(month, 0) + paid

    return {
        "total_paid": round(total_paid, 2),
        "entry_count": len(expenses),
        "category_totals": category_totals,
        "monthly_totals": monthly_totals,
    }
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.services.project_expenses_svc import load_project_expenses, save_project_expense, compute_project_summary; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/project_expenses_svc.py
git commit -m "feat: add project expenses service layer with summary"
```

---

### Task 6: Projects Router

**Files:**
- Create: `backend/app/routers/projects.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the projects router**

Create `backend/app/routers/projects.py`:

```python
"""Projects API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.core.models import ProjectCreate, ProjectUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import projects_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["projects"])


@router.get("/projects")
@limiter.limit("60/minute")
async def list_projects(
    request: Request,
    status: str = Query(None),
    active: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = projects_svc.load_projects(
        user.id, user.access_token, status=status, active_only=active,
    )
    return {"data": entries}


@router.post("/projects")
@limiter.limit("30/minute")
async def create_project(
    request: Request,
    data: ProjectCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = projects_svc.save_project(user.id, data.model_dump(), user.access_token)
    log_audit(user.id, "create_project", {"name": data.name}, user.access_token)
    return {"data": result, "message": "Project created"}


@router.patch("/projects/{project_id}")
@limiter.limit("30/minute")
async def update_project(
    request: Request,
    project_id: UUID,
    data: ProjectUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = projects_svc.update_project(
        str(project_id), user.id, data.model_dump(exclude_unset=True), user.access_token,
    )
    return {"data": result, "message": "Project updated"}


@router.delete("/projects/{project_id}")
@limiter.limit("10/minute")
async def deactivate_project(
    request: Request,
    project_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    projects_svc.deactivate_project(str(project_id), user.id, user.access_token)
    log_audit(user.id, "deactivate_project", {"project_id": str(project_id)}, user.access_token)
    return {"message": "Project deactivated"}
```

- [ ] **Step 2: Register the router in main.py**

Add to `backend/app/main.py` imports and router registration:

After the existing import line:
```python
from app.routers import fire_inputs, income, expenses, sip_log, projections, export, precious_metals
```
Change to:
```python
from app.routers import fire_inputs, income, expenses, sip_log, projections, export, precious_metals, projects
```

After `app.include_router(export.router, prefix="/api")`, add:
```python
app.include_router(projects.router, prefix="/api")
```

- [ ] **Step 3: Verify server starts**

Run: `cd backend && python -c "from app.main import app; print('App loaded, routes:', len(app.routes))"`

Expected: prints route count without errors

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/projects.py backend/app/main.py
git commit -m "feat: add projects API router"
```

---

### Task 7: Project Expenses Router

**Files:**
- Create: `backend/app/routers/project_expenses.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the project expenses router**

Create `backend/app/routers/project_expenses.py`:

```python
"""Project expenses API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.core.models import ProjectExpenseCreate, ProjectExpenseUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import project_expenses_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["project-expenses"])


@router.get("/project-expenses")
@limiter.limit("60/minute")
async def list_project_expenses(
    request: Request,
    project_id: str = Query(None),
    category: str = Query(None),
    active: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = project_expenses_svc.load_project_expenses(
        user.id, user.access_token,
        project_id=project_id, category=category, active_only=active,
    )
    return {"data": entries}


@router.post("/project-expenses")
@limiter.limit("30/minute")
async def create_project_expense(
    request: Request,
    data: ProjectExpenseCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = project_expenses_svc.save_project_expense(
        user.id, data.model_dump(), user.access_token,
    )
    log_audit(user.id, "create_project_expense", {"project_id": data.project_id, "category": data.category}, user.access_token)
    return {"data": result, "message": "Expense added"}


@router.patch("/project-expenses/{expense_id}")
@limiter.limit("30/minute")
async def update_project_expense(
    request: Request,
    expense_id: UUID,
    data: ProjectExpenseUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = project_expenses_svc.update_project_expense(
        str(expense_id), user.id, data.model_dump(exclude_unset=True), user.access_token,
    )
    return {"data": result, "message": "Expense updated"}


@router.delete("/project-expenses/{expense_id}")
@limiter.limit("10/minute")
async def deactivate_project_expense(
    request: Request,
    expense_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    project_expenses_svc.deactivate_project_expense(str(expense_id), user.id, user.access_token)
    log_audit(user.id, "deactivate_project_expense", {"expense_id": str(expense_id)}, user.access_token)
    return {"message": "Expense deactivated"}


@router.get("/project-expenses/summary")
@limiter.limit("30/minute")
async def project_expense_summary(
    request: Request,
    project_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    summary = project_expenses_svc.compute_project_summary(
        user.id, user.access_token, project_id,
    )
    return {"data": summary}
```

- [ ] **Step 2: Register in main.py**

Update the import line to include `project_expenses`:
```python
from app.routers import fire_inputs, income, expenses, sip_log, projections, export, precious_metals, projects, project_expenses
```

Add after the projects router:
```python
app.include_router(project_expenses.router, prefix="/api")
```

- [ ] **Step 3: Verify server loads**

Run: `cd backend && python -c "from app.main import app; print('App loaded, routes:', len(app.routes))"`

Expected: prints route count without errors

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/project_expenses.py backend/app/main.py
git commit -m "feat: add project expenses API router with summary endpoint"
```

---

### Task 8: Frontend Hooks

**Files:**
- Create: `frontend/src/hooks/useProjects.ts`
- Create: `frontend/src/hooks/useProjectExpenses.ts`

- [ ] **Step 1: Write the useProjects hook**

Create `frontend/src/hooks/useProjects.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface Project {
  id: string;
  name: string;
  status: "active" | "completed";
  budget: number | null;
  start_date: string;
  end_date: string | null;
  is_active?: boolean;
  created_at?: string;
}

export function useProjects(filters: { status?: string; active?: boolean } = {}) {
  const queryClient = useQueryClient();
  const active = filters.active ?? true;

  const params = new URLSearchParams();
  params.set("active", String(active));
  if (filters.status) params.set("status", filters.status);

  const query = useQuery({
    queryKey: ["projects", { active, status: filters.status }],
    queryFn: () =>
      api
        .get<{ data: Project[] }>(`/api/projects?${params.toString()}`)
        .then((r) => r.data),
  });

  const save = useMutation({
    mutationFn: (data: Omit<Project, "id" | "is_active" | "created_at">) =>
      api.post("/api/projects", data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Project> }) =>
      api.patch(`/api/projects/${id}`, data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.delete(`/api/projects/${id}`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  return {
    projects: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    deactivate: deactivate.mutateAsync,
  };
}
```

- [ ] **Step 2: Write the useProjectExpenses hook**

Create `frontend/src/hooks/useProjectExpenses.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface ProjectExpense {
  id: string;
  project_id: string;
  date: string;
  category: string;
  description: string;
  total_amount: number | null;
  paid_amount: number;
  paid_by: string;
  is_active?: boolean;
  created_at?: string;
}

export interface ProjectExpenseInput {
  project_id: string;
  date: string;
  category: string;
  description: string;
  total_amount?: number | null;
  paid_amount: number;
  paid_by?: string;
}

export interface ProjectSummary {
  total_paid: number;
  entry_count: number;
  category_totals: Record<string, number>;
  monthly_totals: Record<string, number>;
}

export function useProjectExpenses(
  filters: { projectId?: string; category?: string; active?: boolean } = {}
) {
  const queryClient = useQueryClient();
  const active = filters.active ?? true;

  const params = new URLSearchParams();
  params.set("active", String(active));
  if (filters.projectId) params.set("project_id", filters.projectId);
  if (filters.category) params.set("category", filters.category);

  const query = useQuery({
    queryKey: ["project-expenses", { projectId: filters.projectId, category: filters.category, active }],
    queryFn: () =>
      api
        .get<{ data: ProjectExpense[] }>(`/api/project-expenses?${params.toString()}`)
        .then((r) => r.data),
    enabled: !!filters.projectId,
  });

  const save = useMutation({
    mutationFn: (data: ProjectExpenseInput) =>
      api.post("/api/project-expenses", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["project-summary"] });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ProjectExpense> }) =>
      api.patch(`/api/project-expenses/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["project-summary"] });
    },
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.delete(`/api/project-expenses/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["project-summary"] });
    },
  });

  return {
    expenses: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    deactivate: deactivate.mutateAsync,
  };
}

export function useProjectSummary(projectId?: string) {
  return useQuery({
    queryKey: ["project-summary", projectId],
    queryFn: () =>
      api
        .get<{ data: ProjectSummary }>(`/api/project-expenses/summary?project_id=${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useProjects.ts frontend/src/hooks/useProjectExpenses.ts
git commit -m "feat: add React Query hooks for projects and project expenses"
```

---

### Task 9: ProjectSummaryCards Component

**Files:**
- Create: `frontend/src/components/projects/ProjectSummaryCards.tsx`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/projects/ProjectSummaryCards.tsx`:

```tsx
import { MetricCard } from "../MetricCard";
import type { ProjectSummary } from "../../hooks/useProjectExpenses";
import type { Project } from "../../hooks/useProjects";

interface Props {
  summary: ProjectSummary | undefined;
  project: Project | undefined;
  isLoading: boolean;
}

export function ProjectSummaryCards({ summary, project, isLoading }: Props) {
  if (isLoading || !summary) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 animate-pulse h-20" />
        ))}
      </div>
    );
  }

  const topCategory = Object.entries(summary.category_totals).sort(
    ([, a], [, b]) => b - a
  )[0];

  const budgetDelta =
    project?.budget != null ? project.budget - summary.total_paid : undefined;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <MetricCard
        label="Total Spent"
        value={summary.total_paid}
        color="gold"
      />
      <MetricCard
        label="Budget"
        value={project?.budget ?? 0}
        prefix={project?.budget != null ? "\u20B9" : ""}
        suffix={project?.budget == null ? "" : undefined}
        delta={budgetDelta}
        deltaLabel="remaining"
        color={budgetDelta != null && budgetDelta < 0 ? "warning" : "default"}
      />
      <MetricCard
        label="Top Category"
        value={topCategory ? topCategory[1] : 0}
        suffix={topCategory ? ` (${topCategory[0]})` : ""}
        color="success"
      />
      <MetricCard
        label="Entries"
        value={summary.entry_count}
        prefix=""
        color="default"
      />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/projects/ProjectSummaryCards.tsx
git commit -m "feat: add ProjectSummaryCards component"
```

---

### Task 10: ProjectExpenseQuickAdd Component

**Files:**
- Create: `frontend/src/components/projects/ProjectExpenseQuickAdd.tsx`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/projects/ProjectExpenseQuickAdd.tsx`:

```tsx
import { useState } from "react";
import { Plus } from "lucide-react";
import type { ProjectExpenseInput } from "../../hooks/useProjectExpenses";

interface Props {
  projectId: string;
  categories: string[];
  onSave: (data: ProjectExpenseInput) => Promise<unknown>;
}

const EMPTY_FORM = {
  date: new Date().toISOString().slice(0, 10),
  category: "",
  description: "",
  total_amount: "",
  paid_amount: "",
  paid_by: "Saurabh Harak",
};

export function ProjectExpenseQuickAdd({ projectId, categories, onSave }: Props) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!form.category || !form.description || !form.paid_amount) {
      setError("Category, description, and paid amount are required");
      return;
    }

    setSaving(true);
    try {
      await onSave({
        project_id: projectId,
        date: form.date,
        category: form.category,
        description: form.description,
        total_amount: form.total_amount ? parseFloat(form.total_amount) : null,
        paid_amount: parseFloat(form.paid_amount),
        paid_by: form.paid_by || "Saurabh Harak",
      });
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mb-4">
      <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 items-end">
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Date</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1]"
            />
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Category</label>
            <input
              list="project-categories"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              placeholder="Select or type"
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1]"
            />
            <datalist id="project-categories">
              {categories.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </div>
          <div className="md:col-span-2 lg:col-span-1">
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Description</label>
            <input
              type="text"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="What was this for?"
              maxLength={200}
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1]"
            />
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Total Amt</label>
            <input
              type="number"
              value={form.total_amount}
              onChange={(e) => setForm({ ...form, total_amount: e.target.value })}
              placeholder="Optional"
              min="0"
              step="0.01"
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1]"
            />
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Paid Amt</label>
            <input
              type="number"
              value={form.paid_amount}
              onChange={(e) => setForm({ ...form, paid_amount: e.target.value })}
              placeholder="Amount paid"
              min="0"
              step="0.01"
              required
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1]"
            />
          </div>
          <div>
            <button
              type="submit"
              disabled={saving}
              className="w-full flex items-center justify-center gap-1 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded px-3 py-1.5 text-sm font-medium disabled:opacity-50 transition-colors"
            >
              <Plus size={16} />
              {saving ? "Adding..." : "Add"}
            </button>
          </div>
        </div>
        {error && (
          <p className="text-[#E5A100] text-sm mt-2">{error}</p>
        )}
      </div>
    </form>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/projects/ProjectExpenseQuickAdd.tsx
git commit -m "feat: add ProjectExpenseQuickAdd form component"
```

---

### Task 11: ProjectExpenseTable Component

**Files:**
- Create: `frontend/src/components/projects/ProjectExpenseTable.tsx`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/projects/ProjectExpenseTable.tsx`:

```tsx
import { useState, useMemo } from "react";
import { Pencil, Check, X, Trash2 } from "lucide-react";
import { formatIndian } from "../../lib/formatIndian";
import type { ProjectExpense } from "../../hooks/useProjectExpenses";

interface Props {
  expenses: ProjectExpense[];
  categories: string[];
  onUpdate: (args: { id: string; data: Partial<ProjectExpense> }) => Promise<unknown>;
  onDeactivate: (id: string) => Promise<unknown>;
}

type SortKey = "date" | "category" | "paid_amount";

interface EditForm {
  date: string;
  category: string;
  description: string;
  total_amount: string;
  paid_amount: string;
  paid_by: string;
}

export function ProjectExpenseTable({ expenses, categories, onUpdate, onDeactivate }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDesc, setSortDesc] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState("");
  const [search, setSearch] = useState("");
  const [filterCategory, setFilterCategory] = useState("");

  const sorted = useMemo(() => {
    let filtered = expenses;
    if (search) {
      const q = search.toLowerCase();
      filtered = filtered.filter(
        (e) =>
          e.description.toLowerCase().includes(q) ||
          e.category.toLowerCase().includes(q) ||
          e.paid_by.toLowerCase().includes(q)
      );
    }
    if (filterCategory) {
      filtered = filtered.filter((e) => e.category === filterCategory);
    }
    return [...filtered].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "date") cmp = a.date.localeCompare(b.date);
      else if (sortKey === "category") cmp = a.category.localeCompare(b.category);
      else cmp = a.paid_amount - b.paid_amount;
      return sortDesc ? -cmp : cmp;
    });
  }, [expenses, sortKey, sortDesc, search, filterCategory]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDesc(!sortDesc);
    else { setSortKey(key); setSortDesc(true); }
  };

  const startEdit = (e: ProjectExpense) => {
    setEditingId(e.id);
    setEditForm({
      date: e.date,
      category: e.category,
      description: e.description,
      total_amount: e.total_amount != null ? String(e.total_amount) : "",
      paid_amount: String(e.paid_amount),
      paid_by: e.paid_by,
    });
    setEditError("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditForm(null);
    setEditError("");
  };

  const saveEdit = async () => {
    if (!editForm || !editingId) return;
    setSaving(true);
    setEditError("");
    try {
      await onUpdate({
        id: editingId,
        data: {
          date: editForm.date,
          category: editForm.category,
          description: editForm.description,
          total_amount: editForm.total_amount ? parseFloat(editForm.total_amount) : null,
          paid_amount: parseFloat(editForm.paid_amount),
          paid_by: editForm.paid_by,
        },
      });
      cancelEdit();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const sortIcon = (key: SortKey) =>
    sortKey === key ? (sortDesc ? " \u2193" : " \u2191") : "";

  return (
    <div>
      {/* Filters */}
      <div className="flex gap-3 mb-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search expenses..."
          className="bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1] flex-1 max-w-xs"
        />
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-[#1A3A5C]/30">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#132E3D] text-[#E8ECF1]/60 text-left">
              <th className="px-3 py-2 cursor-pointer" onClick={() => handleSort("date")}>
                Date{sortIcon("date")}
              </th>
              <th className="px-3 py-2 cursor-pointer" onClick={() => handleSort("category")}>
                Category{sortIcon("category")}
              </th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2 text-right">Total</th>
              <th className="px-3 py-2 text-right cursor-pointer" onClick={() => handleSort("paid_amount")}>
                Paid{sortIcon("paid_amount")}
              </th>
              <th className="px-3 py-2">Paid By</th>
              <th className="px-3 py-2 w-20"></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((e) => {
              const isEditing = editingId === e.id;

              if (isEditing && editForm) {
                return (
                  <tr key={e.id} className="bg-[#0D1B2A] border-t border-[#1A3A5C]/20">
                    <td className="px-3 py-1.5">
                      <input type="date" value={editForm.date}
                        onChange={(ev) => setEditForm({ ...editForm, date: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-32" />
                    </td>
                    <td className="px-3 py-1.5">
                      <input list="edit-categories" value={editForm.category}
                        onChange={(ev) => setEditForm({ ...editForm, category: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-full" />
                      <datalist id="edit-categories">
                        {categories.map((c) => <option key={c} value={c} />)}
                      </datalist>
                    </td>
                    <td className="px-3 py-1.5">
                      <input type="text" value={editForm.description} maxLength={200}
                        onChange={(ev) => setEditForm({ ...editForm, description: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-full" />
                    </td>
                    <td className="px-3 py-1.5">
                      <input type="number" value={editForm.total_amount} min="0" step="0.01"
                        onChange={(ev) => setEditForm({ ...editForm, total_amount: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-24 text-right" />
                    </td>
                    <td className="px-3 py-1.5">
                      <input type="number" value={editForm.paid_amount} min="0" step="0.01"
                        onChange={(ev) => setEditForm({ ...editForm, paid_amount: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-24 text-right" />
                    </td>
                    <td className="px-3 py-1.5">
                      <input type="text" value={editForm.paid_by} maxLength={100}
                        onChange={(ev) => setEditForm({ ...editForm, paid_by: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-full" />
                    </td>
                    <td className="px-3 py-1.5">
                      <div className="flex gap-1">
                        <button onClick={saveEdit} disabled={saving}
                          className="p-1 text-[#00895E] hover:bg-[#00895E]/20 rounded">
                          <Check size={14} />
                        </button>
                        <button onClick={cancelEdit}
                          className="p-1 text-[#E8ECF1]/60 hover:bg-[#E8ECF1]/10 rounded">
                          <X size={14} />
                        </button>
                      </div>
                      {editError && <p className="text-[#E5A100] text-xs mt-1">{editError}</p>}
                    </td>
                  </tr>
                );
              }

              return (
                <tr key={e.id} className="border-t border-[#1A3A5C]/20 hover:bg-[#132E3D]/50 text-[#E8ECF1]">
                  <td className="px-3 py-2">{e.date}</td>
                  <td className="px-3 py-2">
                    <span className="bg-[#1A3A5C]/40 px-2 py-0.5 rounded text-xs">{e.category}</span>
                  </td>
                  <td className="px-3 py-2">{e.description}</td>
                  <td className="px-3 py-2 text-right text-[#E8ECF1]/60">
                    {e.total_amount != null ? `\u20B9${formatIndian(e.total_amount)}` : "\u2014"}
                  </td>
                  <td className="px-3 py-2 text-right font-medium">
                    {`\u20B9${formatIndian(e.paid_amount)}`}
                  </td>
                  <td className="px-3 py-2 text-[#E8ECF1]/60">{e.paid_by}</td>
                  <td className="px-3 py-2">
                    <div className="flex gap-1">
                      <button onClick={() => startEdit(e)}
                        className="p-1 text-[#E8ECF1]/40 hover:text-[#D4A843] rounded">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => onDeactivate(e.id)}
                        className="p-1 text-[#E8ECF1]/40 hover:text-[#E5A100] rounded">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {sorted.length === 0 && (
          <p className="text-center text-[#E8ECF1]/40 py-8">No expenses found</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/projects/ProjectExpenseTable.tsx
git commit -m "feat: add ProjectExpenseTable with inline edit, sort, search, filter"
```

---

### Task 12: ProjectCharts Component

**Files:**
- Create: `frontend/src/components/projects/ProjectCharts.tsx`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/projects/ProjectCharts.tsx`:

```tsx
import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid,
} from "recharts";
import { formatIndian } from "../../lib/formatIndian";
import type { ProjectSummary } from "../../hooks/useProjectExpenses";

interface Props {
  summary: ProjectSummary | undefined;
}

export function ProjectCharts({ summary }: Props) {
  const [open, setOpen] = useState(false);

  if (!summary) return null;

  const categoryData = Object.entries(summary.category_totals)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  const monthlyData = Object.entries(summary.monthly_totals)
    .map(([month, value]) => ({ month, value }))
    .sort((a, b) => a.month.localeCompare(b.month));

  return (
    <div className="mt-6">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm text-[#E8ECF1]/60 hover:text-[#E8ECF1] transition-colors mb-3"
      >
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        {open ? "Hide Charts" : "Show Charts"}
      </button>

      {open && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Category Bar Chart */}
          <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
            <h3 className="text-sm font-medium text-[#E8ECF1]/60 mb-3">Spending by Category</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={categoryData} layout="vertical" margin={{ left: 100 }}>
                <XAxis type="number" tickFormatter={(v) => `\u20B9${formatIndian(v)}`}
                  tick={{ fill: "#E8ECF1", opacity: 0.5, fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={90}
                  tick={{ fill: "#E8ECF1", opacity: 0.7, fontSize: 11 }} />
                <Tooltip
                  formatter={(v: number) => [`\u20B9${formatIndian(v)}`, "Spent"]}
                  contentStyle={{ backgroundColor: "#0D1B2A", border: "1px solid #1A3A5C", borderRadius: 8 }}
                  labelStyle={{ color: "#E8ECF1" }}
                  itemStyle={{ color: "#D4A843" }}
                />
                <Bar dataKey="value" fill="#D4A843" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Monthly Line Chart */}
          <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
            <h3 className="text-sm font-medium text-[#E8ECF1]/60 mb-3">Monthly Spending Trend</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1A3A5C" opacity={0.3} />
                <XAxis dataKey="month"
                  tick={{ fill: "#E8ECF1", opacity: 0.5, fontSize: 11 }}
                  tickFormatter={(m) => m.slice(5)} />
                <YAxis tickFormatter={(v) => `${formatIndian(v)}`}
                  tick={{ fill: "#E8ECF1", opacity: 0.5, fontSize: 11 }} />
                <Tooltip
                  formatter={(v: number) => [`\u20B9${formatIndian(v)}`, "Spent"]}
                  contentStyle={{ backgroundColor: "#0D1B2A", border: "1px solid #1A3A5C", borderRadius: 8 }}
                  labelStyle={{ color: "#E8ECF1" }}
                  itemStyle={{ color: "#00895E" }}
                />
                <Line type="monotone" dataKey="value" stroke="#00895E" strokeWidth={2}
                  dot={{ fill: "#00895E", r: 3 }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/projects/ProjectCharts.tsx
git commit -m "feat: add ProjectCharts with collapsible category bar + monthly trend"
```

---

### Task 13: Projects Page + Navigation + Routing

**Files:**
- Create: `frontend/src/pages/Projects.tsx`
- Modify: `frontend/src/lib/constants.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write the Projects page**

Create `frontend/src/pages/Projects.tsx`:

```tsx
import { useState, useMemo } from "react";
import { Plus } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { ProjectSummaryCards } from "../components/projects/ProjectSummaryCards";
import { ProjectExpenseQuickAdd } from "../components/projects/ProjectExpenseQuickAdd";
import { ProjectExpenseTable } from "../components/projects/ProjectExpenseTable";
import { ProjectCharts } from "../components/projects/ProjectCharts";
import { useProjects } from "../hooks/useProjects";
import { useProjectExpenses, useProjectSummary } from "../hooks/useProjectExpenses";

export default function Projects() {
  const { projects, isLoading: projectsLoading, save: saveProject } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectBudget, setNewProjectBudget] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);

  // Auto-select first project
  const activeProjectId = selectedProjectId || projects[0]?.id || "";

  const { expenses, isLoading: expensesLoading, save: saveExpense, update: updateExpense, deactivate: deactivateExpense } =
    useProjectExpenses({ projectId: activeProjectId });

  const { data: summary, isLoading: summaryLoading } = useProjectSummary(activeProjectId);

  const activeProject = projects.find((p) => p.id === activeProjectId);

  const categories = useMemo(() => {
    const cats = new Set(expenses.map((e) => e.category));
    return Array.from(cats).sort();
  }, [expenses]);

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;
    setCreatingProject(true);
    try {
      await saveProject({
        name: newProjectName.trim(),
        status: "active",
        budget: newProjectBudget ? parseFloat(newProjectBudget) : null,
        start_date: new Date().toISOString().slice(0, 10),
        end_date: null,
      });
      setNewProjectName("");
      setNewProjectBudget("");
      setShowNewProject(false);
    } finally {
      setCreatingProject(false);
    }
  };

  if (projectsLoading) return <LoadingState />;

  return (
    <div>
      <PageHeader title="Projects" subtitle="Track expenses for construction, renovation, and other projects" />

      {/* Project selector + New Project */}
      <div className="flex items-center gap-3 mb-6">
        <select
          value={activeProjectId}
          onChange={(e) => setSelectedProjectId(e.target.value)}
          className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded-lg px-4 py-2 text-sm text-[#E8ECF1] min-w-[200px]"
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} {p.status === "completed" ? "(Completed)" : ""}
            </option>
          ))}
        </select>
        <button
          onClick={() => setShowNewProject(!showNewProject)}
          className="flex items-center gap-1 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          New Project
        </button>
      </div>

      {/* New project form */}
      {showNewProject && (
        <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">Project Name</label>
              <input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="e.g. Car Purchase"
                maxLength={100}
                className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
              />
            </div>
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">Budget (optional)</label>
              <input
                type="number"
                value={newProjectBudget}
                onChange={(e) => setNewProjectBudget(e.target.value)}
                placeholder="Total budget"
                min="1"
                className="bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1] w-40"
              />
            </div>
            <button
              onClick={handleCreateProject}
              disabled={creatingProject || !newProjectName.trim()}
              className="bg-[#D4A843] hover:bg-[#D4A843]/80 text-[#0D1B2A] rounded px-4 py-1.5 text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {creatingProject ? "Creating..." : "Create"}
            </button>
          </div>
        </div>
      )}

      {/* No projects state */}
      {projects.length === 0 && !showNewProject && (
        <EmptyState
          title="No projects yet"
          message="Create a project to start tracking expenses"
        />
      )}

      {/* Project content */}
      {activeProjectId && (
        <>
          <ProjectSummaryCards
            summary={summary}
            project={activeProject}
            isLoading={summaryLoading}
          />

          <ProjectExpenseQuickAdd
            projectId={activeProjectId}
            categories={categories}
            onSave={saveExpense}
          />

          {expensesLoading ? (
            <LoadingState />
          ) : (
            <ProjectExpenseTable
              expenses={expenses}
              categories={categories}
              onUpdate={updateExpense}
              onDeactivate={deactivateExpense}
            />
          )}

          <ProjectCharts summary={summary} />
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add to NAV_ITEMS**

In `frontend/src/lib/constants.ts`, add the Projects entry after "Precious Metals" in the `NAV_ITEMS` array:

```typescript
{ path: "/projects", label: "Projects", icon: "Briefcase" },
```

The full `NAV_ITEMS` becomes:
```typescript
export const NAV_ITEMS = [
  { path: "/", label: "Dashboard", icon: "LayoutDashboard" },
  { path: "/income-expenses", label: "Income & Expenses", icon: "Coins" },
  { path: "/precious-metals", label: "Precious Metals", icon: "Gem" },
  { path: "/projects", label: "Projects", icon: "Briefcase" },
  { path: "/fire-settings", label: "FIRE Settings", icon: "Settings" },
  { path: "/fund-allocation", label: "Fund Allocation", icon: "Briefcase" },
  { path: "/growth-projection", label: "Growth Projection", icon: "TrendingUp" },
  { path: "/retirement-analysis", label: "Retirement Analysis", icon: "Shield" },
  { path: "/sip-tracker", label: "SIP Tracker", icon: "ClipboardList" },
  { path: "/settings-privacy", label: "Settings & Privacy", icon: "Lock" },
] as const;
```

Note: "Projects" and "Fund Allocation" both use "Briefcase". To differentiate, change "Projects" to use "Hammer" icon. Add `Hammer` to the Sidebar iconMap import:

In `frontend/src/layouts/Sidebar.tsx`, add `Hammer` to the import from `lucide-react` and to the `iconMap` object.

Update the NAV_ITEMS entry to `icon: "Hammer"`.

- [ ] **Step 3: Add the route to App.tsx**

In `frontend/src/App.tsx`:

Add lazy import after PreciousMetals:
```typescript
const Projects = lazy(() => import("./pages/Projects"));
```

Add route after the precious-metals route:
```typescript
<Route
  path="/projects"
  element={
    <ProtectedRoute>
      <Projects />
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 4: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No type errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Projects.tsx frontend/src/lib/constants.ts frontend/src/layouts/Sidebar.tsx frontend/src/App.tsx
git commit -m "feat: add Projects page with navigation and routing"
```

---

### Task 14: Run Migration and End-to-End Verification

- [ ] **Step 1: Run migration 009 in Supabase SQL Editor**

Copy contents of `migrations/009_projects.sql` to Supabase SQL Editor and execute.

Expected: Both tables created, indexes, triggers, RLS all set up.

- [ ] **Step 2: Get your user_id from Supabase**

Go to Supabase Dashboard > Authentication > Users. Copy your user UUID.

- [ ] **Step 3: Update and run migration 010**

Replace `REPLACE_WITH_YOUR_USER_ID` in `migrations/010_seed_construction.sql` with your actual UUID. Run in Supabase SQL Editor.

Expected: 1 project + 109 expenses inserted.

- [ ] **Step 4: Start backend and verify API**

Run: `cd backend && uvicorn app.main:app --reload`

Test: `curl -s http://localhost:8000/docs | head -5` (should load API docs in dev mode)

- [ ] **Step 5: Start frontend and verify page**

Run: `cd frontend && npm run dev`

Navigate to `/projects`. Verify:
- House Construction project appears in dropdown
- Summary cards show totals
- Table shows 109 entries
- Search and category filter work
- Charts toggle works

- [ ] **Step 6: Test adding a new expense via UI**

Use the quick-add form to add a test expense. Verify it appears in the table and summary updates.

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "feat: project expenses module complete - migration, backend, frontend"
```
