# FIRE Retirement Tracker — Full Formula Verification Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Independently verify every single formula in the Excel workbook by computing expected values in Python and comparing against Excel output. This is money — zero tolerance for errors.

**Architecture:** Write a Python test suite (`tests/test_formulas.py`) that loads the workbook, independently computes every expected value from raw inputs, and asserts they match. Each sheet gets its own test class. Every formula cell gets a test.

**Tech Stack:** Python 3.10, openpyxl, pytest

---

## File Structure

```
fire-retirement-tracker/
├── fire-retirement-tracker.xlsx          # The workbook under test
├── fire-retirement-tracker-BACKUP.xlsx   # Backup of pre-fix version
├── tests/
│   ├── conftest.py                       # Shared fixtures (load workbook, raw inputs)
│   ├── test_01_inputs.py                 # Inputs sheet: all auto-calculated cells
│   ├── test_02_fund_allocation.py        # Fund Allocation: % splits + SIP amounts
│   ├── test_03_growth_projection.py      # Growth Projection: year-by-year compounding
│   ├── test_04_retirement_income.py      # Retirement Income: OFFSET, SWR, 3-bucket
│   └── test_05_sip_tracker.py            # SIP Tracker: step-up timing, totals
└── docs/superpowers/plans/
    └── 2026-03-30-excel-formula-verification.md  # This plan
```

Each test file targets exactly one sheet. `conftest.py` provides the raw input values so tests are self-contained and don't depend on each other.

---

### Task 1: Test Infrastructure — conftest.py

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Create conftest with shared fixtures**

```python
import pytest
import openpyxl
from pathlib import Path

WORKBOOK_PATH = Path(__file__).parent.parent / "fire-retirement-tracker.xlsx"

@pytest.fixture(scope="session")
def wb():
    """Load workbook with formulas (not cached values)."""
    wb = openpyxl.load_workbook(str(WORKBOOK_PATH))
    yield wb
    wb.close()

@pytest.fixture(scope="session")
def wb_values():
    """Load workbook with cached computed values."""
    wb = openpyxl.load_workbook(str(WORKBOOK_PATH), data_only=True)
    yield wb
    wb.close()

@pytest.fixture(scope="session")
def inputs():
    """Raw input constants from the Inputs sheet — the single source of truth.
    Every test computes expected values from THESE numbers, never from other cells."""
    return {
        "dob": "1997-01-15",
        "current_age": 29,           # DATEDIF result as of ~2026
        "retirement_age": 45,
        "life_expectancy": 90,
        "years_to_retirement": 16,   # 45 - 29
        "retirement_duration": 45,   # 90 - 45
        "your_sip": 225_000,
        "wife_sip": 100_000,
        "total_sip": 325_000,
        "step_up": 0.10,
        "existing_corpus": 2_500_000,
        "equity_return": 0.11,
        "debt_return": 0.07,
        "gold_return": 0.09,
        "cash_return": 0.05,
        "inflation": 0.065,
        "swr": 0.03,
        "equity_pct": 0.75,
        "debt_pct": 0.15,
        "gold_pct": 0.05,
        "cash_pct": 0.05,
        "monthly_expense": 125_000,
    }

# Tolerance for floating point comparisons (0.01 = 1 paisa)
TOLERANCE = 0.01
```

- [ ] **Step 2: Run to verify fixtures load**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest tests/conftest.py --co -q`
Expected: No errors (collection only)

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add conftest with shared fixtures for formula verification"
```

---

### Task 2: Test Inputs Sheet — All Auto-Calculated Cells

**Files:**
- Create: `tests/test_01_inputs.py`

Tests every formula in the Inputs sheet (B5, B8, B9, B15, B32, B36, B37, B38, B41, B42).

- [ ] **Step 1: Write tests for all 10 formula cells**

