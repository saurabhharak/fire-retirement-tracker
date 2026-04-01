# Expense Management Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Income & Expenses page into a daily-use expense tracker with month navigation, owner filtering, tabbed views (Fixed/One-time/Income), quick-add form, per-owner totals, and expense editing.

**Architecture:** Add `expense_month`/`expense_year` columns to `fixed_expenses` for one-time date tracking. Add filter query params to the backend API. Decompose the 734-line monolithic frontend component into 10+ focused components with tab-based navigation and client-side filtering.

**Tech Stack:** FastAPI (backend), React + TypeScript + Tailwind (frontend), Supabase PostgreSQL (database)

---

## File Structure

### Backend (modify existing)
```
backend/app/core/models.py              -- Add expense_month, expense_year to models
backend/app/routers/expenses.py         -- Add filter query params (owner, frequency, month, year)
backend/app/services/expenses_svc.py    -- Add filter chain to load_fixed_expenses
```

### Frontend (new components + modify existing)
```
frontend/src/pages/IncomeExpenses.tsx                    -- Rewrite: thin orchestrator with tabs
frontend/src/components/expenses/MonthNavigator.tsx       -- Month/year selector with arrows
frontend/src/components/expenses/OwnerFilter.tsx          -- Filter pills: All|You|Wife|Household
frontend/src/components/expenses/ExpenseTabs.tsx          -- Tab bar: All|Fixed|One-time|Income
frontend/src/components/expenses/FinancialSummary.tsx     -- Top metric cards (extracted)
frontend/src/components/expenses/MoneyFlowChart.tsx       -- Pie chart (extracted)
frontend/src/components/expenses/ExpenseTable.tsx         -- Filterable expense table with edit
frontend/src/components/expenses/ExpenseQuickAdd.tsx      -- Always-visible inline add form
frontend/src/components/expenses/IncomeLog.tsx            -- Income table (extracted)
frontend/src/components/expenses/OwnerTotalsBar.tsx       -- Per-owner total strip
frontend/src/hooks/useExpenses.ts                        -- Add filter params to hook
frontend/src/lib/expenseUtils.ts                         -- Add month-aware helpers
```

### Database (migration SQL)
```
migrations/005_expense_month_year.sql   -- Add columns + backfill
```

---

### Task 1: Database Migration — Add expense_month/expense_year columns

**Files:**
- Create: `migrations/005_expense_month_year.sql`

- [ ] **Step 1: Create migration SQL**

```sql
-- Migration 005: Add month/year tracking for one-time expenses
-- Run in Supabase SQL Editor

-- Add expense_month and expense_year columns
ALTER TABLE public.fixed_expenses
  ADD COLUMN IF NOT EXISTS expense_month int CHECK (expense_month >= 1 AND expense_month <= 12),
  ADD COLUMN IF NOT EXISTS expense_year  int CHECK (expense_year >= 2020 AND expense_year <= 2100);

-- Add index for month/year filtering
CREATE INDEX IF NOT EXISTS idx_fixed_expenses_month_year
  ON public.fixed_expenses(user_id, expense_year, expense_month);

-- Backfill: derive month/year from created_at for existing one-time expenses
UPDATE public.fixed_expenses
SET expense_month = EXTRACT(MONTH FROM created_at)::int,
    expense_year  = EXTRACT(YEAR FROM created_at)::int
WHERE frequency = 'one-time'
  AND expense_month IS NULL;

-- Verify owner column exists (was added earlier via direct SQL)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'fixed_expenses' AND column_name = 'owner'
  ) THEN
    ALTER TABLE public.fixed_expenses
      ADD COLUMN owner text NOT NULL DEFAULT 'household'
      CHECK (owner IN ('you', 'wife', 'household'));
  END IF;
END $$;
```

- [ ] **Step 2: User runs migration in Supabase SQL Editor**

- [ ] **Step 3: Commit migration file**

```bash
git add migrations/005_expense_month_year.sql
git commit -m "feat: add expense_month/year columns for one-time expense tracking"
```

