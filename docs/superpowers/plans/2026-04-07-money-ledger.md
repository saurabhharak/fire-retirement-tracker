# Money Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a personal debt tracker — contacts list with per-person balance computation, transaction history with categories and payment methods.

**Architecture:** Two Supabase tables (ledger_contacts + ledger_transactions), two FastAPI routers with service layers, React page with expandable contact rows showing inline transaction history. Follows existing codebase patterns exactly.

**Tech Stack:** Supabase PostgreSQL, FastAPI, Pydantic v2, React 19, TanStack React Query v5, TailwindCSS 4.2

**Spec:** `docs/superpowers/specs/2026-04-07-money-ledger-design.md`

---

## File Map

### New files:
| File | Responsibility |
|---|---|
| `migrations/012_ledger.sql` | Schema: 2 tables, indexes, triggers, RLS |
| `backend/app/services/ledger_contacts_svc.py` | Contacts CRUD + balance computation + summary |
| `backend/app/services/ledger_txns_svc.py` | Transactions CRUD |
| `backend/app/routers/ledger_contacts.py` | Contacts API (5 endpoints) |
| `backend/app/routers/ledger_txns.py` | Transactions API (4 endpoints) |
| `frontend/src/hooks/useLedgerContacts.ts` | Contacts + summary hook |
| `frontend/src/hooks/useLedgerTxns.ts` | Transactions hook |
| `frontend/src/pages/MoneyLedger.tsx` | Main page |
| `frontend/src/components/ledger/LedgerSummaryCards.tsx` | 4 metric cards |
| `frontend/src/components/ledger/ContactsList.tsx` | People table with expandable rows |
| `frontend/src/components/ledger/TransactionHistory.tsx` | Inline transaction table |
| `frontend/src/components/ledger/AddContactForm.tsx` | Add person form |
| `frontend/src/components/ledger/AddTxnForm.tsx` | Add transaction form |

### Modified files:
| File | Change |
|---|---|
| `backend/app/core/models.py` | Add 4 Pydantic models |
| `backend/app/main.py` | Register 2 routers |
| `frontend/src/lib/constants.ts` | Add "Money Ledger" to NAV_ITEMS |
| `frontend/src/layouts/Sidebar.tsx` | Add Wallet icon |
| `frontend/src/App.tsx` | Add /money-ledger route |
| `schema.sql` | Add 2 tables |

---

### Task 1: Database Migration

**Files:**
- Create: `migrations/012_ledger.sql`
- Modify: `schema.sql`

- [ ] **Step 1: Write the migration**

Create `migrations/012_ledger.sql` with the exact SQL from the spec — 2 tables, indexes, triggers, RLS. Use `BEGIN;`/`COMMIT;`, `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`.

Key points:
- `ledger_contacts`: user_id FK, name NOT NULL with char_length CHECK, phone optional, is_active, UNIQUE(user_id, name)
- `ledger_transactions`: contact_id FK (CASCADE), direction CHECK IN ('gave','received'), amount > 0, category/payment_method with CHECK enums, NO is_active (hard delete)
- RLS: standard 4 policies on contacts, join-based on transactions
- Indexes: `idx_ledger_contacts_user_active`, `idx_ledger_transactions_contact_id`

- [ ] **Step 2: Update schema.sql**
- [ ] **Step 3: Commit**

---

### Task 2: Pydantic Models

**Files:**
- Modify: `backend/app/core/models.py`

- [ ] **Step 1: Add 4 models**

Append to `models.py`:
- `LedgerContactCreate`: name (max_length=100), phone (Optional, max_length=15)
- `LedgerContactUpdate`: all Optional
- `LedgerTxnCreate`: contact_id (str), direction (Literal gave/received), amount (gt=0), date, category (Literal), payment_method (Literal), note (Optional, max_length=200)
- `LedgerTxnUpdate`: all Optional

- [ ] **Step 2: Verify import**
- [ ] **Step 3: Commit**

---

### Task 3: Backend Services + Routers

