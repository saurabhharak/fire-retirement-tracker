"""Test Inputs Sheet: verify all formula cells and constant values."""
import pytest
from conftest import TOLERANCE, blended_return


class TestInputsConstants:
    """Verify raw input constants are correctly stored."""

    def test_b4_dob(self, wb):
        val = wb["Inputs"]["B4"].value
        assert val is not None, "B4 DOB is empty"

    def test_b6_retirement_age(self, wb, inputs):
        assert wb["Inputs"]["B6"].value == inputs["retirement_age"]

    def test_b7_life_expectancy(self, wb, inputs):
        assert wb["Inputs"]["B7"].value == inputs["life_expectancy"]

    def test_b13_your_sip(self, wb, inputs):
        assert wb["Inputs"]["B13"].value == inputs["your_sip"]

    def test_b14_wife_sip(self, wb, inputs):
        assert wb["Inputs"]["B14"].value == inputs["wife_sip"]

    def test_b16_step_up(self, wb, inputs):
        assert wb["Inputs"]["B16"].value == inputs["step_up"]

    def test_b17_existing_corpus(self, wb, inputs):
        assert wb["Inputs"]["B17"].value == inputs["existing_corpus"]

    def test_b20_equity_return(self, wb, inputs):
        assert wb["Inputs"]["B20"].value == inputs["equity_return"]

    def test_b21_debt_return(self, wb, inputs):
        assert wb["Inputs"]["B21"].value == inputs["debt_return"]

    def test_b22_gold_return(self, wb, inputs):
        assert wb["Inputs"]["B22"].value == inputs["gold_return"]

    def test_b23_cash_return(self, wb, inputs):
        assert wb["Inputs"]["B23"].value == inputs["cash_return"]

    def test_b24_inflation(self, wb, inputs):
        assert wb["Inputs"]["B24"].value == inputs["inflation"]

    def test_b25_swr(self, wb, inputs):
        assert wb["Inputs"]["B25"].value == inputs["swr"]

    def test_b28_equity_pct(self, wb, inputs):
        assert wb["Inputs"]["B28"].value == inputs["equity_pct"]

    def test_b29_debt_pct(self, wb, inputs):
        assert wb["Inputs"]["B29"].value == inputs["debt_pct"]

    def test_b30_gold_pct(self, wb, inputs):
        assert wb["Inputs"]["B30"].value == inputs["gold_pct"]

    def test_b31_cash_pct(self, wb, inputs):
        assert wb["Inputs"]["B31"].value == inputs["cash_pct"]

    def test_b35_monthly_expense(self, wb, inputs):
        assert wb["Inputs"]["B35"].value == inputs["monthly_expense"]


class TestInputsFormulas:
    """Verify every formula cell has the correct formula text."""

    def test_b5_age_formula(self, wb):
        f = wb["Inputs"]["B5"].value
        assert f.startswith("="), f"B5 not a formula: {f}"
        assert "DATEDIF" in f, f"B5 should use DATEDIF: {f}"
        assert "TODAY()" in f, f"B5 should reference TODAY(): {f}"

    def test_b8_years_to_retirement(self, wb):
        f = wb["Inputs"]["B8"].value
        assert f == "=B6-B5", f"B8: got '{f}', expected '=B6-B5'"

    def test_b9_retirement_duration(self, wb):
        f = wb["Inputs"]["B9"].value
        assert f == "=B7-B6", f"B9: got '{f}', expected '=B7-B6'"

    def test_b15_total_sip(self, wb):
        f = wb["Inputs"]["B15"].value
        assert f == "=B13+B14", f"B15: got '{f}', expected '=B13+B14'"

    def test_b32_allocation_total(self, wb):
        f = wb["Inputs"]["B32"].value
        assert f == "=B28+B29+B30+B31", f"B32: got '{f}'"

    def test_b36_monthly_expense_at_retirement(self, wb):
        f = wb["Inputs"]["B36"].value
        assert "B35" in f, f"B36 should reference B35 (monthly expense): {f}"
        assert "B24" in f, f"B36 should reference B24 (inflation): {f}"
        assert "B8" in f, f"B36 should reference B8 (years to retirement): {f}"

    def test_b37_annual_expense(self, wb):
        f = wb["Inputs"]["B37"].value
        assert "B36" in f and "12" in f, f"B37 should be B36*12: {f}"

    def test_b38_required_corpus(self, wb):
        f = wb["Inputs"]["B38"].value
        assert "B37" in f and "B25" in f, f"B38 should be B37/B25: {f}"

    def test_b41_blended_return(self, wb):
        f = wb["Inputs"]["B41"].value
        for cell in ["B28", "B20", "B29", "B21", "B30", "B22", "B31", "B23"]:
            assert cell in f, f"B41 missing reference to {cell}: {f}"

    def test_b42_uses_fisher_equation(self, wb):
        """CRITICAL: Real Return must use Fisher equation, not simple subtraction."""
        f = wb["Inputs"]["B42"].value
        assert "/(1+" in f or "/ (1+" in f, f"B42 doesn't use Fisher equation: {f}"
        assert "B41" in f, f"B42 should reference B41 (blended return): {f}"
        assert "B24" in f, f"B42 should reference B24 (inflation): {f}"

    def test_b42_is_not_simple_subtraction(self, wb):
        """Ensure the old bug (B41-B24) is fixed."""
        f = wb["Inputs"]["B42"].value
        assert f != "=B41-B24", f"B42 still uses simple subtraction: {f}"


class TestInputsMath:
    """Verify the MATH is correct using independent Python computation."""

    def test_years_to_retirement(self, inputs):
        assert inputs["retirement_age"] - inputs["current_age"] == 16

    def test_retirement_duration(self, inputs):
        assert inputs["life_expectancy"] - inputs["retirement_age"] == 45

    def test_total_sip(self, inputs):
        assert inputs["your_sip"] + inputs["wife_sip"] == 325_000

    def test_allocation_sums_to_100(self, inputs):
        total = inputs["equity_pct"] + inputs["debt_pct"] + inputs["gold_pct"] + inputs["cash_pct"]
        assert abs(total - 1.0) < TOLERANCE

    def test_blended_return(self, inputs):
        br = blended_return(inputs)
        assert abs(br - 0.10) < TOLERANCE, f"Blended return: {br}, expected 0.10"

    def test_real_return_fisher(self, inputs):
        br = blended_return(inputs)
        real = (1 + br) / (1 + inputs["inflation"]) - 1
        assert abs(real - 0.032863849) < 0.0001, f"Fisher real return: {real}"
        # Verify it differs from simple subtraction
        simple = br - inputs["inflation"]
        assert abs(real - simple) > 0.001, "Fisher should differ from simple subtraction"

    def test_monthly_expense_at_retirement(self, inputs):
        expected = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"]
        assert abs(expected - 342376.33) < 1.0, f"Monthly expense at retirement: {expected}"

    def test_annual_expense_at_retirement(self, inputs):
        monthly = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"]
        annual = monthly * 12
        assert abs(annual - 4108516.0) < 1.0, f"Annual expense at retirement: {annual}"

    def test_required_corpus(self, inputs):
        annual = inputs["monthly_expense"] * (1 + inputs["inflation"]) ** inputs["years_to_retirement"] * 12
        required = annual / inputs["swr"]
        assert abs(required - 136950533.6) < 1.0, f"Required corpus: {required}"