---

### Task 2: Backend — Update Pydantic models

**Files:**
- Modify: `backend/app/core/models.py`

- [ ] **Step 1: Add expense_month/year to FixedExpense model**

Add `expense_month` and `expense_year` fields to both `FixedExpense` and `FixedExpenseUpdate`:

```python
from typing import Optional

class FixedExpense(BaseModel):
    name: str = Field(max_length=100)
    amount: float = Field(gt=0)
    frequency: Literal["monthly", "quarterly", "yearly", "one-time"]
    owner: str = Field(default="household", max_length=50)
    expense_month: Optional[int] = Field(None, ge=1, le=12)
    expense_year: Optional[int] = Field(None, ge=2020, le=2100)

class FixedExpenseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    amount: Optional[float] = Field(None, gt=0)
    frequency: Optional[Literal["monthly", "quarterly", "yearly", "one-time"]] = None
    is_active: Optional[bool] = None
    owner: Optional[str] = None
    expense_month: Optional[int] = Field(None, ge=1, le=12)
    expense_year: Optional[int] = Field(None, ge=2020, le=2100)
```

- [ ] **Step 2: Verify backend compiles**

```bash
cd backend && python -c "from app.core.models import FixedExpense, FixedExpenseUpdate; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/models.py
git commit -m "feat(backend): add expense_month/year to Pydantic models"
```

---

### Task 3: Backend — Add filter params to expenses API

**Files:**
- Modify: `backend/app/routers/expenses.py`
- Modify: `backend/app/services/expenses_svc.py`

- [ ] **Step 1: Update router with filter query params**

```python
from typing import Optional

@router.get("/expenses")
@limiter.limit("60/minute")
def list_expenses(
    request: Request,
    active: bool = Query(True),
    owner: Optional[str] = Query(None),
    frequency: Optional[str] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020, le=2100),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = expenses_svc.load_fixed_expenses(
        user.id, user.access_token,
        active_only=active, owner=owner, frequency=frequency,
        month=month, year=year,
    )
    return {"data": entries}
```

- [ ] **Step 2: Update service with filter chain**

```python
def load_fixed_expenses(
    user_id: str, access_token: str,
    active_only: bool = True,
    owner: str = None,
    frequency: str = None,
    month: int = None,
    year: int = None,
) -> list[dict]:
    try:
        client = get_user_client(access_token)
        query = client.table("fixed_expenses").select("*").eq("user_id", user_id)
        if active_only:
            query = query.eq("is_active", True)
        if owner:
            query = query.eq("owner", owner)
        if frequency:
            query = query.eq("frequency", frequency)
        # Month/year filter: show recurring always + one-time for specific month
        if month and year:
            query = query.or_(
                f"frequency.neq.one-time,and(expense_month.eq.{month},expense_year.eq.{year})"
            )
        response = query.order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error("Could not load expenses: %s", e)
        raise DatabaseError("Could not load expenses") from e
```

- [ ] **Step 3: Verify backend starts and /expenses responds**

```bash
cd backend && python -c "from app.main import app; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/expenses.py backend/app/services/expenses_svc.py
git commit -m "feat(backend): add owner/frequency/month/year filters to expenses API"
```

---

### Task 4: Frontend — Update useExpenses hook with filters

**Files:**
- Modify: `frontend/src/hooks/useExpenses.ts`

- [ ] **Step 1: Add filter params to useExpenses**

```typescript
interface ExpenseFilters {
  active?: boolean;
  owner?: string;
  frequency?: string;
  month?: number;
  year?: number;
}

export function useExpenses(filters: ExpenseFilters = {}) {
  const queryClient = useQueryClient();

  const params = new URLSearchParams();
  if (filters.active !== undefined) params.set("active", String(filters.active));
  if (filters.owner) params.set("owner", filters.owner);
  if (filters.frequency) params.set("frequency", filters.frequency);
  if (filters.month) params.set("month", String(filters.month));
  if (filters.year) params.set("year", String(filters.year));

  const query = useQuery({
    queryKey: ["expenses", filters],
    queryFn: () => api.get<{ data: any[] }>(`/api/expenses?${params}`).then(r => r.data),
  });

  // ... mutations stay the same
}
```