**Files:**
- Create: `backend/app/services/ledger_contacts_svc.py`
- Create: `backend/app/services/ledger_txns_svc.py`
- Create: `backend/app/routers/ledger_contacts.py`
- Create: `backend/app/routers/ledger_txns.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write contacts service**

`ledger_contacts_svc.py` — Follow `expenses_svc.py` pattern:
- `load_contacts(user_id, access_token, active_only)` — Fetch contacts, then for each contact compute balance by querying their transactions. Return contacts with `total_gave`, `total_received`, `balance`, `balance_label`.
- `save_contact(user_id, data, access_token)` — Insert with user_id
- `update_contact(contact_id, user_id, data, access_token)` — Update
- `deactivate_contact(contact_id, user_id, access_token)` — Set is_active=false
- `compute_summary(user_id, access_token)` — Aggregate: total_gave, total_received, net_balance, people_count

Balance logic: For each contact, query `ledger_transactions` grouped by direction. `balance = sum(received) - sum(gave)`. `balance_label`: positive = "owes you", negative = "you owe", zero = "settled".

- [ ] **Step 2: Write transactions service**

`ledger_txns_svc.py`:
- `load_transactions(user_id, access_token, contact_id)` — Verify contact ownership, fetch transactions ordered by date desc
- `save_transaction(user_id, data, access_token)` — Verify contact ownership, insert. Serialize dates.
- `update_transaction(txn_id, user_id, data, access_token)` — Verify ownership via contact join, update. Serialize dates.
- `delete_transaction(txn_id, user_id, access_token)` — Verify ownership, HARD delete (not soft-delete)

- [ ] **Step 3: Write contacts router**

`ledger_contacts.py` — 5 endpoints:
- `GET /ledger-contacts` (60/min) — list with balances
- `POST /ledger-contacts` (30/min) — create + audit
- `PATCH /ledger-contacts/{contact_id}` (30/min) — update + audit
- `DELETE /ledger-contacts/{contact_id}` (10/min) — soft-delete + audit
- `GET /ledger-contacts/summary` (30/min) — totals

NOTE: Place `/summary` route BEFORE `/{contact_id}` to avoid FastAPI path shadowing.

- [ ] **Step 4: Write transactions router**

`ledger_txns.py` — 4 endpoints:
- `GET /ledger-txns` (60/min) — list (?contact_id=X)
- `POST /ledger-txns` (30/min) — create + audit
- `PATCH /ledger-txns/{txn_id}` (30/min) — update + audit
- `DELETE /ledger-txns/{txn_id}` (10/min) — hard delete + audit

- [ ] **Step 5: Register routers in main.py**

Add both routers with `prefix="/api"`.

- [ ] **Step 6: Verify**

`python -c "from app.main import app; print('OK, routes:', len(app.routes))"`

- [ ] **Step 7: Commit** (4 separate commits: models, services, routers, main.py)

---

### Task 4: Frontend Hooks

**Files:**
- Create: `frontend/src/hooks/useLedgerContacts.ts`
- Create: `frontend/src/hooks/useLedgerTxns.ts`

- [ ] **Step 1: Write contacts hook**

`useLedgerContacts.ts`:
- Types: `LedgerContact` (id, name, phone, total_gave, total_received, balance, balance_label), `LedgerSummary`
- `useQuery` for contacts list (queryKey: ["ledger-contacts"])
- `useQuery` for summary (queryKey: ["ledger-summary"])
- `useMutation` for save, update, deactivate — invalidate both contacts + summary

- [ ] **Step 2: Write transactions hook**

`useLedgerTxns.ts`:
- Types: `LedgerTxn` (id, contact_id, direction, amount, date, category, payment_method, note)
- `useQuery` for transactions (queryKey: ["ledger-txns", contactId], enabled: !!contactId)
- `useMutation` for save, update, delete — invalidate txns + contacts + summary

- [ ] **Step 3: Commit**

---

### Task 5: Frontend Components

**Files:**
- Create: `frontend/src/components/ledger/LedgerSummaryCards.tsx`
- Create: `frontend/src/components/ledger/AddContactForm.tsx`
- Create: `frontend/src/components/ledger/AddTxnForm.tsx`
- Create: `frontend/src/components/ledger/TransactionHistory.tsx`
- Create: `frontend/src/components/ledger/ContactsList.tsx`

- [ ] **Step 1: LedgerSummaryCards** — 4 MetricCards: Total Given, Total Received, Net Balance (green/amber based on sign), People count

- [ ] **Step 2: AddContactForm** — Name + phone inputs with proper `<label>` elements, `htmlFor`/`id` pairs

- [ ] **Step 3: AddTxnForm** — Date (lazy init), direction toggle (gave/received), amount, category select, payment method select, note (`autoComplete="off"`). All with labels.

- [ ] **Step 4: TransactionHistory** — Table with date, direction, amount, category, method, note. Direction "Gave" in amber, "Received" in green. `tabular-nums` on amounts. Delete button with `window.confirm()`. Loading state while fetching.

- [ ] **Step 5: ContactsList** — Table with Name, Given, Received, Balance columns. Full row clickable to expand. `aria-expanded` + `aria-label` on rows. Balance colors: green "owes you", amber "you owe", `text-[#E8ECF1]/60` "settled". `tabular-nums` on amounts. `React.memo` on individual rows. Expanded row shows `TransactionHistory` + `AddTxnForm` inline.

UX review fixes incorporated:
- All icon buttons have `aria-label`
- Expandable rows have `aria-expanded`
- Forms have proper `<label>` elements
- `window.confirm()` before contact delete
- `formatRupees()` for all currency (not "Rs.")
- Settled balance uses `/60` opacity (not `/40`)
- Net Balance card: green when positive, amber when negative
- `autoComplete="off"` on note field
- Lazy state init for date default

- [ ] **Step 6: Commit**

---

### Task 6: Page + Navigation + Routing

**Files:**
- Create: `frontend/src/pages/MoneyLedger.tsx`
- Modify: `frontend/src/lib/constants.ts`
- Modify: `frontend/src/layouts/Sidebar.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: MoneyLedger page** — PageHeader, SummaryCards, AddContactForm, search input, ContactsList. Loading/empty states.

- [ ] **Step 2: NAV_ITEMS** — Add `{ path: "/money-ledger", label: "Money Ledger", icon: "Wallet" }` after Projects

- [ ] **Step 3: Sidebar** — Add `Wallet` to lucide-react import and iconMap

- [ ] **Step 4: App.tsx** — Lazy import + ProtectedRoute for `/money-ledger`

- [ ] **Step 5: Verify TypeScript** — `npx tsc --noEmit`

- [ ] **Step 6: Commit**

---

### Task 7: Run Migration + E2E Verification

- [ ] **Step 1: Run migration 012 in Supabase SQL Editor**
- [ ] **Step 2: Start backend + frontend**
- [ ] **Step 3: Test full flow** — Add person, add transactions, verify balances, expand/collapse, delete transaction, verify balance updates
- [ ] **Step 4: Push to GitHub**
