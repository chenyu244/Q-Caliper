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
        num_subgroups: 子组数量（cpk 计算中的子组数，或 MR 的对数）
    """
    mean: float
    std_within: float
    std_overall: float
    cp: float
    cpk: float
    pp: float
    ppk: float
    cmk: float
    usl: float | None
    lsl: float | None
    pct_above_usl: float
    pct_below_lsl: float
    pct_total_out: float
    sample_size: int
    num_subgroups: int
    analysis_mode: str  # "cpk_grouped" 或 "cpk_individual"


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
    """计算 Cpk/Cmk/Ppk 过程能力指数。

    设计理念：智能自动化，一次计算返回三个指标
    
    在 auto 模式下（推荐）：
    1. 根据 subgroup_size 自动判断 Cpk 的计算方法
    2. 同时计算 Cmk 和 Ppk
    3. 返回所有三个指标，用户可以进行对比诊断
    
    参数:
        data: 测量数据数组
        usl: 规格上限（可选）
        lsl: 规格下限（可选）
        subgroup_size: 子组大小
                      - > 1: 使用 Xbar-R 方法计算 Cpk
                      - = 1: 使用 I-MR 方法计算 Cpk
                      - None: 默认为 1（无法分组）
        analysis_type: "auto" (推荐) 或 "manual"
                      - auto: 自动计算所有三个指标
                      - manual: 仅计算指定的指标（需要用户知道自己要什么）

    返回:
        CapabilityResult 包含 cpk、cmk、ppk 三个指标，用户可以同时对比

    使用示例：
        >>> result = calculate_capability(data, usl=100.5, lsl=99.5, subgroup_size=5)
        >>> print(f"Cpk: {result.cpk:.3f}")  # 自动用 Xbar-R 方法
        >>> print(f"Cmk: {result.cmk:.3f}")  # 设备能力
        >>> print(f"Ppk: {result.ppk:.3f}")  # 过程性能
        >>> 
        >>> # 对比诊断
        >>> if result.cpk > result.ppk + 0.15:
        ...     print("过程存在漂移")
    """
    if usl is None and lsl is None:
        raise ValueError("必须至少指定 USL 或 LSL 其中之一")

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

    # ========================================================================
    # 统一逻辑：计算所有三个指标
    # ========================================================================

    # 1. 计算 std_within（用于 Cpk）
    # ========================================================================
    if subgroup_size > 1:
        # 方法 A：Xbar-R（有理子组）
        mode = "cpk_grouped"
        n_subgroups = n // subgroup_size

        if n_subgroups < 2:
            raise ValueError(
                f"子组大小为 {subgroup_size} 时，至少需要 {subgroup_size * 2} 个数据点"
            )

        # 计算子组内极差
        subgroups = arr[: n_subgroups * subgroup_size].reshape(-1, subgroup_size)
        ranges = np.ptp(subgroups, axis=1)
        bar_R = np.mean(ranges)
        d2 = _d2_constant(subgroup_size)
        std_within = float(bar_R / d2)

    else:  # subgroup_size == 1
        # 方法 B：I-MR（移动极差）
        mode = "cpk_individual"

        if n < 2:
            raise ValueError("I-MR 方法至少需要 2 个数据点")

        moving_ranges = np.abs(np.diff(arr))
        bar_MR = np.mean(moving_ranges)
        d2_mr = 1.128
        std_within = float(bar_MR / d2_mr)
        n_subgroups = max(1, n - 1)

    # 2. 计算三个指标
    # ========================================================================
    cp = _calc_cp(usl, lsl, std_within)
    cpk = _calc_cpk(mean, usl, lsl, std_within)
    pp = _calc_cp(usl, lsl, std_overall)
    ppk = _calc_cpk(mean, usl, lsl, std_overall)
    cmk = _calc_cpk(mean, usl, lsl, std_overall)  # Cmk 用全样本标准差

    # 3. 计算超出规格的百分比
    # ========================================================================
    pct_above = _calc_pct_above(usl, mean, std_overall)
    pct_below = _calc_pct_below(lsl, mean, std_overall)

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


def _calc_cpk(
    mean: float, usl: float | None, lsl: float | None, sigma: float
) -> float:
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
        2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534,
        7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078,
        # 补充大子组查表值
        11: 3.173, 12: 3.258, 13: 3.336, 14: 3.407, 15: 3.472,
        16: 3.532, 17: 3.588, 18: 3.640, 19: 3.689, 20: 3.735, 
        21: 3.778, 22: 3.819, 23: 3.858, 24: 3.895, 25: 3.931
    }
    
    if n in d2_table:
        return d2_table[n]
    elif n > 25:
        raise ValueError(f"子组大小 {n} 过大。当 n > 25 时，极差法失效，请重新评估抽样方案。")
