# Money Ledger (Personal Debt Tracker) — Design Spec

**Date:** 2026-04-07
**Status:** Approved
**Scope:** Track money given to and received from people. Contacts list with per-person balance, transaction history with categories and payment methods.

## Requirements

1. **Contacts list** — Add people by name (+ optional phone). See all people with their computed balances at a glance.
2. **Transactions** — Record money given/received with date, amount, category, payment method, and note.
3. **Balance computation** — Per-person: sum(received) - sum(gave). Positive = they owe you. Negative = you owe them.
4. **Summary** — Total given, total received, net balance, people count.
5. **New page** — "Money Ledger" in sidebar with Wallet icon.

## Database Schema

### Table: `ledger_contacts`

```sql
CREATE TABLE IF NOT EXISTS public.ledger_contacts (
    id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name       text        NOT NULL CHECK (char_length(name) <= 100),
    phone      text        CHECK (phone IS NULL OR char_length(phone) <= 15),
    is_active  boolean     NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_ledger_contact_name UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_ledger_contacts_user_active
    ON public.ledger_contacts(user_id, is_active);

CREATE TRIGGER trg_ledger_contacts_updated_at
    BEFORE UPDATE ON public.ledger_contacts
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

RLS: standard 4 policies with `auth.uid() = user_id`.

### Table: `ledger_transactions`

```sql
CREATE TABLE IF NOT EXISTS public.ledger_transactions (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id     uuid        NOT NULL REFERENCES public.ledger_contacts(id) ON DELETE CASCADE,
    direction      text        NOT NULL CHECK (direction IN ('gave', 'received')),
    amount         numeric     NOT NULL CHECK (amount > 0),
    date           date        NOT NULL,
    category       text        NOT NULL CHECK (category IN ('loan', 'borrowed', 'payment', 'advance', 'other')),
    payment_method text        NOT NULL CHECK (payment_method IN ('cash', 'upi', 'bank_transfer', 'other')),
    note           text        CHECK (note IS NULL OR char_length(note) <= 200),
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ledger_transactions_contact_id
    ON public.ledger_transactions(contact_id);

CREATE TRIGGER trg_ledger_transactions_updated_at
    BEFORE UPDATE ON public.ledger_transactions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

RLS: join-based (same as `project_expenses` / `sip_log_funds` pattern):
- `contact_id IN (SELECT id FROM public.ledger_contacts WHERE user_id = auth.uid())`

### Design decisions

- **No `is_active` on transactions** — Hard delete for transactions. Soft-deleting a financial transaction silently changes balances which is confusing. Contacts use soft-delete (`is_active`) since they may have historical value.
- **No `user_id` on transactions** — RLS joins through `contact_id -> ledger_contacts.user_id`.
- **`UNIQUE (user_id, name)` on contacts** — Prevents duplicate contact names per user.
- **Balance computed on read** — `sum(received) - sum(gave)` calculated server-side, not stored.
- **Transactions cascade on contact delete** — If a contact is hard-deleted, all their transactions go too. But contacts use soft-delete, so this only triggers on user account deletion.

## API Design

### Contacts endpoints

| Method | Path | Rate Limit | Purpose |
|---|---|---|---|
| GET | `/api/ledger-contacts` | 60/min | List contacts with computed balances |
| POST | `/api/ledger-contacts` | 30/min | Add contact |
| PATCH | `/api/ledger-contacts/{contact_id}` | 30/min | Update name/phone |
| DELETE | `/api/ledger-contacts/{contact_id}` | 10/min | Soft-delete |
| GET | `/api/ledger-contacts/summary` | 30/min | Total given/received/net/people count |

### Transactions endpoints

| Method | Path | Rate Limit | Purpose |
|---|---|---|---|
| GET | `/api/ledger-txns` | 60/min | List transactions (`?contact_id=X`) |
| POST | `/api/ledger-txns` | 30/min | Add transaction |
| PATCH | `/api/ledger-txns/{txn_id}` | 30/min | Update transaction |
| DELETE | `/api/ledger-txns/{txn_id}` | 10/min | Hard delete |

### Response envelope

Standard `{"data": ...}` / `{"data": ..., "message": ...}` / `{"message": ...}`.

### Balance computation (in contacts list response)

Each contact in the GET response includes computed fields:
```json
{
  "id": "uuid",
  "name": "Rahul",
  "phone": "9876543210",
  "total_gave": 5000,
  "total_received": 2000,
  "balance": 3000,
  "balance_label": "owes you"
}
```

`balance_label`: positive = "owes you", negative = "you owe", zero = "settled".

### Pydantic Models

```python
class LedgerContactCreate(BaseModel):
    name: str = Field(max_length=100)
    phone: Optional[str] = Field(None, max_length=15)

class LedgerContactUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=15)

class LedgerTxnCreate(BaseModel):
    contact_id: str
    direction: Literal["gave", "received"]
    amount: float = Field(gt=0)
    date: date
    category: Literal["loan", "borrowed", "payment", "advance", "other"]
    payment_method: Literal["cash", "upi", "bank_transfer", "other"]
    note: Optional[str] = Field(None, max_length=200)

class LedgerTxnUpdate(BaseModel):
    direction: Optional[Literal["gave", "received"]] = None
    amount: Optional[float] = Field(None, gt=0)
    date: Optional[date] = None
    category: Optional[Literal["loan", "borrowed", "payment", "advance", "other"]] = None
    payment_method: Optional[Literal["cash", "upi", "bank_transfer", "other"]] = None
    note: Optional[str] = Field(None, max_length=200)
```

## Service Layer

**`ledger_contacts_svc.py`:**
- `load_contacts(user_id, access_token, active_only)` — Fetch contacts, compute balances from transactions
- `save_contact(user_id, data, access_token)` — Insert
- `update_contact(contact_id, user_id, data, access_token)` — Update
- `deactivate_contact(contact_id, user_id, access_token)` — Soft-delete
- `compute_summary(user_id, access_token)` — Total given/received/net/people

**`ledger_txns_svc.py`:**
- `load_transactions(user_id, access_token, contact_id)` — Fetch transactions for a contact
- `save_transaction(user_id, data, access_token)` — Insert (verify contact ownership)
- `update_transaction(txn_id, user_id, data, access_token)` — Update (verify ownership via contact)
- `delete_transaction(txn_id, user_id, access_token)` — Hard delete (verify ownership)

## Frontend Design

### Navigation

New sidebar entry: **"Money Ledger"** with `Wallet` icon, positioned after "Projects" (grouping financial tools together).

### Page Layout: `MoneyLedger.tsx`

```
+----------------------------------------------------------+
| Money Ledger                                              |
| Track money given and received                            |
+----------------------------------------------------------+
| Summary Cards (4 cards)                                   |
| [Total Given] [Total Received] [Net Balance] [People]    |
+----------------------------------------------------------+
| [+ Add Person]  [Search...]                               |
+----------------------------------------------------------+
| People List                                               |
| Name       | Given    | Received | Balance          | >  |
| Rahul      | Rs.5,000 | Rs.2,000 | +3,000 owes you  | >  |
| Papa       | Rs.0     | Rs.10,000| -10,000 you owe  | >  |
| Amit       | Rs.1,500 | Rs.1,500 | 0 settled         | >  |
+----------------------------------------------------------+

Clicking a person expands inline:
+----------------------------------------------------------+
| Rahul — Balance: +Rs.3,000 (owes you)                    |
| [+ Add Entry]                                             |
| Date       | Direction | Amount | Category | Method | Note|
| 2026-04-05 | Gave      | 5,000  | Loan     | UPI    | ... |
| 2026-04-07 | Received  | 2,000  | Payment  | Cash   | ... |
+----------------------------------------------------------+
```

### Components

| File | Purpose |
|---|---|
| `pages/MoneyLedger.tsx` | Page container |
| `components/ledger/LedgerSummaryCards.tsx` | 4 metric cards |
| `components/ledger/ContactsList.tsx` | People table with balances + expand |
| `components/ledger/TransactionHistory.tsx` | Inline transaction table per contact |
| `components/ledger/AddContactForm.tsx` | Quick-add person form |
| `components/ledger/AddTxnForm.tsx` | Quick-add transaction form |
| `hooks/useLedgerContacts.ts` | Contacts + summary hook |
| `hooks/useLedgerTxns.ts` | Transactions hook |

### Styling

- Balance positive: `text-[#00895E]` (green) + "owes you"
- Balance negative: `text-[#E5A100]` (amber) + "you owe"
- Balance zero: `text-[#E8ECF1]/40` + "settled"
- No red colors. Indian rupee formatting.

## Files to Create/Modify

### New files:
- `migrations/012_ledger.sql`
- `backend/app/services/ledger_contacts_svc.py`
- `backend/app/services/ledger_txns_svc.py`
- `backend/app/routers/ledger_contacts.py`
- `backend/app/routers/ledger_txns.py`
- `frontend/src/pages/MoneyLedger.tsx`
- `frontend/src/components/ledger/LedgerSummaryCards.tsx`
- `frontend/src/components/ledger/ContactsList.tsx`
- `frontend/src/components/ledger/TransactionHistory.tsx`
- `frontend/src/components/ledger/AddContactForm.tsx`
- `frontend/src/components/ledger/AddTxnForm.tsx`
- `frontend/src/hooks/useLedgerContacts.ts`
- `frontend/src/hooks/useLedgerTxns.ts`

### Modified files:
- `backend/app/core/models.py` — Add 4 Pydantic models
- `backend/app/main.py` — Register 2 routers
- `frontend/src/lib/constants.ts` — Add "Money Ledger" to NAV_ITEMS
- `frontend/src/layouts/Sidebar.tsx` — Add Wallet icon
- `frontend/src/App.tsx` — Add /money-ledger route
- `schema.sql` — Add both tables
