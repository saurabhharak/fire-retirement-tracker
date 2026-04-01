# Phase 2: React Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready React SPA that connects to the FastAPI backend (Phase 1), implements all 8 Stitch screen designs, and is deployable on Vercel.

**Architecture:** React + Vite SPA with Tailwind CSS + shadcn/ui components. TanStack Query for data fetching with caching. Supabase JS client for auth (OTP + password). React Router for navigation. Recharts for financial charts. All data flows through FastAPI `/api/*` endpoints.

**Tech Stack:** React 18+, Vite, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Recharts, Supabase JS, React Router v6

**Design Reference:** Stitch designs in `stitch-designs/` directory (8 screens)

---

## File Structure

```
frontend/
├── public/
│   ├── favicon.svg
│   └── manifest.json
├── src/
│   ├── main.tsx                    # Entry point
│   ├── App.tsx                     # Router + providers
│   ├── vite-env.d.ts
│   │
│   ├── lib/
│   │   ├── supabase.ts            # Supabase client init
│   │   ├── api.ts                 # Fetch wrapper for FastAPI (auth header injection)
│   │   ├── formatIndian.ts        # Indian number formatting (port of Python)
│   │   ├── constants.ts           # Colors, fund names, SWR rates
│   │   └── queryClient.ts         # TanStack Query client config
│   │
│   ├── hooks/
│   │   ├── useAuth.ts             # Login, logout, OTP, session state
│   │   ├── useFireInputs.ts       # GET/PUT fire-inputs
│   │   ├── useIncome.ts           # GET/POST/DELETE income
│   │   ├── useExpenses.ts         # GET/POST/PATCH/DELETE expenses
│   │   ├── useSipLog.ts           # GET/POST sip-log
│   │   └── useProjections.ts     # GET projections (growth, retirement, funds, sips)
│   │
│   ├── components/
│   │   ├── ui/                    # shadcn/ui primitives (card, button, input, etc.)
│   │   ├── MetricCard.tsx         # Reusable metric display card
│   │   ├── DataTable.tsx          # Styled table with Indian formatting
│   │   ├── ProsperityChart.tsx    # Recharts wrapper with prosperity theme
│   │   ├── PageHeader.tsx         # Page title with icon
│   │   ├── LoadingState.tsx       # Skeleton/spinner
│   │   └── EmptyState.tsx         # No data CTA
│   │
│   ├── layouts/
│   │   ├── AppLayout.tsx          # Sidebar + main content (authenticated)
│   │   ├── AuthLayout.tsx         # Login page layout (unauthenticated)
│   │   └── Sidebar.tsx            # Navigation sidebar
│   │
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── IncomeExpenses.tsx
│   │   ├── FireSettings.tsx
│   │   ├── FundAllocation.tsx
│   │   ├── GrowthProjection.tsx
│   │   ├── RetirementAnalysis.tsx
│   │   ├── SipTracker.tsx
│   │   └── SettingsPrivacy.tsx
│   │
│   └── styles/
│       └── globals.css            # Tailwind base + prosperity theme
│
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.app.json
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.js
└── .env.example
```

---

### Task 1: Scaffold React + Vite + Tailwind + shadcn/ui

**Files:** All config files + src/main.tsx + src/App.tsx + styles/globals.css

- [ ] **Step 1: Create Vite project**

```bash
cd C:\Projects\fire-retirement-tracker
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

- [ ] **Step 2: Install core dependencies**

```bash
npm install @tanstack/react-query @supabase/supabase-js react-router-dom recharts
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 3: Initialize shadcn/ui**

```bash
npx shadcn@latest init
# Select: TypeScript, Default style, CSS variables, Tailwind CSS
```

- [ ] **Step 4: Create tailwind.config.ts with prosperity theme**

```typescript
import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        prosperity: {
          green: "#00895E",
          gold: "#D4A843",
          blue: "#1A3A5C",
          navy: "#0D1B2A",
          teal: "#132E3D",
          silver: "#E8ECF1",
          success: "#2E8B57",
          warning: "#E5A100",
          error: "#C45B5B",
        },
      },
      fontFamily: {
        headline: ["Inter", "sans-serif"],
        body: ["DM Sans", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 5: Create globals.css**

```css
@import "tailwindcss";

