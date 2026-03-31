"""Test Retirement Income Sheet: OFFSET, SWR scenarios, 3-bucket strategy."""
import pytest
from conftest import TOLERANCE, compute_growth_projection


class TestRetirementIncomeFormulas:
    """Verify formula text in Retirement Income sheet."""

    def test_b4_offset_uses_f4_not_f3(self, wb):
        """CRITICAL BUG FIX: OFFSET base must be F4 (not F3 = off-by-1)."""
        f = wb["Retirement Income"]["B4"].value
        assert "F4" in f, f"B4 OFFSET still uses wrong base (off-by-1 bug): {f}"
        assert "F3" not in f.replace("F4", ""), f"B4 has stale F3 reference: {f}"

    def test_b4_offset_references_years_to_retirement(self, wb):
        f = wb["Retirement Income"]["B4"].value
        assert "B8" in f or "B$8" in f, f"B4 should reference Inputs!B8: {f}"

    def test_b5_references_inputs_b37(self, wb):
        f = wb["Retirement Income"]["B5"].value
        assert "B37" in f, f"B5 should reference Inputs!B37: {f}"

    def test_b6_swp_formula(self, wb):
        f = wb["Retirement Income"]["B6"].value
        assert "B4" in f and "B25" in f and "12" in f, f"B6 should be B4*B25/12: {f}"

    def test_b7_references_inputs_b36(self, wb):
        f = wb["Retirement Income"]["B7"].value
        assert "B36" in f, f"B7 should reference Inputs!B36: {f}"

    def test_b8_surplus_formula(self, wb):
        f = wb["Retirement Income"]["B8"].value
        assert "B6" in f and "B7" in f, f"B8 should be B6-B7: {f}"

    def test_b9_funded_ratio_formula(self, wb):
        f = wb["Retirement Income"]["B9"].value
        assert "B4" in f and "B38" in f, f"B9 should be B4/Inputs!B38: {f}"

    def test_b10_references_inputs_b38(self, wb):
        f = wb["Retirement Income"]["B10"].value
        assert "B38" in f, f"B10 should reference Inputs!B38: {f}"

    # --- 3-Bucket Strategy formulas ---
    @pytest.mark.parametrize("row", [14, 15, 16])
    def test_bucket_amount_formula(self, wb, row):
        f = wb["Retirement Income"][f"C{row}"].value
        assert "B4" in f and f"B{row}" in f, f"C{row} should be B4*B{row}: {f}"

    def test_bucket_pcts_are_constants(self, wb):
        assert wb["Retirement Income"]["B14"].value == 0.08
        assert wb["Retirement Income"]["B15"].value == 0.27
        assert wb["Retirement Income"]["B16"].value == 0.65

    @pytest.mark.parametrize("row", [14, 15])
    def test_coverage_years_formula(self, wb, row):
        f = wb["Retirement Income"][f"E{row}"].value
        assert f"C{row}" in f and "B5" in f, f"E{row} should be C{row}/B5: {f}"

    # --- SWR Comparison formulas ---
    @pytest.mark.parametrize("row", [21, 22, 23, 24, 25])
    def test_swr_annual_formula(self, wb, row):
        f = wb["Retirement Income"][f"B{row}"].value
        assert "B4" in f and f"A{row}" in f, f"B{row} should be B4*A{row}: {f}"

    @pytest.mark.parametrize("row", [21, 22, 23, 24, 25])
    def test_swr_monthly_formula(self, wb, row):
        f = wb["Retirement Income"][f"C{row}"].value
        assert f"B{row}" in f and "12" in f, f"C{row} should be B{row}/12: {f}"

    @pytest.mark.parametrize("row", [21, 22, 23, 24, 25])
    def test_swr_vs_expense_formula(self, wb, row):
        f = wb["Retirement Income"][f"D{row}"].value
        assert f"C{row}" in f and "B7" in f, f"D{row} should be C{row}-B7: {f}"

    def test_swr_rates_correct(self, wb):
        assert wb["Retirement Income"]["A21"].value == 0.02
        assert wb["Retirement Income"]["A22"].value == 0.025
        assert wb["Retirement Income"]["A23"].value == 0.03
        assert wb["Retirement Income"]["A24"].value == 0.035
        assert wb["Retirement Income"]["A25"].value == 0.04


class TestRetirementIncomeMath:
    """Verify retirement math independently."""

    @pytest.fixture(scope="class")
    def corpus(self, inputs):
        proj = compute_growth_projection(inputs)
        return proj[inputs["years_to_retirement"]]["portfolio"]

    @pytest.fixture(scope="class")
    def annual_expense(self, inputs):
        return inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"] * 12

    @pytest.fixture(scope="class")
    def monthly_expense(self, inputs):
        return inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"]

    def test_corpus_matches_growth_projection_year16(self, corpus, inputs):
        proj = compute_growth_projection(inputs)
        assert abs(corpus - proj[16]["portfolio"]) < 0.01

    def test_monthly_swp_at_3pct(self, corpus, inputs):
        swp = corpus * inputs["swr"] / 12
        assert swp > 0

    def test_surplus_is_positive(self, corpus, inputs, monthly_expense):
        swp = corpus * inputs["swr"] / 12
        surplus = swp - monthly_expense
        assert surplus > 0, f"Monthly surplus negative: {surplus:,.0f} -- FIRE plan underfunded!"

    def test_funded_ratio_above_1(self, corpus, annual_expense, inputs):
        required = annual_expense / inputs["swr"]
        ratio = corpus / required
        assert ratio > 1.0, f"Funded ratio {ratio:.2f} < 1.0 -- FIRE target not met!"

    def test_bucket_percentages_sum_to_100(self):
        assert abs(0.08 + 0.27 + 0.65 - 1.0) < TOLERANCE

    def test_bucket_amounts_sum_to_corpus(self, corpus):
        b1 = corpus * 0.08
        b2 = corpus * 0.27
        b3 = corpus * 0.65
        assert abs((b1 + b2 + b3) - corpus) < 1.0

    def test_safety_bucket_covers_years(self, corpus, annual_expense):
        coverage = (corpus * 0.08) / annual_expense
        assert coverage > 1.0, f"Safety bucket covers only {coverage:.1f} years"

    def test_income_bucket_covers_years(self, corpus, annual_expense):
        coverage = (corpus * 0.27) / annual_expense
        assert coverage > 5.0, f"Income bucket covers only {coverage:.1f} years"

    @pytest.mark.parametrize("swr_rate,label", [
        (0.02, "Ultra Safe"), (0.025, "Very Safe"), (0.03, "Recommended"),
        (0.035, "Moderate"), (0.04, "Risky"),
    ])
    def test_swr_scenario_math(self, corpus, monthly_expense, swr_rate, label):
        annual = corpus * swr_rate
        monthly = annual / 12
        vs_expense = monthly - monthly_expense
        # At 2% SWR and above, should still have surplus given 2x+ funded ratio
        if swr_rate >= 0.02:
            assert vs_expense > 0, f"SWR {swr_rate*100}% ({label}): deficit of {vs_expense:,.0f}"

    def test_3pct_swr_matches_recommended(self, corpus, monthly_expense, inputs):
        """The 3% SWR row should match the main SWP calculation."""
        main_swp = corpus * inputs["swr"] / 12
        row_swp = corpus * 0.03 / 12
        assert abs(main_swp - row_swp) < TOLERANCE