- [ ] **Step 2: Update expenseUtils with month-aware helpers**

Add to `frontend/src/lib/expenseUtils.ts`:

```typescript
export function isExpenseInMonth(
  expense: { frequency: string; expense_month?: number; expense_year?: number },
  month: number, year: number
): boolean {
  if (expense.frequency !== "one-time") return true;
  return expense.expense_month === month && expense.expense_year === year;
}

export function getExpenseAmountForMonth(amount: number, frequency: string): number {
  switch (frequency) {
    case "quarterly": return amount / 3;
    case "yearly": return amount / 12;
    case "one-time": return amount;
    default: return amount;
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useExpenses.ts frontend/src/lib/expenseUtils.ts
git commit -m "feat(frontend): add filter params to useExpenses hook + month-aware utils"
```

---

### Task 5: Frontend — Create expense sub-components

**Files:**
- Create: `frontend/src/components/expenses/MonthNavigator.tsx`
- Create: `frontend/src/components/expenses/OwnerFilter.tsx`
- Create: `frontend/src/components/expenses/ExpenseTabs.tsx`
- Create: `frontend/src/components/expenses/ExpenseQuickAdd.tsx`
- Create: `frontend/src/components/expenses/ExpenseTable.tsx`
- Create: `frontend/src/components/expenses/OwnerTotalsBar.tsx`
- Create: `frontend/src/components/expenses/FinancialSummary.tsx`
- Create: `frontend/src/components/expenses/MoneyFlowChart.tsx`
- Create: `frontend/src/components/expenses/IncomeLog.tsx`

Each component should be a focused, single-responsibility React component using Tailwind for styling and the prosperity theme colors.

- [ ] **Step 1: Create components directory and all 9 component files**

Each component receives props from the parent page. No component fetches data directly — all data flows through the parent via hooks.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/expenses/
git commit -m "feat(frontend): create expense sub-components (9 files)"
```

---

### Task 6: Frontend — Rewrite IncomeExpenses page

**Files:**
- Modify: `frontend/src/pages/IncomeExpenses.tsx`

- [ ] **Step 1: Rewrite page as thin orchestrator**

The page manages state (selected month, active tab, owner filter) and composes the sub-components. It uses `useExpenses` with filters, `useIncome`, and `useFireInputs` hooks.

Layout:
1. MonthNavigator + OwnerFilter (sticky top)
2. FinancialSummary (metric cards)
3. MoneyFlowChart (pie chart)
4. ExpenseQuickAdd (always visible)
5. ExpenseTabs → ExpenseTable or IncomeLog based on active tab
6. OwnerTotalsBar (bottom of expense section)

- [ ] **Step 2: Verify TypeScript + dev server**

```bash
cd frontend && npx tsc --noEmit && npm run dev
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/IncomeExpenses.tsx
git commit -m "feat(frontend): rewrite IncomeExpenses as tabbed expense tracker with month nav"
```

---

### Task 7: Testing + Final verification

- [ ] **Step 1: Run backend tests**

```bash
cd backend && python -m pytest tests/unit/ -v
```

- [ ] **Step 2: Run frontend tests**

```bash
cd frontend && npm test
```

- [ ] **Step 3: Build frontend for production**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Push**

```bash
git push origin master
```

---

## Summary of Changes

| Layer | Files Changed | What |
|---|---|---|
| Database | 1 migration | Add expense_month/year columns |
| Backend models | 1 file | Add fields to FixedExpense/FixedExpenseUpdate |
| Backend API | 2 files | Add filter query params + filter chain |
| Frontend hooks | 1 file | Filter-aware useExpenses |
| Frontend utils | 1 file | Month-aware helpers |
| Frontend components | 9 new files | Decomposed sub-components |
| Frontend page | 1 rewrite | Thin orchestrator with tabs |
| **Total** | **16 files** | |
