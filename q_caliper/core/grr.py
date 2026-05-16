"""GRR (Gauge Repeatability and Reproducibility) ANOVA engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from scipy import stats as sp_stats

if TYPE_CHECKING:
    import numpy.typing as npt


@dataclass
class AnovaRow:
    """Single row of an ANOVA table."""

    source: str
    ss: float
    df: int
    ms: float
    f_value: float
    p_value: float


@dataclass
class GrrResult:
    """Result of GRR ANOVA analysis."""

    var_repeatability: float
    var_reproducibility: float
    var_interaction: float
    var_parts: float
    var_total: float
    pct_grr: float
    pct_part_variation: float
    ndc: int
    f_statistic: float
    p_value: float
    anova_table: list[AnovaRow]
    grand_mean: float
    part_means: list[float]
    operator_means: list[float]
    cell_means: list[list[float]]
    raw_data: npt.NDArray
    n_parts: int
    n_operators: int
    n_trials: int


def validate_grr_data(
    n_parts: int,
    n_operators: int,
    n_trials: int,
    n_measurements: int,
) -> list[str]:
    """Validate GRR study parameters.

    Returns:
        List of warning/error messages. Empty if valid.
    """
    issues: list[str] = []
    expected = n_parts * n_operators * n_trials

    if n_parts < 2:
        issues.append("零件数至少需要 2 个")
    if n_operators < 2:
        issues.append("操作者至少需要 2 人")
    if n_trials < 2:
        issues.append("重复测量至少需要 2 次")
    if n_measurements != expected:
        issues.append(
            f"数据量不匹配: 期望 {expected} 个 ({n_parts}x{n_operators}x{n_trials}), 实际 {n_measurements} 个"
        )
    if n_parts < 10:
        issues.append(f"零件数偏少({n_parts}), 建议 >=10 以提高统计功效")
    if n_operators < 3:
        issues.append(f"操作者偏少({n_operators}), 建议 >=3 人")

    return issues


def calculate_grr(
    data: npt.ArrayLike,
    n_parts: int,
    n_operators: int,
    n_trials: int,
) -> GrrResult:
    """Calculate GRR using ANOVA method.

    Args:
        data: Flattened measurement array (parts x operators x trials).
        n_parts: Number of parts.
        n_operators: Number of operators.
        n_trials: Number of trials per operator per part.

    Returns:
        GrrResult with variance components, ANOVA table, and chart data.
    """
    arr = np.asarray(data, dtype=float).reshape(n_parts, n_operators, n_trials)

    grand_mean = float(np.mean(arr))
    part_means = np.mean(arr, axis=(1, 2))
    operator_means = np.mean(arr, axis=(0, 2))
    cell_means = np.mean(arr, axis=2)

    ss_total = float(np.sum((arr - grand_mean) ** 2))
    ss_parts = float(n_operators * n_trials * np.sum((part_means - grand_mean) ** 2))
    ss_operators = float(n_parts * n_trials * np.sum((operator_means - grand_mean) ** 2))

    ss_interaction = 0.0
    for i in range(n_parts):
        for j in range(n_operators):
            expected = part_means[i] + operator_means[j] - grand_mean
            ss_interaction += n_trials * (cell_means[i, j] - expected) ** 2
    ss_interaction = float(ss_interaction)

    ss_error = ss_total - ss_parts - ss_operators - ss_interaction

    df_parts = n_parts - 1
    df_operators = n_operators - 1
    df_interaction = (n_parts - 1) * (n_operators - 1)
    df_error = n_parts * n_operators * (n_trials - 1)

    ms_parts = ss_parts / df_parts if df_parts > 0 else 0.0
    ms_operators = ss_operators / df_operators if df_operators > 0 else 0.0
    ms_interaction = ss_interaction / df_interaction if df_interaction > 0 else 0.0
    ms_error = ss_error / df_error if df_error > 0 else 0.0

    f_interaction = ms_interaction / ms_error if ms_error > 0 else 0.0
    p_interaction = float(1 - sp_stats.f.cdf(f_interaction, df_interaction, df_error)) if df_error > 0 else 1.0

    if p_interaction >= 0.25:
        # 合并交互项 (Pool Interaction)
        ss_pool = ss_interaction + ss_error
        df_pool = df_interaction + df_error
        ms_pool = ss_pool / df_pool if df_pool > 0 else 0.0

        f_parts = ms_parts / ms_pool if ms_pool > 0 else 0.0
        f_operators = ms_operators / ms_pool if ms_pool > 0 else 0.0
        p_parts = float(1 - sp_stats.f.cdf(f_parts, df_parts, df_pool)) if df_pool > 0 else 1.0
        p_operators = float(1 - sp_stats.f.cdf(f_operators, df_operators, df_pool)) if df_pool > 0 else 1.0

        anova_table = [
            AnovaRow("零件 (Parts)", ss_parts, df_parts, ms_parts, f_parts, p_parts),
            AnovaRow("操作者 (Operators)", ss_operators, df_operators, ms_operators, f_operators, p_operators),
            AnovaRow("重复性 (Error)", ss_pool, df_pool, ms_pool, 0.0, 0.0),
            AnovaRow("合计 (Total)", ss_total, df_parts + df_operators + df_pool, 0.0, 0.0, 0.0),
        ]

        var_repeatability = ms_pool
        var_interaction = 0.0
        var_reproducibility = max(0.0, (ms_operators - ms_pool) / (n_parts * n_trials))
        var_parts = max(0.0, (ms_parts - ms_pool) / (n_operators * n_trials))
    else:
        # 不合并 (使用混合模型计算F值)
        f_parts = ms_parts / ms_interaction if ms_interaction > 0 else 0.0
        f_operators = ms_operators / ms_interaction if ms_interaction > 0 else 0.0
        p_parts = float(1 - sp_stats.f.cdf(f_parts, df_parts, df_interaction)) if df_interaction > 0 else 1.0
        p_operators = (
            float(1 - sp_stats.f.cdf(f_operators, df_operators, df_interaction)) if df_interaction > 0 else 1.0
        )

        anova_table = [
            AnovaRow("零件 (Parts)", ss_parts, df_parts, ms_parts, f_parts, p_parts),
            AnovaRow("操作者 (Operators)", ss_operators, df_operators, ms_operators, f_operators, p_operators),
            AnovaRow(
                "交互 (Interaction)", ss_interaction, df_interaction, ms_interaction, f_interaction, p_interaction
            ),
            AnovaRow("重复性 (Error)", ss_error, df_error, ms_error, 0.0, 0.0),
            AnovaRow("合计 (Total)", ss_total, df_parts + df_operators + df_interaction + df_error, 0.0, 0.0, 0.0),
        ]

        var_repeatability = ms_error
        var_interaction = max(0.0, (ms_interaction - ms_error) / n_trials)
        var_reproducibility = max(0.0, (ms_operators - ms_interaction) / (n_parts * n_trials))
        var_parts = max(0.0, (ms_parts - ms_interaction) / (n_operators * n_trials))

    var_total = var_repeatability + var_reproducibility + var_interaction + var_parts
    var_grr = var_repeatability + var_reproducibility + var_interaction

    pct_grr = (var_grr / var_total * 100) if var_total > 0 else 0.0
    pct_part = (var_parts / var_total * 100) if var_total > 0 else 0.0
    ndc = int(1.41 * (var_parts / var_grr) ** 0.5) if var_grr > 0 else 0

    return GrrResult(
        var_repeatability=var_repeatability,
        var_reproducibility=var_reproducibility,
        var_interaction=var_interaction,
        var_parts=var_parts,
        var_total=var_total,
        pct_grr=pct_grr,
        pct_part_variation=pct_part,
        ndc=ndc,
        f_statistic=f_parts,
        p_value=p_parts,
        anova_table=anova_table,
        grand_mean=grand_mean,
        part_means=part_means.tolist(),
        operator_means=operator_means.tolist(),
        cell_means=cell_means.tolist(),
        raw_data=arr,
        n_parts=n_parts,
        n_operators=n_operators,
        n_trials=n_trials,
    )
