"""Unit tests for precious_metals_svc pure functions.

Tests constants, purity factors, sanity bounds, purity rate computation,
and sanity-check logic for all three metals (gold, silver, platinum).
"""

import pytest

from app.services.precious_metals_svc import (
    METAL_TYPES,
    PURITY_FACTORS,
    PURE_PURITY,
    SANITY_BOUNDS,
    GOLDAPI_SYMBOLS,
    TROY_OZ_TO_GRAMS,
    MEMORY_CACHE_SECONDS,
    DB_CACHE_SECONDS,
    compute_purity_rates,
    is_rate_sane,
)


# ===================================================================
# Constants validation
# ===================================================================


class TestConstants:
    """Verify all module-level constants are correctly defined."""

    def test_metal_types_tuple(self):
        assert METAL_TYPES == ("gold", "silver", "platinum")

    def test_troy_oz_to_grams(self):
        assert TROY_OZ_TO_GRAMS == 31.1035

    def test_memory_cache_seconds(self):
        assert MEMORY_CACHE_SECONDS == 6 * 3600

    def test_db_cache_seconds(self):
        assert DB_CACHE_SECONDS == 12 * 3600

    def test_goldapi_symbols(self):
        assert GOLDAPI_SYMBOLS == {"gold": "XAU", "silver": "XAG", "platinum": "XPT"}


# ===================================================================
# Purity factors: verify all 9 purities
# ===================================================================


class TestPurityFactors:
    """Verify PURITY_FACTORS contains correct values for all metals."""

    # Gold purities
    def test_gold_24k(self):
        assert PURITY_FACTORS["gold"]["24K"] == 1.0

    def test_gold_22k(self):
        assert PURITY_FACTORS["gold"]["22K"] == pytest.approx(22 / 24)

    def test_gold_18k(self):
        assert PURITY_FACTORS["gold"]["18K"] == pytest.approx(18 / 24)

    # Silver purities
    def test_silver_999(self):
        assert PURITY_FACTORS["silver"]["999"] == 1.0

    def test_silver_925(self):
        assert PURITY_FACTORS["silver"]["925"] == 0.925

    def test_silver_900(self):
        assert PURITY_FACTORS["silver"]["900"] == 0.90

    # Platinum purities
    def test_platinum_999(self):
        assert PURITY_FACTORS["platinum"]["999"] == 1.0

    def test_platinum_950(self):
        assert PURITY_FACTORS["platinum"]["950"] == 0.95

    def test_platinum_900(self):
        assert PURITY_FACTORS["platinum"]["900"] == 0.90

    def test_pure_purity_map(self):
        assert PURE_PURITY == {"gold": "24K", "silver": "999", "platinum": "999"}


# ===================================================================
# Sanity bounds: verify bounds for all 3 metals
# ===================================================================


class TestSanityBounds:
    """Verify SANITY_BOUNDS per-metal min/max are correctly defined."""

    def test_gold_bounds(self):
        assert SANITY_BOUNDS["gold"] == (1000, 500000)

    def test_silver_bounds(self):
        assert SANITY_BOUNDS["silver"] == (50, 500)

    def test_platinum_bounds(self):
        assert SANITY_BOUNDS["platinum"] == (1000, 200000)

    def test_all_metals_have_bounds(self):
        for metal in METAL_TYPES:
            assert metal in SANITY_BOUNDS
            low, high = SANITY_BOUNDS[metal]
            assert low > 0
            assert high > low


# ===================================================================
# compute_purity_rates: verify rate derivation per metal
# ===================================================================


class TestComputePurityRates:
    """Test compute_purity_rates for each metal type."""

    def test_gold_purity_rates(self):
        """Gold at 8000 INR/gram pure -> 22K and 18K derived."""
        rates = compute_purity_rates("gold", 8000.0)
        assert rates["24K"] == 8000.0
        assert rates["22K"] == pytest.approx(8000.0 * 22 / 24, rel=1e-4)
        assert rates["18K"] == pytest.approx(8000.0 * 18 / 24, rel=1e-4)

    def test_silver_purity_rates(self):
        """Silver at 100 INR/gram pure -> 925 and 900 derived."""
        rates = compute_purity_rates("silver", 100.0)
        assert rates["999"] == 100.0
        assert rates["925"] == pytest.approx(100.0 * 0.925, rel=1e-4)
        assert rates["900"] == pytest.approx(100.0 * 0.90, rel=1e-4)

    def test_platinum_purity_rates(self):
        """Platinum at 3000 INR/gram pure -> 950 and 900 derived."""
        rates = compute_purity_rates("platinum", 3000.0)
        assert rates["999"] == 3000.0
        assert rates["950"] == pytest.approx(3000.0 * 0.95, rel=1e-4)
        assert rates["900"] == pytest.approx(3000.0 * 0.90, rel=1e-4)

    def test_rates_are_rounded(self):
        """All rates should be rounded to 2 decimal places."""
        rates = compute_purity_rates("gold", 7777.777)
        for key, value in rates.items():
            assert value == round(value, 2), f"{key} not rounded to 2dp"

    def test_silver_rates_are_rounded(self):
        rates = compute_purity_rates("silver", 88.888)
        for key, value in rates.items():
            assert value == round(value, 2), f"{key} not rounded to 2dp"


# ===================================================================
# is_rate_sane: valid and invalid for each metal
# ===================================================================


class TestIsRateSane:
    """Test is_rate_sane for boundary and out-of-range values."""

    # Gold: bounds (1000, 500000)
    def test_gold_valid_mid_range(self):
        assert is_rate_sane("gold", 8000.0) is True

    def test_gold_valid_lower_bound(self):
        assert is_rate_sane("gold", 1000.0) is True

    def test_gold_valid_upper_bound(self):
        assert is_rate_sane("gold", 500000.0) is True

    def test_gold_invalid_below(self):
        assert is_rate_sane("gold", 999.99) is False

    def test_gold_invalid_above(self):
        assert is_rate_sane("gold", 500000.01) is False

    # Silver: bounds (50, 500)
    def test_silver_valid_mid_range(self):
        assert is_rate_sane("silver", 100.0) is True

    def test_silver_valid_lower_bound(self):
        assert is_rate_sane("silver", 50.0) is True

    def test_silver_valid_upper_bound(self):
        assert is_rate_sane("silver", 500.0) is True

    def test_silver_invalid_below(self):
        assert is_rate_sane("silver", 49.99) is False

    def test_silver_invalid_above(self):
        assert is_rate_sane("silver", 500.01) is False

    # Platinum: bounds (1000, 200000)
    def test_platinum_valid_mid_range(self):
        assert is_rate_sane("platinum", 3000.0) is True

    def test_platinum_valid_lower_bound(self):
        assert is_rate_sane("platinum", 1000.0) is True

    def test_platinum_valid_upper_bound(self):
        assert is_rate_sane("platinum", 200000.0) is True

    def test_platinum_invalid_below(self):
        assert is_rate_sane("platinum", 999.99) is False

    def test_platinum_invalid_above(self):
        assert is_rate_sane("platinum", 200000.01) is False

    # Edge: negative and zero
    def test_zero_rate_is_insane(self):
        for metal in METAL_TYPES:
            assert is_rate_sane(metal, 0.0) is False

    def test_negative_rate_is_insane(self):
        for metal in METAL_TYPES:
            assert is_rate_sane(metal, -100.0) is False
