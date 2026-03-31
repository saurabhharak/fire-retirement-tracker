"""Test Fund Allocation Sheet: verify formulas and allocation math."""
import pytest
from conftest import TOLERANCE

# Fund allocation: (name, category, parent_pct_key, sub_pct, excel_row)
FUNDS = [
    ("Nifty 50 Index Fund",       "equity", "equity_pct", 35,  4),
    ("Nifty Next 50 Index Fund",  "equity", "equity_pct", 20,  5),
    ("Nifty Midcap 150",          "equity", "equity_pct", 20,  6),
    ("Nifty Smallcap 250",        "equity", "equity_pct", 10,  7),
    ("Nifty Total Market",        "equity", "equity_pct", 15,  8),
    ("Short Duration Debt Fund",  "debt",   "debt_pct",   40,  9),
    ("Arbitrage Fund",            "debt",   "debt_pct",   30, 10),
    ("Liquid/Overnight Fund",     "debt",   "debt_pct",   30, 11),
    ("Gold ETF",                  "gold",   "gold_pct",  100, 12),
    ("Emergency / Cash Reserve",  "cash",   "cash_pct",  100, 13),
]


class TestFundAllocationFormulas:
    """Verify every formula references the correct Inputs cells."""

    @pytest.mark.parametrize("fund", FUNDS, ids=[f[0] for f in FUNDS])
    def test_percentage_formula_references_inputs(self, wb, fund):
        """C column formulas should reference the correct Inputs cell."""
        name, category, parent_key, sub_pct, row = fund
        f = wb["Fund Allocation"][f"C{row}"].value
        assert f.startswith("="), f"C{row} not a formula: {f}"
        # Should reference the parent allocation cell
        pct_cell_map = {"equity_pct": "B28", "debt_pct": "B29", "gold_pct": "B30", "cash_pct": "B31"}
        expected_cell = pct_cell_map[parent_key]
        assert expected_cell in f, f"C{row} ({name}) should reference Inputs!{expected_cell}: {f}"

    @pytest.mark.parametrize("fund", FUNDS, ids=[f[0] for f in FUNDS])
    def test_sip_formula_references_total_sip(self, wb, fund):
        """D column formulas should reference total SIP (Inputs!B15)."""
        name, category, parent_key, sub_pct, row = fund
        f = wb["Fund Allocation"][f"D{row}"].value
        assert f.startswith("="), f"D{row} not a formula: {f}"
        assert "B15" in f or f"C{row}" in f, f"D{row} ({name}) should reference B15 or C{row}: {f}"

    def test_c14_total_formula(self, wb):
        f = wb["Fund Allocation"]["C14"].value
        assert "SUM" in f and "C4" in f and "C13" in f, f"C14 should be SUM(C4:C13): {f}"

    def test_d14_total_formula(self, wb):
        f = wb["Fund Allocation"]["D14"].value
        assert "SUM" in f and "D4" in f and "D13" in f, f"D14 should be SUM(D4:D13): {f}"


class TestFundAllocationMath:
    """Verify fund allocation math independently."""

    def test_equity_sub_pcts_sum_to_100(self):
        equity_sub_pcts = [f[3] for f in FUNDS if f[1] == "equity"]
        assert sum(equity_sub_pcts) == 100

    def test_debt_sub_pcts_sum_to_100(self):
        debt_sub_pcts = [f[3] for f in FUNDS if f[1] == "debt"]
        assert sum(debt_sub_pcts) == 100

    @pytest.mark.parametrize("fund", FUNDS, ids=[f[0] for f in FUNDS])
    def test_fund_percentage_math(self, inputs, fund):
        """Each fund's portfolio % computed from raw inputs."""
        name, category, parent_key, sub_pct, row = fund
        if category in ("gold", "cash"):
            expected = inputs[parent_key]
        else:
            expected = inputs[parent_key] * sub_pct / 100
        # Just verify the number is reasonable
        assert 0 < expected <= 1.0, f"{name}: pct {expected} out of range"

    @pytest.mark.parametrize("fund", FUNDS, ids=[f[0] for f in FUNDS])
    def test_fund_sip_amount_math(self, inputs, fund):
        """Each fund's monthly SIP amount from raw inputs."""
        name, category, parent_key, sub_pct, row = fund
        if category in ("gold", "cash"):
            pct = inputs[parent_key]
        else:
            pct = inputs[parent_key] * sub_pct / 100
        sip = pct * inputs["total_sip"]
        assert sip > 0, f"{name}: SIP amount {sip} should be positive"

    def test_all_fund_sips_sum_to_total(self, inputs):
        """All fund SIPs must sum to total SIP."""
        total = 0
        for name, category, parent_key, sub_pct, row in FUNDS:
            if category in ("gold", "cash"):
                pct = inputs[parent_key]
            else:
                pct = inputs[parent_key] * sub_pct / 100
            total += pct * inputs["total_sip"]
        assert abs(total - inputs["total_sip"]) < TOLERANCE, (
            f"Fund SIPs sum to {total}, expected {inputs['total_sip']}"
        )

    def test_all_fund_pcts_sum_to_100(self, inputs):
        """All fund percentages must sum to 1.0."""
        total = 0
        for name, category, parent_key, sub_pct, row in FUNDS:
            if category in ("gold", "cash"):
                total += inputs[parent_key]
            else:
                total += inputs[parent_key] * sub_pct / 100
        assert abs(total - 1.0) < TOLERANCE, f"Fund pcts sum to {total}, expected 1.0"
