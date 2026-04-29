"""Tests for Cpk/Ppk calculation engine."""

from __future__ import annotations

import numpy as np
import pytest

from q_caliper.core.cpk import calculate_cpk, normality_test


class TestNormalityTest:
    """Test normality_test function."""

    def test_normal_data(self) -> None:
        rng = np.random.default_rng(42)
        data = rng.normal(loc=100, scale=5, size=100)
        result = normality_test(data)
        assert result.is_normal
        assert result.test_name == "Shapiro-Wilk"

    def test_uniform_data_not_normal(self) -> None:
        rng = np.random.default_rng(42)
        data = rng.uniform(low=0, high=100, size=200)
        result = normality_test(data, alpha=0.01)
        assert not result.is_normal

    def test_too_few_points(self) -> None:
        with pytest.raises(ValueError, match="at least 8"):
            normality_test([1, 2, 3])


class TestCpkCalculation:
    """Test calculate_cpk function."""

    def test_symmetric_specs(self) -> None:
        rng = np.random.default_rng(42)
        data = rng.normal(loc=100, scale=2, size=100)
        result = calculate_cpk(data, usl=110, lsl=90)
        assert result.cp > 1.0
        assert result.cpk > 1.0
        assert result.mean == pytest.approx(100, abs=2)

    def test_one_sided_usl(self) -> None:
        data = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        result = calculate_cpk(data, usl=25)
        assert result.cpk > 0

    def test_both_specs_required(self) -> None:
        with pytest.raises(ValueError, match=r"[Aa]t least one"):
            calculate_cpk([1, 2, 3])