```python
import pytest
from tests.conftest import TOLERANCE

class TestInputsSheet:
    """Verify every auto-calculated cell in the Inputs sheet."""

    def test_b5_current_age(self, wb_values, inputs):
        """B5 = DATEDIF(B4, TODAY(), 'Y') — age from DOB."""
        val = wb_values["Inputs"]["B5"].value
        # Age should be 29 (born 1997, tested ~2026)
        assert val == inputs["current_age"], f"B5 Current Age: got {val}, expected {inputs['current_age']}"

    def test_b8_years_to_retirement(self, wb_values, inputs):
        """B8 = B6 - B5 = retirement_age - current_age."""
        val = wb_values["Inputs"]["B8"].value
        expected = inputs["retirement_age"] - inputs["current_age"]
        assert val == expected, f"B8 Years to Retirement: got {val}, expected {expected}"

    def test_b9_retirement_duration(self, wb_values, inputs):
        """B9 = B7 - B6 = life_expectancy - retirement_age."""
        val = wb_values["Inputs"]["B9"].value
        expected = inputs["life_expectancy"] - inputs["retirement_age"]
        assert val == expected, f"B9 Retirement Duration: got {val}, expected {expected}"

    def test_b15_total_sip(self, wb_values, inputs):
        """B15 = B13 + B14 = your_sip + wife_sip."""
        val = wb_values["Inputs"]["B15"].value
        expected = inputs["your_sip"] + inputs["wife_sip"]
        assert val == expected, f"B15 Total SIP: got {val}, expected {expected}"

    def test_b32_allocation_sums_to_100(self, wb_values, inputs):
        """B32 = B28+B29+B30+B31 = must equal 1.0 (100%)."""
        val = wb_values["Inputs"]["B32"].value
        expected = inputs["equity_pct"] + inputs["debt_pct"] + inputs["gold_pct"] + inputs["cash_pct"]
        assert abs(val - expected) < TOLERANCE, f"B32 Allocation Total: got {val}, expected {expected}"
        assert abs(val - 1.0) < TOLERANCE, f"B32 must equal 1.0, got {val}"

    def test_b36_monthly_expense_at_retirement(self, wb_values, inputs):
        """B36 = B35 * (1+B24)^B8 — inflation-adjusted expense."""
        val = wb_values["Inputs"]["B36"].value
        expected = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"]
        assert abs(val - expected) < TOLERANCE, f"B36 Monthly Expense at Retirement: got {val}, expected {expected}"

    def test_b37_annual_expense_at_retirement(self, wb_values, inputs):
        """B37 = B36 * 12."""
        val = wb_values["Inputs"]["B37"].value
        monthly = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"]
        expected = monthly * 12
        assert abs(val - expected) < TOLERANCE, f"B37 Annual Expense: got {val}, expected {expected}"

    def test_b38_required_corpus(self, wb_values, inputs):
        """B38 = B37 / B25 = annual_expense / SWR."""
        val = wb_values["Inputs"]["B38"].value
        annual = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"] * 12
        expected = annual / inputs["swr"]
        assert abs(val - expected) < TOLERANCE, f"B38 Required Corpus: got {val}, expected {expected}"

    def test_b41_blended_return(self, wb_values, inputs):
        """B41 = B28*B20 + B29*B21 + B30*B22 + B31*B23."""
        val = wb_values["Inputs"]["B41"].value
        expected = (
            inputs["equity_pct"] * inputs["equity_return"]
            + inputs["debt_pct"] * inputs["debt_return"]
            + inputs["gold_pct"] * inputs["gold_return"]
            + inputs["cash_pct"] * inputs["cash_return"]
        )
        assert abs(val - expected) < TOLERANCE, f"B41 Blended Return: got {val}, expected {expected}"

    def test_b42_real_return_fisher(self, wb_values, inputs):
        """B42 = (1+B41)/(1+B24)-1 — Fisher equation (NOT simple subtraction)."""
        val = wb_values["Inputs"]["B42"].value
        blended = (
            inputs["equity_pct"] * inputs["equity_return"]
            + inputs["debt_pct"] * inputs["debt_return"]
            + inputs["gold_pct"] * inputs["gold_return"]
            + inputs["cash_pct"] * inputs["cash_return"]
        )
        expected = (1 + blended) / (1 + inputs["inflation"]) - 1
        assert abs(val - expected) < TOLERANCE, f"B42 Real Return: got {val}, expected {expected}"
        # Also verify it's NOT the old simple subtraction
        wrong_value = blended - inputs["inflation"]
        assert abs(val - wrong_value) > 0.001, "B42 still uses simple subtraction — Fisher fix not applied!"

    def test_formula_text_b42_is_fisher(self, wb):
        """Verify the actual formula text uses Fisher equation."""
        formula = wb["Inputs"]["B42"].value
        assert "/(1+" in formula or "/ (1+" in formula, f"B42 formula doesn't look like Fisher: {formula}"
```

- [ ] **Step 2: Run tests**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest tests/test_01_inputs.py -v`
Expected: All 11 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_01_inputs.py
git commit -m "test: verify all Inputs sheet formulas"
```

---

### Task 3: Test Fund Allocation Sheet — Every Fund Row

**Files:**
- Create: `tests/test_02_fund_allocation.py`

Tests all 10 fund rows (C4:C13, D4:D13) plus totals (C14, D14).

- [ ] **Step 1: Write tests for all fund allocation formulas**

