"""GRR (Gauge Repeatability and Reproducibility) ANOVA engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import numpy.typing as npt


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
        GrrResult with variance components and GRR metrics.
    """
    arr = np.asarray(data, dtype=float).reshape(n_parts, n_operators, n_trials)

    grand_mean = np.mean(arr)
    part_means = np.mean(arr, axis=(1, 2))
    operator_means = np.mean(arr, axis=(0, 2))
    cell_means = np.mean(arr, axis=2)

    ss_total = np.sum((arr - grand_mean) ** 2)
    ss_parts = n_operators * n_trials * np.sum((part_means - grand_mean) ** 2)
    ss_operators = n_parts * n_trials * np.sum((operator_means - grand_mean) ** 2)

    ss_interaction = 0.0
    for i in range(n_parts):
        for j in range(n_operators):
            expected = part_means[i] + operator_means[j] - grand_mean
            ss_interaction += n_trials * (cell_means[i, j] - expected) ** 2

    ss_error = ss_total - ss_parts - ss_operators - ss_interaction

    df_parts = n_parts - 1
    df_operators = n_operators - 1
    df_interaction = (n_parts - 1) * (n_operators - 1)
    df_error = n_parts * n_operators * (n_trials - 1)

    ms_error = ss_error / df_error if df_error > 0 else 0.0
    ms_interaction = ss_interaction / df_interaction if df_interaction > 0 else 0.0
    ms_operators = ss_operators / df_operators if df_operators > 0 else 0.0
    ms_parts = ss_parts / df_parts if df_parts > 0 else 0.0

    var_repeatability = ms_error
    var_interaction = max(0.0, (ms_interaction - ms_error) / n_trials)
    var_reproducibility = max(0.0, (ms_operators - ms_error) / (n_parts * n_trials))
    var_parts = max(0.0, (ms_parts - ms_error) / (n_operators * n_trials))

    var_total = var_repeatability + var_reproducibility + var_interaction + var_parts
    var_grr = var_repeatability + var_reproducibility + var_interaction

    pct_grr = (var_grr / var_total * 100) if var_total > 0 else 0.0
    pct_part = (var_parts / var_total * 100) if var_total > 0 else 0.0
    ndc = int(1.41 * (var_parts / var_grr) ** 0.5) if var_grr > 0 else 0

    f_stat = ms_parts / ms_error if ms_error > 0 else 0.0
    from scipy import stats as sp_stats

    p_val = 1 - sp_stats.f.cdf(f_stat, df_parts, df_error) if df_error > 0 else 1.0

    return GrrResult(
        var_repeatability=var_repeatability,
        var_reproducibility=var_reproducibility,
        var_interaction=var_interaction,
        var_parts=var_parts,
        var_total=var_total,
        pct_grr=pct_grr,
        pct_part_variation=pct_part,
        ndc=ndc,
        f_statistic=f_stat,
        p_value=p_val,
    )