@layer base {
  :root {
    --background: 210 50% 7%;
    --foreground: 220 30% 93%;
  }
  body {
    @apply bg-prosperity-navy text-prosperity-silver font-body;
    font-variant-numeric: tabular-nums;
  }
}
```

- [ ] **Step 6: Create .env.example**

```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 7: Verify dev server runs**

```bash
npm run dev
# Should open http://localhost:5173
```

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold React + Vite + Tailwind + shadcn/ui"
```

---

### Task 2: Lib modules (API client, Supabase, formatting, constants)

**Files:** src/lib/*.ts

- [ ] **Step 1: Create supabase.ts**

```typescript
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseKey);
```

- [ ] **Step 2: Create api.ts (fetch wrapper with JWT injection)**

```typescript
import { supabase } from "./supabase";

const API_URL = import.meta.env.VITE_API_URL;

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}
```

- [ ] **Step 3: Create formatIndian.ts**

```typescript
export function formatIndian(amount: number): string {
  const isNeg = amount < 0;
  const n = Math.round(Math.abs(amount));
  const s = String(n);

  if (s.length <= 3) return isNeg ? `-${s}` : s;

  const last3 = s.slice(-3);
  let remaining = s.slice(0, -3);
  const groups: string[] = [];

  while (remaining.length > 2) {
    groups.push(remaining.slice(-2));
    remaining = remaining.slice(0, -2);
  }
  if (remaining) groups.push(remaining);
  groups.reverse();

  const result = groups.join(",") + "," + last3;
  return isNeg ? `-${result}` : result;
}
```

- [ ] **Step 4: Create constants.ts**

```typescript
export const COLORS = {
  primary: "#00895E",
  secondary: "#D4A843",
  tertiary: "#1A3A5C",
  background: "#0D1B2A",
  surface: "#132E3D",
  text: "#E8ECF1",
  success: "#2E8B57",
  warning: "#E5A100",
  error: "#C45B5B",
} as const;