```python
import pytest
from tests.conftest import TOLERANCE

# Fund allocation breakdown: (name, category, parent_pct_key, sub_pct)
FUNDS = [
    ("Nifty 50 Index Fund",       "equity", "equity_pct", 35),
    ("Nifty Next 50 Index Fund",  "equity", "equity_pct", 20),
    ("Nifty Midcap 150",          "equity", "equity_pct", 20),
    ("Nifty Smallcap 250",        "equity", "equity_pct", 10),
    ("Nifty Total Market",        "equity", "equity_pct", 15),
    ("Short Duration Debt Fund",  "debt",   "debt_pct",   40),
    ("Arbitrage Fund",            "debt",   "debt_pct",   30),
    ("Liquid/Overnight Fund",     "debt",   "debt_pct",   30),
    ("Gold ETF",                  "gold",   "gold_pct",   100),
    ("Emergency / Cash Reserve",  "cash",   "cash_pct",   100),
]

class TestFundAllocationSheet:
    """Verify every fund row and totals in Fund Allocation sheet."""

    @pytest.mark.parametrize("row_idx,fund_info", enumerate(FUNDS), ids=[f[0] for f in FUNDS])
    def test_fund_percentage(self, wb_values, inputs, row_idx, fund_info):
        """C column: each fund's % of total portfolio."""
        name, category, parent_key, sub_pct = fund_info
        row = row_idx + 4  # Data starts at row 4
        val = wb_values["Fund Allocation"][f"C{row}"].value
        if category in ("gold", "cash"):
            expected = inputs[parent_key]  # Gold/Cash = 100% of their allocation
        else:
            expected = inputs[parent_key] * sub_pct / 100
        assert abs(val - expected) < TOLERANCE, f"C{row} {name} %: got {val}, expected {expected}"

    @pytest.mark.parametrize("row_idx,fund_info", enumerate(FUNDS), ids=[f[0] for f in FUNDS])
    def test_fund_monthly_sip(self, wb_values, inputs, row_idx, fund_info):
        """D column: each fund's monthly SIP amount in rupees."""
        name, category, parent_key, sub_pct = fund_info
        row = row_idx + 4
        val = wb_values["Fund Allocation"][f"D{row}"].value
        if category in ("gold", "cash"):
            pct = inputs[parent_key]
        else:
            pct = inputs[parent_key] * sub_pct / 100
        expected = pct * inputs["total_sip"]
        assert abs(val - expected) < TOLERANCE, f"D{row} {name} SIP: got {val}, expected {expected}"

    def test_c14_total_percentage(self, wb_values):
        """C14 = SUM(C4:C13) must equal 1.0 (100%)."""
        val = wb_values["Fund Allocation"]["C14"].value
        assert abs(val - 1.0) < TOLERANCE, f"C14 Total %: got {val}, expected 1.0"

    def test_d14_total_sip(self, wb_values, inputs):
        """D14 = SUM(D4:D13) must equal total monthly SIP."""
        val = wb_values["Fund Allocation"]["D14"].value
        assert abs(val - inputs["total_sip"]) < TOLERANCE, f"D14 Total SIP: got {val}, expected {inputs['total_sip']}"

    def test_equity_sub_pcts_sum_to_100(self):
        """Equity sub-allocation percentages must sum to 100."""
        equity_sub_pcts = [f[3] for f in FUNDS if f[1] == "equity"]
        assert sum(equity_sub_pcts) == 100, f"Equity sub-pcts sum to {sum(equity_sub_pcts)}, not 100"

    def test_debt_sub_pcts_sum_to_100(self):
        """Debt sub-allocation percentages must sum to 100."""
        debt_sub_pcts = [f[3] for f in FUNDS if f[1] == "debt"]
        assert sum(debt_sub_pcts) == 100, f"Debt sub-pcts sum to {sum(debt_sub_pcts)}, not 100"
```

- [ ] **Step 2: Run tests**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest tests/test_02_fund_allocation.py -v`
Expected: All 26 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_02_fund_allocation.py
git commit -m "test: verify all Fund Allocation formulas and sub-allocation sums"
```

---

### Task 4: Test Growth Projection — The Critical Sheet (Year-by-Year)

**Files:**
- Create: `tests/test_03_growth_projection.py`

This is the most critical sheet. Tests every row (Year 0-40), every column (B through I), plus the three bugs we fixed: step-up timing, mid-year compounding, and post-retirement SIP=0.

- [ ] **Step 1: Write comprehensive growth projection tests**

