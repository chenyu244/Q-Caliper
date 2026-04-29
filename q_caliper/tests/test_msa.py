"""Tests for MSA (Measurement System Analysis) engine."""

from __future__ import annotations

import numpy as np
import pytest

from q_caliper.core.msa import analyze_bias, analyze_linearity


class TestBiasAnalysis:
    """Test bias analysis."""

    def test_no_bias(self) -> None:
        rng = np.random.default_rng(42)
        data = rng.normal(loc=100, scale=1, size=50)
        result = analyze_bias(data, reference_value=100)
        assert abs(result.mean_bias) < 1.0
        assert result.pct_bias < 5

    def test_significant_bias(self) -> None:
        rng = np.random.default_rng(42)
        data = rng.normal(loc=105, scale=0.5, size=50)
        result = analyze_bias(data, reference_value=100)
        assert result.is_significant is True
        assert result.mean_bias > 0

    def test_confidence_interval(self) -> None:
        rng = np.random.default_rng(42)
        data = rng.normal(loc=50, scale=2, size=30)
        result = analyze_bias(data, reference_value=50)
        assert result.ci_lower < result.observed_mean < result.ci_upper


class TestLinearityAnalysis:
    """Test linearity analysis."""

    def test_perfect_linearity(self) -> None:
        refs = np.array([10, 20, 30, 40, 50], dtype=float)
        means = refs.copy()
        result = analyze_linearity(refs, means, process_variation=30)
        assert result.slope == pytest.approx(0.0, abs=0.01)
        assert result.r_squared < 0.01

    def test_proportional_bias(self) -> None:
        refs = np.array([10, 20, 30, 40, 50], dtype=float)
        means = refs * 1.05 + 2
        result = analyze_linearity(refs, means, process_variation=30)
        assert result.slope > 0
        assert result.r_squared > 0.8

    def test_too_few_points(self) -> None:
        with pytest.raises(ValueError, match="At least 3"):
            analyze_linearity([1, 2], [1, 2], process_variation=1)
