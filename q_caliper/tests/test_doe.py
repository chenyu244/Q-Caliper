"""Tests for DOE design engine."""

from __future__ import annotations

import pytest

from q_caliper.core.doe import fractional_factorial, full_factorial


class TestFullFactorial:
    """Test full factorial design generation."""

    def test_2_factor_design(self) -> None:
        design = full_factorial(2, randomize=False)
        assert design.n_runs == 4
        assert design.n_factors == 2
        assert design.design_matrix.shape == (4, 2)

    def test_3_factor_design(self) -> None:
        design = full_factorial(3, randomize=False)
        assert design.n_runs == 8
        assert design.n_factors == 3

    def test_custom_factor_names(self) -> None:
        design = full_factorial(2, factor_names=["Temp", "Pressure"], randomize=False)
        assert design.factor_names == ["Temp", "Pressure"]

    def test_invalid_factors(self) -> None:
        with pytest.raises(ValueError):
            full_factorial(0)


class TestFractionalFactorial:
    """Test fractional factorial design generation."""

    def test_half_fraction_3_factors(self) -> None:
        design = fractional_factorial(3, randomize=False)
        assert design.n_runs == 4
        assert design.n_factors == 3

    def test_too_few_factors(self) -> None:
        with pytest.raises(ValueError):
            fractional_factorial(2)
