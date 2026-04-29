"""Tests for SPC chart engine."""

from __future__ import annotations

import numpy as np

from q_caliper.core.spc import ControlLimits, detect_violations, imr_chart, xbar_r_chart


class TestXbarRChart:
    """Test XBar-R chart generation."""

    def test_basic_chart(self) -> None:
        rng = np.random.default_rng(42)
        data = rng.normal(loc=100, scale=2, size=50)
        xbar, r_chart = xbar_r_chart(data, subgroup_size=5)
        assert len(xbar.values) == 10
        assert len(r_chart.values) == 10
        assert xbar.limits.ucl > xbar.limits.cl > xbar.limits.lcl


class TestImrChart:
    """Test I-MR chart generation."""

    def test_basic_chart(self) -> None:
        rng = np.random.default_rng(42)
        data = rng.normal(loc=50, scale=1, size=30)
        i_chart, mr_chart = imr_chart(data)
        assert len(i_chart.values) == 30
        assert len(mr_chart.values) == 29


class TestViolationDetection:
    """Test Western Electric rule violation detection."""

    def test_no_violations_in_stable_process(self) -> None:
        rng = np.random.default_rng(42)
        values = rng.normal(loc=100, scale=1, size=20).tolist()
        limits = ControlLimits(ucl=103, cl=100, lcl=97)
        violations = detect_violations(values, limits)
        assert len(violations) == 0

    def test_detects_out_of_control(self) -> None:
        values = [100.0] * 10 + [110.0]
        limits = ControlLimits(ucl=103, cl=100, lcl=97)
        violations = detect_violations(values, limits)
        assert any(v.rule == "Rule 1" for v in violations)