```python
import pytest
from tests.conftest import TOLERANCE

class TestGrowthProjectionSheet:
    """Verify every cell in the Growth Projection sheet.

    This is the most important sheet — it drives the retirement corpus.
    We independently compute every value from raw inputs and compare.
    """

    @pytest.fixture
    def expected_projection(self, inputs):
        """Independently compute the full year-by-year projection from raw inputs."""
        rows = []
        sip = inputs["total_sip"]
        portfolio = inputs["existing_corpus"]
        cumulative = inputs["existing_corpus"]
        blended = (
            inputs["equity_pct"] * inputs["equity_return"]
            + inputs["debt_pct"] * inputs["debt_return"]
            + inputs["gold_pct"] * inputs["gold_return"]
            + inputs["cash_pct"] * inputs["cash_return"]
        )

        for year in range(0, 41):
            age = inputs["current_age"] + year

            # Monthly SIP logic:
            # Year 0: display base SIP, but invest 0 (starting point)
            # Year 1: invest at base SIP (NO step-up)
            # Year 2+: step up from previous year's SIP (if before retirement)
            # Post-retirement: SIP = 0
            if year == 0:
                monthly_sip = inputs["total_sip"]
                annual_inv = 0
            elif year == 1:
                monthly_sip = inputs["total_sip"]  # Base SIP, no step-up
                annual_inv = monthly_sip * 12
            elif year <= inputs["years_to_retirement"]:
                monthly_sip = sip * (1 + inputs["step_up"])
                annual_inv = monthly_sip * 12
            else:
                monthly_sip = 0
                annual_inv = 0

            sip = monthly_sip

            # Portfolio compounding (mid-year convention for new SIP)
            if year == 0:
                pass  # Portfolio = existing corpus
            else:
                portfolio = portfolio * (1 + blended) + annual_inv * (1 + blended / 2)

            cumulative += annual_inv
            gains = portfolio - cumulative
            equity_value = portfolio * inputs["equity_pct"]
            debt_gold_cash = portfolio * (1 - inputs["equity_pct"])

            rows.append({
                "year": year,
                "age": age,
                "monthly_sip": monthly_sip,
                "annual_inv": annual_inv,
                "cumulative": cumulative,
                "portfolio": portfolio,
                "gains": gains,
                "equity_value": equity_value,
                "debt_gold_cash": debt_gold_cash,
            })

        return rows

    # --- Column B: Age ---
    @pytest.mark.parametrize("year", range(0, 41))
    def test_age_column(self, wb_values, inputs, year):
        """B column: Age = current_age + year."""
        row = year + 4
        val = wb_values["Growth Projection"][f"B{row}"].value
        expected = inputs["current_age"] + year
        assert val == expected, f"B{row} Age (Year {year}): got {val}, expected {expected}"

    # --- Column C: Monthly SIP ---
    def test_c4_year0_sip_is_base(self, wb_values, inputs):
        """Year 0 SIP = base SIP (display only, no investment)."""
        val = wb_values["Growth Projection"]["C4"].value
        assert val == inputs["total_sip"], f"C4: got {val}, expected {inputs['total_sip']}"

    def test_c5_year1_sip_is_base_not_stepped_up(self, wb_values, inputs):
        """CRITICAL: Year 1 SIP must be BASE SIP (325000), NOT stepped up (357500).
        This was a bug — step-up was applied 1 year too early."""
        val = wb_values["Growth Projection"]["C5"].value
        assert val == inputs["total_sip"], (
            f"C5 Year 1 SIP: got {val}, expected {inputs['total_sip']}. "
            f"Step-up bug still present if got {inputs['total_sip'] * (1 + inputs['step_up'])}"
        )

    def test_c5_formula_text(self, wb):
        """Verify C5 formula references base SIP, not step-up."""
        formula = wb["Growth Projection"]["C5"].value
        assert "B16" not in formula, f"C5 still references step-up (B16): {formula}"
        assert "B15" in formula, f"C5 should reference base SIP (B15): {formula}"

    @pytest.mark.parametrize("year", range(2, 17))
    def test_sip_stepup_during_accumulation(self, wb_values, inputs, expected_projection, year):
        """Years 2-16: SIP should step up by 10% each year."""
        row = year + 4
        val = wb_values["Growth Projection"][f"C{row}"].value
        expected = expected_projection[year]["monthly_sip"]
        assert abs(val - expected) < TOLERANCE, (
            f"C{row} Year {year} SIP: got {val}, expected {expected}"
        )

    @pytest.mark.parametrize("year", range(17, 41))
    def test_sip_zero_after_retirement(self, wb_values, year):
        """CRITICAL: Post-retirement SIP must be 0."""
        row = year + 4
        val = wb_values["Growth Projection"][f"C{row}"].value
        assert val == 0, f"C{row} Year {year} (post-retirement) SIP: got {val}, expected 0"

    # --- Column D: Annual Investment ---
    @pytest.mark.parametrize("year", range(0, 41))
    def test_annual_investment(self, wb_values, expected_projection, year):
        """D column: Annual Investment = Monthly SIP * 12 (or 0 for Year 0 / post-retirement)."""
        row = year + 4
        val = wb_values["Growth Projection"][f"D{row}"].value
        expected = expected_projection[year]["annual_inv"]
        assert abs(val - expected) < TOLERANCE, (
            f"D{row} Year {year} Annual Inv: got {val}, expected {expected}"
        )

    # --- Column E: Cumulative Invested ---
    @pytest.mark.parametrize("year", range(0, 41))
    def test_cumulative_invested(self, wb_values, expected_projection, year):
        """E column: Running total of all money invested."""
        row = year + 4
        val = wb_values["Growth Projection"][f"E{row}"].value
        expected = expected_projection[year]["cumulative"]
        assert abs(val - expected) < TOLERANCE, (
            f"E{row} Year {year} Cumulative: got {val:,.0f}, expected {expected:,.0f}"
        )

    # --- Column F: Portfolio Value (THE critical column) ---
    def test_f4_year0_portfolio_equals_existing_corpus(self, wb_values, inputs):
        """Year 0 portfolio = existing corpus exactly."""
        val = wb_values["Growth Projection"]["F4"].value
        assert val == inputs["existing_corpus"], f"F4: got {val}, expected {inputs['existing_corpus']}"

    def test_f5_formula_uses_midyear_convention(self, wb):
        """CRITICAL: Verify F5 formula text uses mid-year convention, not start-of-year."""
        formula = wb["Growth Projection"]["F5"].value
        # Should be: =F4*(1+Inputs!$B$41)+D5*(1+Inputs!$B$41/2)
        # Should NOT contain: =(F4+D5)*(1+Inputs!B41)
        assert "+D5" not in formula.split(")*")[0] if ")*" in formula else True, (
            f"F5 still uses start-of-year: {formula}"
        )
        assert "/2" in formula or "/ 2" in formula, f"F5 missing mid-year /2 factor: {formula}"

    @pytest.mark.parametrize("year", range(1, 41))
    def test_portfolio_value(self, wb_values, expected_projection, year):
        """F column: Portfolio Value computed with mid-year convention.
        Tolerance is 1 rupee for large amounts."""
        row = year + 4
        val = wb_values["Growth Projection"][f"F{row}"].value
        expected = expected_projection[year]["portfolio"]
        tolerance = max(1.0, abs(expected) * 1e-9)  # 1 rupee or 1 billionth, whichever is larger
        assert abs(val - expected) < tolerance, (
            f"F{row} Year {year} Portfolio: got {val:,.2f}, expected {expected:,.2f}, "
            f"diff {val - expected:,.2f}"
        )

    # --- Column G: Total Gains ---
    @pytest.mark.parametrize("year", range(0, 41))
    def test_total_gains(self, wb_values, expected_projection, year):
        """G column: Gains = Portfolio - Cumulative Invested."""
        row = year + 4
        val = wb_values["Growth Projection"][f"G{row}"].value
        expected = expected_projection[year]["gains"]
        tolerance = max(1.0, abs(expected) * 1e-9) if expected != 0 else TOLERANCE
        assert abs(val - expected) < tolerance, (
            f"G{row} Year {year} Gains: got {val:,.2f}, expected {expected:,.2f}"
        )

    # --- Columns H & I: Equity / Debt+Gold+Cash split ---
    @pytest.mark.parametrize("year", range(0, 41))
    def test_equity_value_split(self, wb_values, expected_projection, year):
        """H column: Equity Value = Portfolio * equity_pct."""
        row = year + 4
        val = wb_values["Growth Projection"][f"H{row}"].value
        expected = expected_projection[year]["equity_value"]
        tolerance = max(1.0, abs(expected) * 1e-9)
        assert abs(val - expected) < tolerance, (
            f"H{row} Year {year} Equity: got {val:,.2f}, expected {expected:,.2f}"
        )

    @pytest.mark.parametrize("year", range(0, 41))
    def test_debt_gold_cash_split(self, wb_values, expected_projection, year):
        """I column: Debt+Gold+Cash = Portfolio * (1 - equity_pct)."""
        row = year + 4
        val = wb_values["Growth Projection"][f"I{row}"].value
        expected = expected_projection[year]["debt_gold_cash"]
        tolerance = max(1.0, abs(expected) * 1e-9)
        assert abs(val - expected) < tolerance, (
            f"I{row} Year {year} D+G+C: got {val:,.2f}, expected {expected:,.2f}"
        )

    # --- Cross-checks ---
    @pytest.mark.parametrize("year", range(0, 41))
    def test_portfolio_equals_equity_plus_rest(self, wb_values, year):
        """F = H + I (portfolio = equity + debt+gold+cash)."""
        row = year + 4
        ws = wb_values["Growth Projection"]
        f_val = ws[f"F{row}"].value
        h_val = ws[f"H{row}"].value
        i_val = ws[f"I{row}"].value
        assert abs(f_val - (h_val + i_val)) < 1.0, (
            f"Row {row} Year {year}: F({f_val:,.0f}) != H({h_val:,.0f}) + I({i_val:,.0f})"
        )

    @pytest.mark.parametrize("year", range(0, 41))
    def test_gains_equals_portfolio_minus_cumulative(self, wb_values, year):
        """G = F - E (gains = portfolio - cumulative invested)."""
        row = year + 4
        ws = wb_values["Growth Projection"]
        f_val = ws[f"F{row}"].value
        e_val = ws[f"E{row}"].value
        g_val = ws[f"G{row}"].value
        assert abs(g_val - (f_val - e_val)) < 1.0, (
            f"Row {row} Year {year}: G({g_val:,.0f}) != F({f_val:,.0f}) - E({e_val:,.0f})"
        )
```

