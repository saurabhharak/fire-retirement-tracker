"""Test Growth Projection Sheet: THE critical sheet. Verify every formula and every year."""
import pytest
from conftest import TOLERANCE, blended_return, compute_growth_projection


class TestGrowthProjectionFormulas:
    """Verify formula text in every cell of Growth Projection."""

    # --- Column B: Age ---
    @pytest.mark.parametrize("year", range(0, 41))
    def test_age_formula(self, wb, year):
        row = year + 4
        f = wb["Growth Projection"][f"B{row}"].value
        assert f.startswith("="), f"B{row} not a formula: {f}"
        assert "Inputs" in f and "B5" in f, f"B{row} should reference Inputs!B5: {f}"

    # --- Column C: Monthly SIP ---
    def test_c4_year0_sip(self, wb, inputs):
        """Year 0 shows base SIP (from Inputs!B15)."""
        f = wb["Growth Projection"]["C4"].value
        assert "B15" in f or f == f"=Inputs!B15", f"C4 should reference base SIP: {f}"

    def test_c5_year1_is_base_not_stepped_up(self, wb):
        """CRITICAL BUG FIX: Year 1 must use base SIP, NOT step-up."""
        f = wb["Growth Projection"]["C5"].value
        assert "B16" not in f, f"C5 still references step-up B16 (BUG!): {f}"
        assert "B15" in f, f"C5 should reference base SIP B15: {f}"

    @pytest.mark.parametrize("year", range(2, 17))
    def test_sip_during_accumulation_has_stepup(self, wb, year):
        """Years 2-16: formula should include step-up reference."""
        row = year + 4
        f = wb["Growth Projection"][f"C{row}"].value
        assert "B16" in f or "B$16" in f, f"C{row} should reference step-up (B16): {f}"

    @pytest.mark.parametrize("year", range(2, 41))
    def test_sip_has_retirement_condition(self, wb, year):
        """Years 2+: formula should have IF condition for retirement cutoff."""
        row = year + 4
        f = wb["Growth Projection"][f"C{row}"].value
        assert "IF(" in f.upper(), f"C{row} should have IF condition for retirement: {f}"
        assert "B$8" in f or "B8" in f, f"C{row} should reference years_to_retirement: {f}"

    # --- Column D: Annual Investment ---
    @pytest.mark.parametrize("year", range(1, 41))
    def test_annual_investment_formula(self, wb, year):
        row = year + 4
        f = wb["Growth Projection"][f"D{row}"].value
        assert f"C{row}" in f and "12" in f, f"D{row} should be C{row}*12: {f}"

    def test_d4_year0_is_zero(self, wb):
        """Year 0 has no investment (starting point)."""
        val = wb["Growth Projection"]["D4"].value
        assert val == 0, f"D4 should be 0: {val}"

    # --- Column E: Cumulative Invested ---
    def test_e4_year0_cumulative(self, wb):
        f = wb["Growth Projection"]["E4"].value
        assert "B17" in str(f), f"E4 should reference existing corpus (B17): {f}"

    @pytest.mark.parametrize("year", range(1, 41))
    def test_cumulative_formula(self, wb, year):
        row = year + 4
        f = wb["Growth Projection"][f"E{row}"].value
        assert f"E{row-1}" in f and f"D{row}" in f, f"E{row} should be E{row-1}+D{row}: {f}"

    # --- Column F: Portfolio Value (MOST CRITICAL) ---
    def test_f4_year0_portfolio(self, wb):
        f = wb["Growth Projection"]["F4"].value
        assert "B17" in str(f), f"F4 should reference existing corpus: {f}"

    @pytest.mark.parametrize("year", range(1, 41))
    def test_portfolio_uses_midyear_convention(self, wb, year):
        """CRITICAL BUG FIX: Must use mid-year convention (D*rate/2), not start-of-year."""
        row = year + 4
        f = wb["Growth Projection"][f"F{row}"].value
        # Should contain: F{row-1}*(1+rate) + D{row}*(1+rate/2)
        assert f"F{row-1}" in f, f"F{row} should reference F{row-1}: {f}"
        assert "/2" in f or "/ 2" in f, f"F{row} MISSING mid-year /2 factor (BUG!): {f}"
        assert f"D{row}" in f, f"F{row} should reference D{row}: {f}"
        assert "B$41" in f or "B41" in f, f"F{row} should reference blended return: {f}"

    @pytest.mark.parametrize("year", range(1, 41))
    def test_portfolio_not_start_of_year(self, wb, year):
        """Ensure old bug (F+D)*(1+r) is NOT present."""
        row = year + 4
        f = wb["Growth Projection"][f"F{row}"].value
        # Old formula pattern: (F{row-1}+D{row})*(1+...
        bad_pattern = f"(F{row-1}+D{row})"
        assert bad_pattern not in f, f"F{row} still uses start-of-year compounding (BUG!): {f}"

    # --- Column G: Total Gains ---
    @pytest.mark.parametrize("year", range(0, 41))
    def test_gains_formula(self, wb, year):
        row = year + 4
        val = wb["Growth Projection"][f"G{row}"].value
        if year == 0:
            assert val == 0, f"G{row} Year 0 gains should be 0: {val}"
        else:
            f = str(val)
            assert f"F{row}" in f and f"E{row}" in f, f"G{row} should be F{row}-E{row}: {f}"

    # --- Columns H & I: Equity / Non-equity split ---
    @pytest.mark.parametrize("year", range(0, 41))
    def test_equity_split_formula(self, wb, year):
        row = year + 4
        f = wb["Growth Projection"][f"H{row}"].value
        assert f"F{row}" in str(f) and "B28" in str(f), f"H{row} should be F{row}*Inputs!B28: {f}"

    @pytest.mark.parametrize("year", range(0, 41))
    def test_non_equity_split_formula(self, wb, year):
        row = year + 4
        f = wb["Growth Projection"][f"I{row}"].value
        assert f"F{row}" in str(f), f"I{row} should reference F{row}: {f}"