export const NAV_ITEMS = [
  { path: "/", label: "Dashboard", icon: "LayoutDashboard" },
  { path: "/income-expenses", label: "Income & Expenses", icon: "Coins" },
  { path: "/fire-settings", label: "FIRE Settings", icon: "Settings" },
  { path: "/fund-allocation", label: "Fund Allocation", icon: "Briefcase" },
  { path: "/growth-projection", label: "Growth Projection", icon: "TrendingUp" },
  { path: "/retirement-analysis", label: "Retirement Analysis", icon: "Shield" },
  { path: "/sip-tracker", label: "SIP Tracker", icon: "ClipboardList" },
  { path: "/settings-privacy", label: "Settings & Privacy", icon: "Lock" },
] as const;
```

- [ ] **Step 5: Create queryClient.ts**

```typescript
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,     // 5 minutes
      gcTime: 30 * 60 * 1000,        // 30 minutes
      refetchOnWindowFocus: true,
      retry: 1,
    },
  },
});
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat(frontend): add lib modules (API client, Supabase, formatting, constants)"
```

---

### Task 3: Auth hook + Login page

**Files:** src/hooks/useAuth.ts, src/pages/Login.tsx, src/layouts/AuthLayout.tsx

- [ ] **Step 1: Create useAuth hook**

Handles: login with password, OTP send/verify, logout, session state, auto-refresh.

- [ ] **Step 2: Create AuthLayout**

Simple centered layout for the login page.

- [ ] **Step 3: Create Login page**

Three tabs matching Stitch design: Email OTP (default), Password Login, Sign Up.
OTP flow: enter email → send code → enter 8-digit code → verified.

- [ ] **Step 4: Commit**

---

### Task 4: App layout + Sidebar + Router

**Files:** src/App.tsx, src/layouts/AppLayout.tsx, src/layouts/Sidebar.tsx

- [ ] **Step 1: Create Sidebar matching Stitch design**

Dark sidebar with nav items, icons, active state highlight, user email, logout button.

- [ ] **Step 2: Create AppLayout**

Sidebar + main content area. Responsive: sidebar becomes hamburger menu on mobile.

- [ ] **Step 3: Create App.tsx with React Router**

Protected routes (require auth), public route (login), redirect logic.

- [ ] **Step 4: Commit**

---

### Task 5: Reusable components (MetricCard, DataTable, Chart, etc.)

**Files:** src/components/*.tsx

- [ ] **Step 1: Install shadcn/ui primitives**

```bash
npx shadcn@latest add card button input label tabs form select dialog
```

- [ ] **Step 2: Create MetricCard.tsx**

Displays: label, formatted value (Indian notation), optional delta with color.

- [ ] **Step 3: Create DataTable.tsx**

Styled table with column headers, Indian number formatting, alternating row tints.

- [ ] **Step 4: Create ProsperityChart.tsx**

Recharts wrapper that applies prosperity color theme to any chart.

- [ ] **Step 5: Create PageHeader.tsx, LoadingState.tsx, EmptyState.tsx**

- [ ] **Step 6: Commit**

---

### Task 6: Data hooks (useFireInputs, useIncome, useExpenses, useProjections, useSipLog)

**Files:** src/hooks/*.ts

- [ ] **Step 1: Create all TanStack Query hooks**

Each hook wraps `apiFetch` calls with `useQuery` / `useMutation`:
- `useFireInputs()` → GET + PUT
- `useIncome()` → GET + POST + DELETE
- `useExpenses()` → GET + POST + PATCH + DELETE
- `useSipLog()` → GET + POST
- `useProjections()` → GET growth, retirement, funds, sips

- [ ] **Step 2: Commit**

---

### Task 7: Dashboard page

**Files:** src/pages/Dashboard.tsx

Reference: `stitch-designs/01-dashboard-desktop.png`

- [ ] **Step 1: Build Dashboard matching Stitch design**

- FIRE countdown with progress bar
- Income overview row (4 MetricCards)
- FIRE metrics row (4 MetricCards with funded ratio color)
- Portfolio growth Recharts stacked area chart (equity green + debt blue)
- Vertical dashed line at retirement age

- [ ] **Step 2: Commit**

---

### Task 8: FIRE Settings page

**Files:** src/pages/FireSettings.tsx

Reference: `stitch-designs/04-fire-settings.png`

- [ ] **Step 1: Build settings form**

Form sections in cards: Personal, Investment, Monthly Expense & SWR, Expected Returns, Asset Allocation.
Debt auto-calculates. Allocation total validation. Save button. Preview section below.

- [ ] **Step 2: Commit**

---

### Task 9: Income & Expenses page

**Files:** src/pages/IncomeExpenses.tsx

Reference: `stitch-designs/02-income-expenses-desktop.png`

- [ ] **Step 1: Build financial summary + pie chart + tables**

Financial summary at top, "Where Your Money Goes" donut chart, income history with edit/delete, fixed expenses with deactivate, add forms in expandable sections.

- [ ] **Step 2: Commit**

---

### Task 10: Growth Projection, Retirement Analysis, Fund Allocation, SIP Tracker pages

**Files:** src/pages/GrowthProjection.tsx, RetirementAnalysis.tsx, FundAllocation.tsx, SipTracker.tsx

References: `stitch-designs/05-08-*.png`

- [ ] **Step 1: Build all 4 remaining pages**

Each following its Stitch design reference.

- [ ] **Step 2: Commit**

---

### Task 11: Settings & Privacy + final wiring

**Files:** src/pages/SettingsPrivacy.tsx

- [ ] **Step 1: Build export + delete account page**

- [ ] **Step 2: Verify all pages work end-to-end with FastAPI backend**

- [ ] **Step 3: Final commit + push**

---

## Implementation Notes

### React Best Practices Applied
- `client-swr-dedup`: TanStack Query handles request deduplication
- `bundle-barrel-imports`: Direct imports only, no barrel files
- `rerender-memo`: Memoize MetricCard and DataTable with React.memo
- `rendering-conditional-render`: Use ternary, not `&&`
- `js-set-map-lookups`: Use Map for fund name lookups
- `bundle-dynamic-imports`: Lazy load chart-heavy pages
- `rerender-lazy-state-init`: Function init for form state

### Prosperity Theme Tokens (Tailwind)
- `bg-prosperity-navy` — page background
- `text-prosperity-silver` — body text
- `text-prosperity-green` — positive values, success
- `text-prosperity-gold` — headings, highlights
- `text-prosperity-warning` — caution (NOT red)
- `text-prosperity-error` — muted coral alerts (NOT red)
- `border-prosperity-teal` — card borders