- [ ] **Step 2: Run tests**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest tests/test_03_growth_projection.py -v --tb=short 2>&1 | head -80`
Expected: All tests PASS (300+ parametrized tests)

- [ ] **Step 3: Commit**

```bash
git add tests/test_03_growth_projection.py
git commit -m "test: verify all Growth Projection formulas (41 years x 8 columns)"
```

---

### Task 5: Test Retirement Income Sheet — OFFSET, SWR, 3-Bucket

**Files:**
- Create: `tests/test_04_retirement_income.py`

Tests the OFFSET fix, all SWR scenarios, 3-bucket strategy, and cross-sheet consistency.

- [ ] **Step 1: Write retirement income tests**

```python
import pytest
from tests.conftest import TOLERANCE

class TestRetirementIncomeSheet:
    """Verify every formula in the Retirement Income sheet."""

    @pytest.fixture
    def retirement_corpus(self, inputs):
        """Independently compute the corpus at retirement (Year 16)."""
        sip = inputs["total_sip"]
        portfolio = inputs["existing_corpus"]
        blended = (
            inputs["equity_pct"] * inputs["equity_return"]
            + inputs["debt_pct"] * inputs["debt_return"]
            + inputs["gold_pct"] * inputs["gold_return"]
            + inputs["cash_pct"] * inputs["cash_return"]
        )
        for year in range(1, inputs["years_to_retirement"] + 1):
            if year == 1:
                monthly_sip = inputs["total_sip"]
            else:
                sip = sip * (1 + inputs["step_up"])
                monthly_sip = sip
            annual_inv = monthly_sip * 12
            portfolio = portfolio * (1 + blended) + annual_inv * (1 + blended / 2)
        return portfolio

    # --- B4: Corpus at Retirement ---
    def test_b4_corpus_at_retirement(self, wb_values, retirement_corpus):
        """B4 = OFFSET picks the correct retirement year from Growth Projection."""
        val = wb_values["Retirement Income"]["B4"].value
        tolerance = max(1.0, abs(retirement_corpus) * 1e-9)
        assert abs(val - retirement_corpus) < tolerance, (
            f"B4 Corpus: got {val:,.0f}, expected {retirement_corpus:,.0f}"
        )

    def test_b4_offset_formula_uses_f4_not_f3(self, wb):
        """CRITICAL: Verify OFFSET base is F4 (not F3 — the off-by-1 bug)."""
        formula = wb["Retirement Income"]["B4"].value
        assert "F4" in formula, f"B4 OFFSET still uses F3 (off-by-1 bug): {formula}"
        assert "F3" not in formula.replace("F4", ""), f"B4 has stale F3 reference: {formula}"

    def test_b4_matches_growth_projection_retirement_row(self, wb_values, inputs):
        """B4 must match the Growth Projection F column at the retirement year row."""
        retirement_row = inputs["years_to_retirement"] + 4  # Year 0 = row 4, Year 16 = row 20
        gp_val = wb_values["Growth Projection"][f"F{retirement_row}"].value
        ri_val = wb_values["Retirement Income"]["B4"].value
        assert abs(ri_val - gp_val) < 1.0, (
            f"Retirement B4 ({ri_val:,.0f}) != Growth F{retirement_row} ({gp_val:,.0f})"
        )

    # --- B5: Annual Expense at Retirement ---
    def test_b5_annual_expense(self, wb_values, inputs):
        """B5 = Inputs!B37 = monthly_expense * (1+inflation)^years * 12."""
        val = wb_values["Retirement Income"]["B5"].value
        expected = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"] * 12
        assert abs(val - expected) < TOLERANCE, f"B5 Annual Expense: got {val:,.0f}, expected {expected:,.0f}"

    # --- B6: Monthly SWP Income ---
    def test_b6_monthly_swp(self, wb_values, retirement_corpus, inputs):
        """B6 = B4 * SWR / 12."""
        val = wb_values["Retirement Income"]["B6"].value
        expected = retirement_corpus * inputs["swr"] / 12
        tolerance = max(1.0, abs(expected) * 1e-9)
        assert abs(val - expected) < tolerance, f"B6 Monthly SWP: got {val:,.0f}, expected {expected:,.0f}"

    # --- B7: Monthly Expense at Retirement ---
    def test_b7_monthly_expense(self, wb_values, inputs):
        """B7 = Inputs!B36."""
        val = wb_values["Retirement Income"]["B7"].value
        expected = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"]
        assert abs(val - expected) < TOLERANCE, f"B7 Monthly Expense: got {val:,.0f}, expected {expected:,.0f}"

    # --- B8: Monthly Surplus/Deficit ---
    def test_b8_surplus(self, wb_values, retirement_corpus, inputs):
        """B8 = B6 - B7 = SWP income - monthly expense."""
        val = wb_values["Retirement Income"]["B8"].value
        swp = retirement_corpus * inputs["swr"] / 12
        expense = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"]
        expected = swp - expense
        tolerance = max(1.0, abs(expected) * 1e-9)
        assert abs(val - expected) < tolerance, f"B8 Surplus: got {val:,.0f}, expected {expected:,.0f}"

    def test_b8_is_positive(self, wb_values):
        """Sanity: surplus should be positive (otherwise FIRE plan fails)."""
        val = wb_values["Retirement Income"]["B8"].value
        assert val > 0, f"B8 Monthly Surplus is NEGATIVE: {val:,.0f} — FIRE plan underfunded!"

    # --- B9: Funded Ratio ---
    def test_b9_funded_ratio(self, wb_values, retirement_corpus, inputs):
        """B9 = B4 / Inputs!B38 = corpus / required_corpus."""
        val = wb_values["Retirement Income"]["B9"].value
        required = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"] * 12 / inputs["swr"]
        expected = retirement_corpus / required
        assert abs(val - expected) < 0.01, f"B9 Funded Ratio: got {val:.4f}, expected {expected:.4f}"

    def test_b9_above_1(self, wb_values):
        """Sanity: funded ratio must be > 1.0."""
        val = wb_values["Retirement Income"]["B9"].value
        assert val > 1.0, f"B9 Funded Ratio below 1.0: {val:.2f} — FIRE target not met!"

    # --- B10: Required Corpus ---
    def test_b10_required_corpus(self, wb_values, inputs):
        """B10 = Inputs!B38."""
        val = wb_values["Retirement Income"]["B10"].value
        expected = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"] * 12 / inputs["swr"]
        assert abs(val - expected) < TOLERANCE, f"B10 Required Corpus: got {val:,.0f}, expected {expected:,.0f}"

    # --- 3-Bucket Strategy (rows 14-16) ---
    @pytest.mark.parametrize("row,pct", [(14, 0.08), (15, 0.27), (16, 0.65)])
    def test_bucket_amount(self, wb_values, retirement_corpus, row, pct):
        """C14/C15/C16 = corpus * bucket percentage."""
        val = wb_values["Retirement Income"][f"C{row}"].value
        expected = retirement_corpus * pct
        tolerance = max(1.0, abs(expected) * 1e-9)
        assert abs(val - expected) < tolerance, f"C{row} Bucket ({pct*100}%): got {val:,.0f}, expected {expected:,.0f}"

    def test_bucket_percentages_sum_to_100(self, wb_values):
        """Bucket percentages must sum to 100%."""
        ws = wb_values["Retirement Income"]
        total = ws["B14"].value + ws["B15"].value + ws["B16"].value
        assert abs(total - 1.0) < TOLERANCE, f"Bucket %s sum to {total}, not 1.0"

    def test_bucket_amounts_sum_to_corpus(self, wb_values):
        """Bucket amounts must sum to total corpus."""
        ws = wb_values["Retirement Income"]
        corpus = ws["B4"].value
        bucket_sum = ws["C14"].value + ws["C15"].value + ws["C16"].value
        assert abs(bucket_sum - corpus) < 1.0, (
            f"Bucket sum ({bucket_sum:,.0f}) != corpus ({corpus:,.0f})"
        )

    # --- E14/E15: Coverage Years ---
    def test_e14_safety_bucket_coverage(self, wb_values, retirement_corpus, inputs):
        """E14 = C14 / B5 (safety bucket / annual expense = years of coverage)."""
        val = wb_values["Retirement Income"]["E14"].value
        annual_expense = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"] * 12
        expected = (retirement_corpus * 0.08) / annual_expense
        assert abs(val - expected) < 0.01, f"E14 Safety Coverage: got {val:.2f}yr, expected {expected:.2f}yr"

    # --- SWR Comparison (rows 21-25) ---
    @pytest.mark.parametrize("row,swr_rate", [
        (21, 0.02), (22, 0.025), (23, 0.03), (24, 0.035), (25, 0.04)
    ])
    def test_swr_annual_withdrawal(self, wb_values, retirement_corpus, row, swr_rate):
        """B column: Annual withdrawal = corpus * SWR rate."""
        val = wb_values["Retirement Income"][f"B{row}"].value
        expected = retirement_corpus * swr_rate
        tolerance = max(1.0, abs(expected) * 1e-9)
        assert abs(val - expected) < tolerance, (
            f"B{row} SWR {swr_rate*100}% withdrawal: got {val:,.0f}, expected {expected:,.0f}"
        )

    @pytest.mark.parametrize("row,swr_rate", [
        (21, 0.02), (22, 0.025), (23, 0.03), (24, 0.035), (25, 0.04)
    ])
    def test_swr_monthly(self, wb_values, retirement_corpus, row, swr_rate):
        """C column: Monthly = Annual / 12."""
        val = wb_values["Retirement Income"][f"C{row}"].value
        expected = retirement_corpus * swr_rate / 12
        tolerance = max(1.0, abs(expected) * 1e-9)
        assert abs(val - expected) < tolerance, (
            f"C{row} SWR {swr_rate*100}% monthly: got {val:,.0f}, expected {expected:,.0f}"
        )

    @pytest.mark.parametrize("row,swr_rate", [
        (21, 0.02), (22, 0.025), (23, 0.03), (24, 0.035), (25, 0.04)
    ])
    def test_swr_vs_expense(self, wb_values, retirement_corpus, inputs, row, swr_rate):
        """D column: vs Expense = monthly SWP - monthly expense."""
        val = wb_values["Retirement Income"][f"D{row}"].value
        monthly_swp = retirement_corpus * swr_rate / 12
        monthly_expense = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"]
        expected = monthly_swp - monthly_expense
        tolerance = max(1.0, abs(expected) * 1e-9)
        assert abs(val - expected) < tolerance, (
            f"D{row} SWR {swr_rate*100}% vs expense: got {val:,.0f}, expected {expected:,.0f}"
        )
