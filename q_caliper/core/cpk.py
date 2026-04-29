"""Cpk/Ppk process capability analysis engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from scipy import stats

if TYPE_CHECKING:
    import numpy.typing as npt


@dataclass
class NormalityResult:
    """Result of a normality test."""

    test_name: str
    statistic: float
    p_value: float
    is_normal: bool


@dataclass
class CpkResult:
    """Result of Cpk/Ppk calculation."""

    mean: float
    std_within: float
    std_overall: float
    cp: float
    cpk: float
    pp: float
    ppk: float
    usl: float | None
    lsl: float | None
    pct_above_usl: float
    pct_below_lsl: float
    pct_total_out: float


def normality_test(data: npt.ArrayLike, alpha: float = 0.05) -> NormalityResult:
    """Perform normality test on data.

    Uses Shapiro-Wilk for n < 5000, otherwise Anderson-Darling.
    """
    arr = np.asarray(data, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)

    if n < 8:
        raise ValueError("Need at least 8 data points for normality test")

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


def calculate_cpk(
    data: npt.ArrayLike,
    usl: float | None = None,
    lsl: float | None = None,
    subgroup_size: int = 1,
) -> CpkResult:
    """Calculate Cpk/Ppk process capability indices.

    Args:
        data: Measurement data.
        usl: Upper specification limit.
        lsl: Lower specification limit.
        subgroup_size: Subgroup size for within-subgroup std estimation.

    Returns:
        CpkResult with all capability indices.
    """
    if usl is None and lsl is None:
        raise ValueError("At least one of USL or LSL must be specified")

    arr = np.asarray(data, dtype=float)
    arr = arr[~np.isnan(arr)]

    mean = float(np.mean(arr))
    n = len(arr)

    if subgroup_size > 1:
        subgroups = arr[: n - n % subgroup_size].reshape(-1, subgroup_size)
        ranges = np.ptp(subgroups, axis=1)
        d2 = _d2_constant(subgroup_size)
        std_within = float(np.mean(ranges) / d2)
    else:
        std_within = float(np.std(arr, ddof=1))

    std_overall = float(np.std(arr, ddof=1))

    cp = _calc_cp(usl, lsl, std_within)
    cpk = _calc_cpk(mean, usl, lsl, std_within)
    pp = _calc_cp(usl, lsl, std_overall)
    ppk = _calc_cpk(mean, usl, lsl, std_overall)

    pct_above = float(1 - stats.norm.cdf(usl, loc=mean, scale=std_overall)) if usl is not None else 0.0
    pct_below = float(stats.norm.cdf(lsl, loc=mean, scale=std_overall)) if lsl is not None else 0.0

    return CpkResult(
        mean=mean,
        std_within=std_within,
        std_overall=std_overall,
        cp=cp,
        cpk=cpk,
        pp=pp,
        ppk=ppk,
        usl=usl,
        lsl=lsl,
        pct_above_usl=pct_above,
        pct_below_lsl=pct_below,
        pct_total_out=pct_above + pct_below,
    )


def _calc_cp(usl: float | None, lsl: float | None, sigma: float) -> float:
    if usl is not None and lsl is not None:
        return (usl - lsl) / (6 * sigma)
    return 0.0


def _calc_cpk(mean: float, usl: float | None, lsl: float | None, sigma: float) -> float:
    if sigma == 0:
        return 0.0
    cpu = (usl - mean) / (3 * sigma) if usl is not None else float("inf")
    cpl = (mean - lsl) / (3 * sigma) if lsl is not None else float("inf")
    return min(cpu, cpl)


def _d2_constant(n: int) -> float:
    """Return the d2 constant for subgroup size n."""
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
    return d2_table.get(n, 3.0)
