"""Cpk/Cmk/Ppk 过程能力分析引擎。

本模块提供全面的过程能力分析，支持三种指数：
- Cmk: 设备能力（连续测量，不分组）
- Cpk: 过程能力（短期能力，基于子组内变异）
- Ppk: 过程性能（长期表现，基于整体变异）
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
    """正态性检验结果。
    
    属性:
        test_name: 使用的检验方法名称（Shapiro-Wilk 或 Anderson-Darling）
        statistic: 检验统计量的值
        p_value: 检验的 P 值 (0.0-1.0)
        is_normal: 如果数据在 alpha=0.05 时通过正态性检验则为 True
    """

    test_name: str
    statistic: float
    p_value: float
    is_normal: bool


@dataclass
class CapabilityResult:
    """Cpk/Cmk/Ppk 计算结果。
    
    属性:
        mean: 数据均值
        std_within: 子组内（短期）标准差
        std_overall: 整体（长期）标准差
        cp: Cp 指数（双侧）
        cpk: Cpk 指数（短期，考虑中心偏移）
        pp: Pp 指数（双侧）
        ppk: Ppk 指数（长期，考虑中心偏移）
        cmk: Cmk 指数（设备能力，考虑中心偏移）
        usl: 规格上限
        lsl: 规格下限
        pct_above_usl: 高于规格上限的数据点百分比
        pct_below_lsl: 低于规格下限的数据点百分比
        pct_total_out: 超出规格限的总百分比
        sample_size: 分析的样本总数
        num_subgroups: 划分的子组数量
        analysis_mode: 执行的分析类型 ("equipment", "subgrouped", "individual")
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
    analysis_mode: str  # "equipment", "subgrouped", "individual"


def normality_test(data: npt.ArrayLike, alpha: float = 0.05) -> NormalityResult:
    """对数据执行正态性检验。

    当 n < 5000 时使用 Shapiro-Wilk 检验，否则使用 Anderson-Darling 检验。
    
    参数:
        data: 测量数据的输入数组
        alpha: 显著性水平（默认 0.05）
        
    返回:
        包含检验详细信息的 NormalityResult
        
    异常:
        ValueError: 如果提供的数据点少于 8 个
    """
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
    analysis_type: Literal["auto", "equipment", "subgrouped", "individual"] = "auto",
) -> CapabilityResult:
    """计算 Cmk/Cpk/Ppk 过程能力指数。

    这是一个统一的接口，支持三种分析模式：
    
    1. 设备能力 (Cmk)：单一连续序列，不进行子组划分
       - 用于 FAT/SAT 或设备验证
       - 不分离子组变异
       
    2. 分组过程能力 (Cpk)：数据按有理子组组织
       - 将子组内（短期）变异与整体变异分离
       - 通过比较 Cpk 与 Ppk 诊断过程稳定性
       
    3. 个体过程性能 (Ppk)：单次测量，使用 I-MR 估计
       - 当 subgroup_size=1 时的默认模式
       - 使用移动极差 (Moving Range) 估计短期变异

    参数:
        data: 测量数据数组
        usl: 规格上限（可选）
        lsl: 规格下限（可选）
        subgroup_size: 
            - None 或 "auto": 根据数据和分析类型自动选择
            - 整数 > 1: 使用分组分析（Xbar-R 方法）
            - 1: 使用个体分析（I-MR 方法）
        analysis_type:
            - "auto" (默认): 根据子组大小和数据特征自动选择
            - "equipment": 强制计算 Cmk（不分组）
            - "subgrouped": 强制计算分组的 Cpk（需要 subgroup_size > 1）
            - "individual": 强制使用 I-MR 方法计算 Ppk（subgroup_size=1）

    返回:
        包含所有三个指数（Cmk, Cpk, Ppk）的 CapabilityResult
        
    异常:
        ValueError: 如果未指定 USL 或 LSL，或者参数无效
        
    示例:
        >>> data = np.random.normal(100, 2, 50)
        >>> result = calculate_capability(data, usl=110, lsl=90, subgroup_size=5)
        >>> print(f"Cpk: {result.cpk:.3f}, Ppk: {result.ppk:.3f}")
        
        >>> # 设备能力
        >>> result = calculate_capability(data, usl=110, lsl=90, 
        ...                               analysis_type="equipment")
        >>> print(f"Cmk: {result.cmk:.3f}")
    """
    if usl is None and lsl is None:
        raise ValueError("必须至少指定 USL 或 LSL 其中之一")

    arr = np.asarray(data, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)

    if n < 8:
        raise ValueError("至少需要 8 个数据点")

    mean = float(np.mean(arr))

    # 确定分析模式和子组配置
    if analysis_type == "equipment":
        # 设备模式：50-100 个连续样本，不分组
        # 根据汽车行业标准 (Bosch, QS-9000, IATF 16949)
        # σ 计算为全样本标准差
        mode = "equipment"
        effective_subgroup_size = 1  # Cmk 不分组
        num_subgroups = 1  # 将整个数据集视为单一组
    elif analysis_type == "subgrouped":
        if subgroup_size is None or subgroup_size <= 1:
            raise ValueError("分组分析要求 subgroup_size > 1")
        mode = "subgrouped"
        effective_subgroup_size = subgroup_size
        num_subgroups = n // effective_subgroup_size
    elif analysis_type == "individual":
        mode = "individual"
        effective_subgroup_size = 1
        num_subgroups = max(1, n - 1)  # 移动极差使用 n-1 个对
    else:  # auto
        if subgroup_size is not None and subgroup_size > 1:
            mode = "subgrouped"
            effective_subgroup_size = subgroup_size
            num_subgroups = n // effective_subgroup_size
        else:
            # 默认为个体分析 (I-MR)
            mode = "individual"
            effective_subgroup_size = 1
            num_subgroups = max(1, n - 1)

    # 根据模式估计 σ_within
    if mode == "equipment":
        # 设备 (Cmk)：使用全样本标准差，不分组
        # 根据汽车行业标准 (Bosch, QS-9000, IATF 16949)
        # Cmk 反映连续生产运行中的机器精度
        std_within = float(np.std(arr, ddof=1))
    elif mode == "subgrouped" and effective_subgroup_size > 1:
        # Cpk: 使用有理子组的 Xbar-R 方法
        n_subgroups_actual = n // effective_subgroup_size
        if n_subgroups_actual < 2:
            raise ValueError(
                f"子组大小为 {effective_subgroup_size} 时，至少需要 "
                f"{effective_subgroup_size * 2} 个数据点"
            )
        subgroups = arr[: n_subgroups_actual * effective_subgroup_size].reshape(
            -1, effective_subgroup_size
        )
        ranges = np.ptp(subgroups, axis=1)
        d2 = _d2_constant(effective_subgroup_size)
        std_within = float(np.mean(ranges) / d2)
    else:
        # 个体/Ppk: 使用移动极差的 I-MR 方法
        if n < 2:
            raise ValueError("I-MR 方法至少需要 2 个数据点")
        moving_ranges = np.abs(np.diff(arr))
        d2_mr = 1.128  # 移动极差 (n=2) 的 d2 常数
        std_within = float(np.mean(moving_ranges) / d2_mr)

    # σ_overall 始终基于全样本
    std_overall = float(np.std(arr, ddof=1))

    # 计算所有指数
    cp = _calc_cp(usl, lsl, std_within)
    cpk = _calc_cpk(mean, usl, lsl, std_within)
    pp = _calc_cp(usl, lsl, std_overall)
    ppk = _calc_cpk(mean, usl, lsl, std_overall)
    cmk = _calc_cpk(mean, usl, lsl, std_within)  # 计算方式与 Cpk 相同

    # 计算超出规格的百分比
    pct_above = (
        float(1 - stats.norm.cdf(usl, loc=mean, scale=std_overall))
        if usl is not None
        else 0.0
    )
    pct_below = (
        float(stats.norm.cdf(lsl, loc=mean, scale=std_overall))
        if lsl is not None
        else 0.0
    )

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
        num_subgroups=num_subgroups,
        analysis_mode=mode,
    )