```

- [ ] **Step 2: Run tests**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest tests/test_04_retirement_income.py -v --tb=short`
Expected: All 33+ tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_04_retirement_income.py
git commit -m "test: verify all Retirement Income formulas, SWR scenarios, and 3-bucket strategy"
```

---

### Task 6: Test SIP Tracker — Step-up Timing and Structure

**Files:**
- Create: `tests/test_05_sip_tracker.py`

Tests the SIP step-up timing matches Growth Projection, verifies all 192 months, and checks structure.

- [ ] **Step 1: Write SIP tracker tests**

```python
import pytest
from tests.conftest import TOLERANCE

class TestSIPTrackerSheet:
    """Verify SIP Tracker formulas, step-up timing, and structure."""

    @pytest.fixture
    def expected_monthly_sips(self, inputs):
        """Compute expected Planned SIP for all 192 months."""
        sips = []
        current = inputs["total_sip"]
        for month in range(1, 193):
            if month > 1 and (month - 1) % 12 == 0:
                current = current * (1 + inputs["step_up"])
            sips.append(current)
        return sips

    def test_month_count(self, wb_values):
        """SIP Tracker should have exactly 192 months of data."""
        ws = wb_values["SIP Tracker"]
        month_count = 0
        for row in range(5, 197):
            if ws[f"A{row}"].value is not None and isinstance(ws[f"A{row}"].value, (int, float)):
                month_count += 1
        assert month_count == 192, f"Expected 192 months, got {month_count}"

    def test_first_month_is_base_sip(self, wb_values, inputs):
        """Month 1 Planned SIP = base SIP (no step-up)."""
        val = wb_values["SIP Tracker"]["C5"].value
        assert val == inputs["total_sip"], f"Month 1 SIP: got {val}, expected {inputs['total_sip']}"

    def test_months_1_to_12_no_stepup(self, wb_values, inputs):
        """Months 1-12 should all have the base SIP (325000)."""
        for row in range(5, 17):  # months 1-12
            val = wb_values["SIP Tracker"][f"C{row}"].value
            assert val == inputs["total_sip"], (
                f"Month {row-4} (row {row}): got {val}, expected {inputs['total_sip']}"
            )

    def test_month_13_first_stepup(self, wb_values, inputs):
        """Month 13 should be first step-up: 325000 * 1.10 = 357500."""
        val = wb_values["SIP Tracker"]["C17"].value
        expected = inputs["total_sip"] * (1 + inputs["step_up"])
        assert abs(val - expected) < TOLERANCE, f"Month 13 SIP: got {val}, expected {expected}"

    @pytest.mark.parametrize("month", [1, 12, 13, 24, 25, 36, 60, 120, 180, 192])
    def test_planned_sip_at_key_months(self, wb_values, expected_monthly_sips, month):
        """Verify Planned SIP at key milestone months."""
        row = month + 4
        val = wb_values["SIP Tracker"][f"C{row}"].value
        expected = expected_monthly_sips[month - 1]
        assert abs(val - expected) < TOLERANCE, (
            f"Month {month} Planned SIP: got {val:,.0f}, expected {expected:,.0f}"
        )

    def test_stepup_consistency_with_growth_projection(self, wb_values, inputs):
        """SIP Tracker annual SIP must match Growth Projection for each year.
        Sum of 12 months in SIP Tracker = Annual Investment in Growth Projection."""
        ws_sip = wb_values["SIP Tracker"]
        ws_gp = wb_values["Growth Projection"]

        for year in range(1, inputs["years_to_retirement"] + 1):
            # Sum 12 months from SIP Tracker
            start_month = (year - 1) * 12 + 1
            sip_sum = 0
            for m in range(start_month, start_month + 12):
                row = m + 4
                val = ws_sip[f"C{row}"].value
                sip_sum += val if val else 0

            # Get annual investment from Growth Projection
            gp_row = year + 4
            gp_annual = ws_gp[f"D{gp_row}"].value

            assert abs(sip_sum - gp_annual) < 1.0, (
                f"Year {year}: SIP Tracker sum ({sip_sum:,.0f}) != "
                f"Growth Projection D{gp_row} ({gp_annual:,.0f})"
            )

    def test_difference_formula_empty_when_no_actual(self, wb_values):
        """E column should be blank when D (Actual) is empty."""
        val = wb_values["SIP Tracker"]["E5"].value
        assert val is None or val == "", f"E5 should be blank when D5 is empty, got {val}"

    def test_totals_row_exists(self, wb_values):
        """Row 197 should be TOTAL row."""
        val = wb_values["SIP Tracker"]["A197"].value
        assert val == "TOTAL", f"A197: got {val}, expected 'TOTAL'"

    def test_totals_planned_sip(self, wb_values, expected_monthly_sips):
        """C197 = sum of all planned SIPs for 192 months."""
        val = wb_values["SIP Tracker"]["C197"].value
        expected = sum(expected_monthly_sips)
        assert abs(val - expected) < 1.0, (
            f"C197 Total Planned: got {val:,.0f}, expected {expected:,.0f}"
        )

    # --- Structure checks ---
    def test_all_fund_columns_present(self, wb_values):
        """All 10 fund columns should have headers."""
        ws = wb_values["SIP Tracker"]
        expected_funds = [
            ("F4", "Nifty50"), ("G4", "Next50"), ("H4", "Mid150"),
            ("J4", "Small250"), ("K4", "TotalMkt"), ("L4", "ShortDebt"),
            ("M4", "Arbitrage"), ("N4", "Liquid"), ("O4", "GoldETF"), ("P4", "Cash"),
        ]
        for cell, keyword in expected_funds:
            val = ws[cell].value
            assert val is not None and keyword in str(val), (
                f"{cell} should contain '{keyword}', got: {val}"
            )

    def test_notes_column_exists(self, wb_values):
        """Notes column (I4) should exist."""
        val = wb_values["SIP Tracker"]["I4"].value
        assert val is not None and "Notes" in str(val), f"I4 should be Notes, got: {val}"
