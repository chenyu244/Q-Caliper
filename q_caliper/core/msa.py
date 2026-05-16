"""MSA (Measurement System Analysis) — linear and bias analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from scipy import stats as sp_stats

if TYPE_CHECKING:
    import numpy.typing as npt


@dataclass
class BiasResult:
    """Result of bias analysis."""

    mean_bias: float
    reference_value: float
    observed_mean: float
    t_statistic: float
    p_value: float
    pct_bias: float
    ci_lower: float
    ci_upper: float
    is_significant: bool


@dataclass
class LinearPoint:
    """Single point in a linear analysis."""

    reference: float
    observed_mean: float
    bias: float


@dataclass
class LinearResult:
    """Result of linearity analysis."""

    slope: float
    intercept: float
    r_squared: float
    p_slope: float
    p_intercept: float
    pct_linearity: float
    linearity: float
    points: list[LinearPoint]
    regression_line_x: list[float]
    regression_line_y: list[float]


def analyze_bias(
    data: npt.ArrayLike,
    reference_value: float,
    alpha: float = 0.05,
) -> BiasResult:
    """Perform bias analysis (one-sample t-test vs reference).

    Args:
        data: Measurement data.
        reference_value: Known reference/true value.
        alpha: Significance level.

    Returns:
        BiasResult with bias statistics.
    """
    arr = np.asarray(data, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    se = std / np.sqrt(n)

    bias = mean - reference_value
    t_stat = bias / se if se > 0 else 0.0
    p_val = 2 * (1 - sp_stats.t.cdf(abs(t_stat), df=n - 1))

    t_crit = sp_stats.t.ppf(1 - alpha / 2, n - 1)
    ci_lower = mean - t_crit * se
    ci_upper = mean + t_crit * se

    pct_bias = (bias / reference_value * 100) if reference_value != 0 else 0.0

    return BiasResult(
        mean_bias=bias,
        reference_value=reference_value,
        observed_mean=mean,
        t_statistic=t_stat,
        p_value=p_val,
        pct_bias=pct_bias,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        is_significant=bool(p_val < alpha),
    )


def analyze_linearity(
    reference_values: npt.ArrayLike,
    observed_means: npt.ArrayLike,
    process_variation: float,
) -> LinearResult:
    """Perform MSA linearity analysis.

    Args:
        reference_values: Array of reference values.
        observed_means: Array of mean observed values at each reference.
        process_variation: Total process variation (6*sigma).

    Returns:
        LinearResult with regression results.
    """
    refs = np.asarray(reference_values, dtype=float)
    means = np.asarray(observed_means, dtype=float)
    n = len(refs)

    if n < 3:
        raise ValueError("At least 3 reference points needed for linearity analysis")

    biases = means - refs
    slope, intercept, r_value, p_value, _std_err = sp_stats.linregress(refs, biases)
    r_squared = float(r_value**2) if not np.isnan(r_value) else 0.0

    x_fit = np.linspace(refs.min(), refs.max(), 50)
    y_fit = slope * x_fit + intercept

    pct_linearity = abs(slope) * 100.0
    linearity = abs(slope) * process_variation if process_variation > 0 else 0.0

    points = [
        LinearPoint(reference=float(r), observed_mean=float(m), bias=float(b))
        for r, m, b in zip(refs, means, biases, strict=False)
    ]

    return LinearResult(
        slope=float(slope),
        intercept=float(intercept),
        r_squared=float(r_squared),
        p_slope=float(p_value),
        p_intercept=0.0,
        pct_linearity=float(pct_linearity),
        linearity=linearity,
        points=points,
        regression_line_x=x_fit.tolist(),
        regression_line_y=y_fit.tolist(),
    )
