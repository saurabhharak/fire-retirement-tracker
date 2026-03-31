"""Test SIP Tracker Sheet: step-up timing, 192 months, fund columns, cross-sheet consistency."""
import pytest
from conftest import TOLERANCE, compute_monthly_sips, compute_growth_projection


class TestSIPTrackerFormulas:
    """Verify formula text in SIP Tracker."""

    def test_c5_month1_references_base_sip(self, wb):
        f = wb["SIP Tracker"]["C5"].value
        assert "B15" in f, f"C5 should reference Inputs!B15 (base SIP): {f}"

    def test_c6_month2_no_stepup(self, wb):
        """Month 2 should use IF(MOD...) pattern and NOT step up."""
        f = wb["SIP Tracker"]["C6"].value
        assert "IF(" in f.upper() or "if(" in f, f"C6 should use IF: {f}"
        assert "MOD(" in f.upper() or "mod(" in f, f"C6 should use MOD: {f}"

    def test_c17_month13_stepup(self, wb):
        """Month 13 should trigger first step-up."""
        f = wb["SIP Tracker"]["C17"].value
        assert "B16" in f, f"C17 should reference step-up (B16): {f}"

    @pytest.mark.parametrize("row", [5, 20, 50, 100, 150, 196])
    def test_difference_formula(self, wb, row):
        f = wb["SIP Tracker"][f"E{row}"].value
        assert "IF(" in f.upper(), f"E{row} should use IF: {f}"
        assert f"D{row}" in f, f"E{row} should reference D{row}: {f}"
        assert f"C{row}" in f, f"E{row} should reference C{row}: {f}"

    def test_totals_row_c197(self, wb):
        f = wb["SIP Tracker"]["C197"].value
        assert "SUM" in f.upper(), f"C197 should use SUM: {f}"
        assert "C5" in f and "C196" in f, f"C197 should sum C5:C196: {f}"

    def test_totals_row_d197(self, wb):
        f = wb["SIP Tracker"]["D197"].value
        assert "SUM" in f.upper(), f"D197 should use SUM: {f}"


class TestSIPTrackerStructure:
    """Verify SIP Tracker has correct structure."""

    def test_192_months_of_data(self, wb):
        ws = wb["SIP Tracker"]
        count = 0
        for row in range(5, 197):
            if ws[f"A{row}"].value is not None:
                count += 1
        assert count == 192, f"Expected 192 months, got {count}"

    def test_first_month_is_1(self, wb):
        assert wb["SIP Tracker"]["A5"].value == 1

    def test_last_month_is_192(self, wb):
        assert wb["SIP Tracker"]["A196"].value == 192

    def test_totals_row_label(self, wb):
        assert wb["SIP Tracker"]["A197"].value == "TOTAL"

    def test_all_10_fund_columns(self, wb):
        ws = wb["SIP Tracker"]
        expected = [
            ("F4", "Nifty50"), ("G4", "Next50"), ("H4", "Mid150"),
            ("J4", "Small250"), ("K4", "TotalMkt"), ("L4", "ShortDebt"),
            ("M4", "Arbitrage"), ("N4", "Liquid"), ("O4", "GoldETF"), ("P4", "Cash"),
        ]
        for cell, keyword in expected:
            val = ws[cell].value
            assert val is not None and keyword in str(val), (
                f"{cell} should contain '{keyword}', got: {val}"
            )

    def test_notes_column(self, wb):
        val = wb["SIP Tracker"]["I4"].value
        assert val is not None and "Notes" in str(val), f"I4 should be Notes: {val}"


class TestSIPTrackerMath:
    """Verify SIP step-up math and cross-sheet consistency."""

    @pytest.fixture(scope="class")
    def monthly_sips(self, inputs):
        return compute_monthly_sips(inputs)

    def test_months_1_to_12_base_sip(self, monthly_sips, inputs):
        for i in range(12):
            assert monthly_sips[i] == inputs["total_sip"], (
                f"Month {i+1}: got {monthly_sips[i]}, expected {inputs['total_sip']}"
            )

    def test_month_13_first_stepup(self, monthly_sips, inputs):
        expected = inputs["total_sip"] * (1 + inputs["step_up"])
        assert abs(monthly_sips[12] - expected) < TOLERANCE

    def test_months_13_to_24_same(self, monthly_sips):
        for i in range(12, 24):
            assert monthly_sips[i] == monthly_sips[12], (
                f"Month {i+1} should equal month 13"
            )

    @pytest.mark.parametrize("year_boundary", [13, 25, 37, 49, 61, 73, 85, 97, 109, 121, 133, 145, 157, 169, 181])
    def test_stepup_at_year_boundaries(self, monthly_sips, inputs, year_boundary):
        """SIP should step up at months 13, 25, 37, ..."""
        idx = year_boundary - 1  # 0-indexed
        prev_idx = idx - 1
        expected = monthly_sips[prev_idx] * (1 + inputs["step_up"])
        assert abs(monthly_sips[idx] - expected) < TOLERANCE, (
            f"Month {year_boundary}: got {monthly_sips[idx]:,.0f}, expected {expected:,.0f}"
        )

    def test_total_planned_sip(self, monthly_sips):
        """Total of 192 months should be a large positive number."""
        total = sum(monthly_sips)
        assert total > 100_000_000, f"Total planned SIP {total:,.0f} seems too low"

    def test_12month_sums_match_growth_projection(self, monthly_sips, inputs):
        """CRITICAL CROSS-CHECK: sum of 12 months in SIP Tracker must match
        Growth Projection Annual Investment for each year."""
        projection = compute_growth_projection(inputs)

        for year in range(1, inputs["years_to_retirement"] + 1):
            start_idx = (year - 1) * 12  # 0-indexed
            sip_12mo_sum = sum(monthly_sips[start_idx:start_idx + 12])
            gp_annual = projection[year]["annual_inv"]
            assert abs(sip_12mo_sum - gp_annual) < 1.0, (
                f"Year {year}: SIP Tracker 12mo sum ({sip_12mo_sum:,.0f}) != "
                f"Growth Projection annual ({gp_annual:,.0f})"
            )

    def test_sip_never_negative(self, monthly_sips):
        for i, sip in enumerate(monthly_sips):
            assert sip >= 0, f"Month {i+1}: negative SIP {sip}"

    def test_sip_monotonically_increasing(self, monthly_sips):
        """SIP should only increase (via annual step-up), never decrease."""
        for i in range(1, len(monthly_sips)):
            assert monthly_sips[i] >= monthly_sips[i-1], (
                f"Month {i+1} ({monthly_sips[i]:,.0f}) < Month {i} ({monthly_sips[i-1]:,.0f})"
            )