def _calc_cp(usl: float | None, lsl: float | None, sigma: float) -> float:
    """计算 Cp 或 Pp（不考虑中心偏移的双侧指数）。
    
    参数:
        usl: 规格上限
        lsl: 规格下限
        sigma: 标准差（短期或整体）
        
    返回:
        Cp/Pp 值（如果双侧限制不可用则为 0.0）
    """
    if sigma == 0:
        return 0.0
    if usl is not None and lsl is not None:
        return (usl - lsl) / (6 * sigma)
    return 0.0


def _calc_cpk(
    mean: float, usl: float | None, lsl: float | None, sigma: float
) -> float:
    """计算 Cpk 或 Ppk（考虑中心偏移的指数）。
    
    取上限和下限能力值的较小者，以考虑均值偏移。
    
    参数:
        mean: 过程均值
        usl: 规格上限
        lsl: 规格下限
        sigma: 标准差（短期或整体）
        
    返回:
        Cpk/Ppk 值（考虑了均值中心化）
    """
    if sigma == 0:
        return 0.0
    cpu = (usl - mean) / (3 * sigma) if usl is not None else float("inf")
    cpl = (mean - lsl) / (3 * sigma) if lsl is not None else float("inf")
    return min(cpu, cpl)


def _d2_constant(n: int) -> float:
    """返回子组大小为 n 时的 d2 常数 (Xbar-R 控制图)。
    
    d2 常数用于将平均极差转换为标准差估计值：
    σ = R̄ / d2
    
    参数:
        n: 子组大小 (2-10)
        
    返回:
        d2 常数值（对于 n > 10，使用公式 d2(n) ≈ sqrt(pi * n / (2n - 1)) 计算）
    """
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
    }
    
    if n in d2_table:
        return d2_table[n]
    else:
        return math.sqrt((math.pi * n) / (2 * n - 1))