```

- [ ] **Step 2: Run tests**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest tests/test_05_sip_tracker.py -v --tb=short`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_05_sip_tracker.py
git commit -m "test: verify SIP Tracker step-up timing, 192 months, and fund column structure"
```

---

### Task 7: Run Full Test Suite and Generate Report

**Files:**
- No new files

- [ ] **Step 1: Run all tests with verbose output**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: ALL TESTS PASS. Target: 400+ individual test assertions.

- [ ] **Step 2: Run with count summary**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest tests/ -v --tb=short -q`
Expected: "X passed" with 0 failures.

- [ ] **Step 3: Commit all test files**

```bash
git add tests/
git commit -m "test: complete formula verification suite — all sheets, all formulas validated"
```

---

## Cross-Sheet Consistency Checks (built into tasks above)

These critical cross-sheet validations are embedded in the test tasks:

1. **Retirement Income B4 matches Growth Projection F20** (Task 5: `test_b4_matches_growth_projection_retirement_row`)
2. **SIP Tracker 12-month sums match Growth Projection annual investments** (Task 6: `test_stepup_consistency_with_growth_projection`)
3. **Fund Allocation total matches Inputs total SIP** (Task 3: `test_d14_total_sip`)
4. **Portfolio = Equity + Debt+Gold+Cash in every row** (Task 4: `test_portfolio_equals_equity_plus_rest`)
5. **Gains = Portfolio - Cumulative in every row** (Task 4: `test_gains_equals_portfolio_minus_cumulative`)
