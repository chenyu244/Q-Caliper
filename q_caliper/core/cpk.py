"""Cpk/Cmk/Ppk 过程能力分析引擎

核心设计：
1. 默认 analysis_type="auto" 时，同时计算并返回 Cpk、Cmk、Ppk
2. Cpk 根据 subgroup_size 自动判断方法（>1 用 Xbar-R，=1 用 I-MR）
3. 不需要用户指定具体的 analysis_type，智能自动处理
4. 所有三个指标都返回，用户可以同时对比

这样用户可以：
- 一次调用获得所有三个指标
- 通过对比 Cpk、Cmk、Ppk 进行诊断
- 无需关心内部计算细节
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import numpy as np
from scipy import stats

if TYPE_CHECKING:
    import numpy.typing as npt


@dataclass
class NormalityResult:
    """正态性检验结果。"""

    test_name: str
    statistic: float
    p_value: float
    is_normal: bool


@dataclass
class CapabilityResult:
    """Cpk/Cmk/Ppk 计算结果 - 总是返回所有三个指标。

    属性说明：
        mean: 数据均值
        std_within: 短期标准差（用于 Cpk 计算）
                   - subgroup_size > 1: R̄/d₂(极差法)
                   - subgroup_size = 1: MR̄/1.128(移动极差法)
        std_overall: 长期标准差（全样本，用于 Cmk 和 Ppk）

        cpk: 过程能力指数（基于 std_within）
        cmk: 设备能力指数（基于 std_overall）
        ppk: 过程性能指数（基于 std_overall）

        cp, pp: 不考虑中心偏移的指数

        analysis_mode: 说明 Cpk 的计算方法 ("cpk_grouped" 或 "cpk_individual")
        num_subgroups: 子组数量

        ppm_observed_total: 观测到的总 PPM
        ppm_expected_within_total: 组内预期的总 PPM
        ppm_expected_overall_total: 整体预期的总 PPM
    """

    mean: float
    std_within: float
    std_overall: float
    cp: float | None
    cpk: float | None
    pp: float | None
    ppk: float | None
    cmk: float | None
    usl: float | None
    lsl: float | None
    pct_above_usl: float
    pct_below_lsl: float
    pct_total_out: float
    sample_size: int
    num_subgroups: int
    analysis_mode: str
    ppm_observed_total: float
    ppm_expected_within_total: float
    ppm_expected_overall_total: float


def normality_test(data: npt.ArrayLike, alpha: float = 0.05) -> NormalityResult:
    """对数据执行正态性检验。"""
    arr = np.asarray(data, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)

    if n < 8:
        raise ValueError("正态性检验至少需要 8 个数据点")

    if n < 5000:
        stat, p_value = stats.shapiro(arr)
        test_name = "Shapiro-Wilk"
    else:
        result = stats.anderson(arr, dist="norm")
        stat = result.statistic
        idx = list(result.significance_level).index(5.0)
        critical = result.critical_values[idx]
        p_value = 0.05 if stat > critical else 0.5
        test_name = "Anderson-Darling"

    return NormalityResult(
        test_name=test_name,
        statistic=float(stat),
        p_value=float(p_value),
        is_normal=bool(p_value > alpha),
    )


def calculate_capability(
    data: npt.ArrayLike,
    usl: float | None = None,
    lsl: float | None = None,
    subgroup_size: int | None = None,
    analysis_type: Literal["auto", "manual"] = "auto",
) -> CapabilityResult:
    """计算 Cpk/Cmk/Ppk 过程能力指数。"""
    arr = np.asarray(data, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)

    if n < 8:
        raise ValueError("至少需要 8 个数据点")

    # 基本统计
    mean = float(np.mean(arr))
    std_overall = float(np.std(arr, ddof=1))

    # 处理子组大小的默认值
    if subgroup_size is None:
        subgroup_size = 1

    # 1. 计算 std_within（用于 Cpk）
    if subgroup_size > 1:
        mode = "cpk_grouped"
        n_subgroups = n // subgroup_size
        if n_subgroups < 2:
            raise ValueError(f"当子组大小为 {subgroup_size} 时，至少需要 {subgroup_size * 2} 个数据点")

        subgroups = arr[: n_subgroups * subgroup_size].reshape(-1, subgroup_size)

        ranges = np.ptp(subgroups, axis=1)
        bar_r = np.mean(ranges)
        d2 = _d2_constant(subgroup_size)
        std_within = float(bar_r / d2)
    else:
        mode = "cpk_individual"
        moving_ranges = np.abs(np.diff(arr))
        bar_mr = np.mean(moving_ranges) if len(moving_ranges) > 0 else 0
        d2_mr = 1.128
        std_within = float(bar_mr / d2_mr)
        n_subgroups = max(1, n - 1)

    # 2. 计算指标（必须提供了规格限）
    if usl is None and lsl is None:
        raise ValueError("必须至少指定 USL 或 LSL 其中之一")

    # 1. 计算三个核心指标
    cp: float | None = None
    cpk: float | None = None
    pp: float | None = None
    ppk: float | None = None
    cmk: float | None = None

    cp = _calc_cp(usl, lsl, std_within)
    cpk = _calc_cpk(mean, usl, lsl, std_within)
    pp = _calc_cp(usl, lsl, std_overall)
    ppk = _calc_cpk(mean, usl, lsl, std_overall)
    cmk = ppk

    pct_above = _calc_pct_above(usl, mean, std_overall)
    pct_below = _calc_pct_below(lsl, mean, std_overall)

    ppm_obs: float = 0.0
    if usl is not None:
        ppm_obs += float(np.sum(arr > usl))
    if lsl is not None:
        ppm_obs += float(np.sum(arr < lsl))
    ppm_obs = (ppm_obs / n) * 1e6

    ppm_exp_within = (_calc_pct_above(usl, mean, std_within) + _calc_pct_below(lsl, mean, std_within)) * 1e6
    ppm_exp_overall = (pct_above + pct_below) * 1e6

    return CapabilityResult(
        mean=mean,
        std_within=std_within,
        std_overall=std_overall,
        cp=cp,
        cpk=cpk,
        pp=pp,
        ppk=ppk,
        cmk=cmk,
        usl=usl,
        lsl=lsl,
        pct_above_usl=pct_above,
        pct_below_lsl=pct_below,
        pct_total_out=pct_above + pct_below,
        sample_size=n,
        num_subgroups=n_subgroups,
        analysis_mode=mode,
        ppm_observed_total=ppm_obs,
        ppm_expected_within_total=ppm_exp_within,
        ppm_expected_overall_total=ppm_exp_overall,
    )


# ============================================================================
# 辅助函数
# ============================================================================


def _calc_cp(usl: float | None, lsl: float | None, sigma: float) -> float:
    """计算 Cp 或 Pp（不考虑中心偏移）。"""
    if sigma == 0 or sigma is None:
        return 0.0
    if usl is not None and lsl is not None:
        return (usl - lsl) / (6 * sigma)
    return 0.0


def _calc_cpk(mean: float, usl: float | None, lsl: float | None, sigma: float) -> float:
    """计算 Cpk、Ppk 或 Cmk（考虑中心偏移）。"""
    if sigma == 0 or sigma is None:
        return 0.0
    cpu = (usl - mean) / (3 * sigma) if usl is not None else float("inf")
    cpl = (mean - lsl) / (3 * sigma) if lsl is not None else float("inf")
    return min(cpu, cpl)


def _calc_pct_above(usl: float | None, mean: float, sigma: float) -> float:
    """计算超过 USL 的百分比。"""
    if usl is None:
        return 0.0
    return float(1 - stats.norm.cdf(usl, loc=mean, scale=sigma))


def _calc_pct_below(lsl: float | None, mean: float, sigma: float) -> float:
    """计算低于 LSL 的百分比。"""
    if lsl is None:
        return 0.0
    return float(stats.norm.cdf(lsl, loc=mean, scale=sigma))


def _d2_constant(n: int) -> float:
    """返回子组大小为 n 时的 d2 常数。"""
    d2_table = {
        2: 1.128,
        3: 1.693,
        4: 2.059,
        5: 2.326,
        6: 2.534,
        7: 2.704,
        8: 2.847,
        9: 2.970,
        10: 3.078,
        # 补充大子组查表值
        11: 3.173,
        12: 3.258,
        13: 3.336,
        14: 3.407,
        15: 3.472,
        16: 3.532,
        17: 3.588,
        18: 3.640,
        19: 3.689,
        20: 3.735,
        21: 3.778,
        22: 3.819,
        23: 3.858,
        24: 3.895,
        25: 3.931,
    }

    if n in d2_table:
        return d2_table[n]
    if n > 25:
        raise ValueError(f"子组大小 {n} 过大。当 n > 25 时，极差法失效，请重新评估抽样方案。")
    raise ValueError(f"不支持的子组大小: {n}")
