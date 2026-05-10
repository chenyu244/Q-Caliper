"""Tests for Cpk/Ppk calculation engine."""

from __future__ import annotations

import numpy as np
import pytest

from q_caliper.core.cpk import calculate_capability, normality_test


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
        with pytest.raises(ValueError, match="至少需要 8 个数据点"):
            normality_test([1, 2, 3])


class TestCpkCalculation:
    """Test calculate_capability function."""

    def test_basic_calculation(self) -> None:
        """测试基本计算，验证所有指标都存在。"""
        rng = np.random.default_rng(42)
        data = rng.normal(loc=100, scale=2, size=100)
        result = calculate_capability(data, usl=110, lsl=90)

        assert result.mean == pytest.approx(100, abs=0.5)
        assert hasattr(result, "cpk")
        assert hasattr(result, "cmk")
        assert hasattr(result, "ppk")
        assert result.cpk > 0
        assert result.cmk > 0
        assert result.ppk > 0
        assert result.analysis_mode == "cpk_individual"  # 默认 subgroup_size=1

    def test_grouped_calculation(self) -> None:
        """测试子组计算 (Xbar-R 方法)。"""
        # 生成 10 组，每组 5 个数据
        data = np.random.normal(100, 1, 50)
        result = calculate_capability(data, usl=105, lsl=95, subgroup_size=5)

        assert result.analysis_mode == "cpk_grouped"
        assert result.num_subgroups == 10
        assert result.sample_size == 50
        assert result.cpk > 0

    def test_individual_calculation(self) -> None:
        """测试单值计算 (I-MR 方法)。"""
        data = np.random.normal(100, 1, 25)
        result = calculate_capability(data, usl=105, lsl=95, subgroup_size=1)

        assert result.analysis_mode == "cpk_individual"
        assert result.num_subgroups == 24  # n-1
        assert result.cpk > 0

    def test_one_sided_usl(self) -> None:
        data = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        result = calculate_capability(data, usl=25)
        assert result.cpk > 0
        assert result.pct_below_lsl == 0.0

    def test_validation_errors(self) -> None:
        """测试异常处理。"""
        # 1. 缺少规格限
        with pytest.raises(ValueError, match="必须至少指定 USL 或 LSL 其中之一"):
            calculate_capability([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        # 2. 数据点太少
        with pytest.raises(ValueError, match="至少需要 8 个数据点"):
            calculate_capability([1, 2, 3], usl=10)

        # 3. 子组太少 (n=12, subgroup_size=10 -> n_subgroups=1 < 2)
        with pytest.raises(ValueError, match="至少需要 20 个数据点"):
            calculate_capability(np.ones(12), usl=10, subgroup_size=10)
