"""Tests for GRR ANOVA engine."""

from __future__ import annotations

import numpy as np
import pytest

from q_caliper.core.grr import calculate_grr, validate_grr_data


class TestGrrValidation:
    """Test validate_grr_data function."""

    def test_valid_params(self) -> None:
        issues = validate_grr_data(10, 3, 3, 90)
        assert len(issues) == 0

    def test_too_few_parts(self) -> None:
        issues = validate_grr_data(1, 3, 3, 9)
        assert any("零件数" in m for m in issues)

    def test_too_few_operators(self) -> None:
        issues = validate_grr_data(10, 1, 3, 30)
        assert any("操作者" in m for m in issues)

    def test_mismatched_data_count(self) -> None:
        issues = validate_grr_data(10, 3, 3, 50)
        assert any("不匹配" in m for m in issues)


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

    def test_anova_table(self) -> None:
        rng = np.random.default_rng(42)
        n_parts, n_ops, n_trials = 10, 3, 3
        data = rng.normal(loc=50, scale=1, size=n_parts * n_ops * n_trials)
        result = calculate_grr(data, n_parts, n_ops, n_trials)
        assert len(result.anova_table) == 5
        assert result.anova_table[-1].source == "合计 (Total)"

    def test_chart_data(self) -> None:
        rng = np.random.default_rng(42)
        n_parts, n_ops, n_trials = 5, 3, 2
        data = rng.normal(loc=0, scale=1, size=n_parts * n_ops * n_trials)
        result = calculate_grr(data, n_parts, n_ops, n_trials)
        assert len(result.part_means) == n_parts
        assert len(result.operator_means) == n_ops
        assert result.raw_data.shape == (n_parts, n_ops, n_trials)
