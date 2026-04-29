"""Tests for GRR ANOVA engine."""

from __future__ import annotations

import numpy as np
import pytest

from q_caliper.core.grr import calculate_grr


class TestGrrCalculation:
    """Test calculate_grr function."""

    def test_basic_grr(self) -> None:
        rng = np.random.default_rng(42)
        n_parts, n_ops, n_trials = 10, 3, 3
        data = rng.normal(loc=50, scale=1, size=n_parts * n_ops * n_trials)
        result = calculate_grr(data, n_parts, n_ops, n_trials)
        assert result.pct_grr >= 0
        assert result.ndc >= 0
        assert result.var_total >= 0

    def test_grr_components_sum(self) -> None:
        rng = np.random.default_rng(42)
        n_parts, n_ops, n_trials = 5, 3, 2
        data = rng.normal(loc=0, scale=1, size=n_parts * n_ops * n_trials)
        result = calculate_grr(data, n_parts, n_ops, n_trials)
        expected_total = (
            result.var_repeatability
            + result.var_reproducibility
            + result.var_interaction
            + result.var_parts
        )
        assert result.var_total == pytest.approx(expected_total, rel=1e-10)