class TestGrowthProjectionMath:
    """Verify math independently using Python simulation."""

    @pytest.fixture(scope="class")
    def projection(self, inputs):
        return compute_growth_projection(inputs)

    def test_year0_portfolio_is_existing_corpus(self, projection, inputs):
        assert projection[0]["portfolio"] == inputs["existing_corpus"]

    def test_year0_no_investment(self, projection):
        assert projection[0]["annual_inv"] == 0

    def test_year0_gains_zero(self, projection):
        assert projection[0]["gains"] == 0

    def test_year1_uses_base_sip(self, projection, inputs):
        """CRITICAL: Year 1 SIP must be base (325000), not stepped up."""
        assert projection[1]["monthly_sip"] == inputs["total_sip"]
        assert projection[1]["annual_inv"] == inputs["total_sip"] * 12

    def test_year2_first_stepup(self, projection, inputs):
        """Year 2 should be first step-up."""
        expected = inputs["total_sip"] * (1 + inputs["step_up"])
        assert abs(projection[2]["monthly_sip"] - expected) < TOLERANCE

    @pytest.mark.parametrize("year", range(2, 17))
    def test_stepup_chain(self, projection, inputs, year):
        """Each accumulation year's SIP = previous * (1+step_up)."""
        expected = projection[year - 1]["monthly_sip"] * (1 + inputs["step_up"])
        assert abs(projection[year]["monthly_sip"] - expected) < TOLERANCE, (
            f"Year {year}: got {projection[year]['monthly_sip']}, expected {expected}"
        )

    @pytest.mark.parametrize("year", range(17, 41))
    def test_post_retirement_sip_zero(self, projection, year):
        """Post-retirement: SIP must be 0."""
        assert projection[year]["monthly_sip"] == 0
        assert projection[year]["annual_inv"] == 0

    @pytest.mark.parametrize("year", range(1, 41))
    def test_portfolio_compounding(self, projection, inputs, year):
        """Verify mid-year compounding formula: prev*(1+r) + annual*(1+r/2)."""
        prev = projection[year - 1]["portfolio"]
        annual = projection[year]["annual_inv"]
        br = blended_return(inputs)
        expected = prev * (1 + br) + annual * (1 + br / 2)
        actual = projection[year]["portfolio"]
        tolerance = max(1.0, abs(expected) * 1e-12)
        assert abs(actual - expected) < tolerance, (
            f"Year {year}: portfolio {actual:,.0f} != {expected:,.0f}"
        )

    @pytest.mark.parametrize("year", range(0, 41))
    def test_gains_equals_portfolio_minus_cumulative(self, projection, year):
        """Gains = Portfolio - Cumulative Invested."""
        p = projection[year]
        assert abs(p["gains"] - (p["portfolio"] - p["cumulative"])) < 0.01

    @pytest.mark.parametrize("year", range(0, 41))
    def test_equity_plus_rest_equals_portfolio(self, projection, year):
        """Equity + Debt+Gold+Cash = Portfolio."""
        p = projection[year]
        assert abs((p["equity_value"] + p["debt_gold_cash"]) - p["portfolio"]) < 0.01

    def test_retirement_corpus_reasonable(self, projection):
        """Sanity: corpus at retirement should be between 20Cr and 50Cr."""
        corpus = projection[16]["portfolio"]
        assert 200_000_000 < corpus < 500_000_000, f"Retirement corpus {corpus:,.0f} seems unreasonable"

    def test_cumulative_always_increasing(self, projection):
        """Cumulative invested should never decrease."""
        for i in range(1, len(projection)):
            assert projection[i]["cumulative"] >= projection[i-1]["cumulative"]

    def test_portfolio_always_increasing_during_accumulation(self, projection):
        """Portfolio should grow every year during accumulation."""
        for year in range(1, 17):
            assert projection[year]["portfolio"] > projection[year-1]["portfolio"], (
                f"Year {year}: portfolio decreased"
            )

    def test_portfolio_still_grows_post_retirement(self, projection):
        """Even without SIP, portfolio should grow (returns > 0)."""
        for year in range(17, 41):
            assert projection[year]["portfolio"] > projection[year-1]["portfolio"]
