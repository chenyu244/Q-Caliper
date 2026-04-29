"""SPC (Statistical Process Control) chart engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import numpy.typing as npt


@dataclass
class ControlLimits:
    """Control chart limits."""

    ucl: float
    cl: float
    lcl: float


@dataclass
class ViolationPoint:
    """A point violating a Western Electric rule."""

    index: int
    rule: str
    description: str


@dataclass
class SpcChartResult:
    """Result of SPC chart analysis."""

    chart_type: str
    values: list[float]
    limits: ControlLimits
    violations: list[ViolationPoint]


def xbar_r_chart(
    data: npt.ArrayLike,
    subgroup_size: int = 5,
) -> tuple[SpcChartResult, SpcChartResult]:
    """Generate XBar-R control charts.

    Args:
        data: Flattened measurement data.
        subgroup_size: Number of observations per subgroup.

    Returns:
        Tuple of (xbar_chart, r_chart) results.
    """
    arr = np.asarray(data, dtype=float)
    n = len(arr)
    n_subgroups = n // subgroup_size
    arr = arr[: n_subgroups * subgroup_size].reshape(n_subgroups, subgroup_size)

    means = np.mean(arr, axis=1)
    ranges = np.ptp(arr, axis=1)

    _d2, _d3, a2, d3_const, d4_const = _get_constants(subgroup_size)

    xbar_cl = float(np.mean(means))
    r_cl = float(np.mean(ranges))

    xbar_ucl = xbar_cl + a2 * r_cl
    xbar_lcl = xbar_cl - a2 * r_cl
    r_ucl = d4_const * r_cl
    r_lcl = max(0.0, d3_const * r_cl)

    xbar_limits = ControlLimits(ucl=xbar_ucl, cl=xbar_cl, lcl=xbar_lcl)
    r_limits = ControlLimits(ucl=r_ucl, cl=r_cl, lcl=r_lcl)

    xbar_violations = detect_violations(means.tolist(), xbar_limits)
    r_violations = detect_violations(ranges.tolist(), r_limits)

    xbar_chart = SpcChartResult(
        chart_type="XBar",
        values=means.tolist(),
        limits=xbar_limits,
        violations=xbar_violations,
    )
    r_chart = SpcChartResult(
        chart_type="R",
        values=ranges.tolist(),
        limits=r_limits,
        violations=r_violations,
    )

    return xbar_chart, r_chart


def imr_chart(data: npt.ArrayLike) -> tuple[SpcChartResult, SpcChartResult]:
    """Generate Individual-Moving Range (I-MR) control charts.

    Args:
        data: Measurement data.

    Returns:
        Tuple of (i_chart, mr_chart) results.
    """
    arr = np.asarray(data, dtype=float)
    arr = arr[~np.isnan(arr)]

    values = arr.tolist()
    mr = np.abs(np.diff(arr)).tolist()

    i_cl = float(np.mean(arr))
    mr_cl = float(np.mean(mr)) if mr else 0.0

    e2 = 2.66
    d4 = 3.267

    i_ucl = i_cl + e2 * mr_cl
    i_lcl = i_cl - e2 * mr_cl
    mr_ucl = d4 * mr_cl
    mr_lcl = 0.0

    i_limits = ControlLimits(ucl=i_ucl, cl=i_cl, lcl=i_lcl)
    mr_limits = ControlLimits(ucl=mr_ucl, cl=mr_cl, lcl=mr_lcl)

    i_violations = detect_violations(values, i_limits)
    mr_violations = detect_violations(mr, mr_limits)

    i_chart = SpcChartResult(
        chart_type="I",
        values=values,
        limits=i_limits,
        violations=i_violations,
    )
    mr_chart_result = SpcChartResult(
        chart_type="MR",
        values=mr,
        limits=mr_limits,
        violations=mr_violations,
    )

    return i_chart, mr_chart_result


def detect_violations(
    values: list[float],
    limits: ControlLimits,
    n_sigma: float = 3.0,
) -> list[ViolationPoint]:
    """Detect Western Electric rule violations.

    Implements the 8 Nelson rules for control chart analysis.
    """
    violations: list[ViolationPoint] = []
    n = len(values)
    cl = limits.cl
    ucl = limits.ucl
    lcl = limits.lcl
    sigma = (ucl - cl) / n_sigma if n_sigma > 0 else 0.0

    for i, v in enumerate(values):
        if v > ucl or v < lcl:
            violations.append(ViolationPoint(i, "Rule 1", f"点超出控制限 (值={v:.3f})"))

    for i in range(n - 8):
        window = values[i : i + 9]
        if all(w > cl for w in window) or all(w < cl for w in window):
            violations.append(ViolationPoint(i + 8, "Rule 2", "连续9点在中心线同一侧"))

    for i in range(n - 5):
        window = values[i : i + 6]
        diffs = [window[j + 1] - window[j] for j in range(5)]
        if all(d > 0 for d in diffs) or all(d < 0 for d in diffs):
            violations.append(ViolationPoint(i + 5, "Rule 3", "连续6点递增或递降"))

    for i in range(n - 13):
        window = values[i : i + 14]
        alternating = all(
            (window[j] > cl) != (window[j + 1] > cl) for j in range(13)
        )
        if alternating:
            violations.append(ViolationPoint(i + 13, "Rule 4", "连续14点交替上下"))

    for i in range(n - 2):
        window = values[i : i + 3]
        zone_a_upper = cl + 2 * sigma
        zone_a_lower = cl - 2 * sigma
        above = sum(1 for w in window if w > zone_a_upper)
        below = sum(1 for w in window if w < zone_a_lower)
        if above >= 2 or below >= 2:
            violations.append(ViolationPoint(i + 2, "Rule 5", "连续3点中2点在A区外"))

    for i in range(n - 4):
        window = values[i : i + 5]
        above = sum(1 for w in window if w > cl + sigma)
        below = sum(1 for w in window if w < cl - sigma)
        if above >= 4 or below >= 4:
            violations.append(ViolationPoint(i + 4, "Rule 6", "连续5点中4点在B区外"))

    for i in range(n - 14):
        window = values[i : i + 15]
        above = sum(1 for w in window if w > cl)
        below = sum(1 for w in window if w < cl)
        if above >= 12 or below >= 12:
            violations.append(ViolationPoint(i + 14, "Rule 7", "连续15点在C区内"))

    for i in range(n - 7):
        window = values[i : i + 8]
        above = sum(1 for w in window if w > cl + sigma or w < cl - sigma)
        if above == 0:
            violations.append(ViolationPoint(i + 7, "Rule 8", "连续8点在C区外(但均在控制限内)"))

    return violations


def _get_constants(n: int) -> tuple[float, float, float, float, float]:
    """Return d2, d3, A2, D3, D4 constants for subgroup size n."""
    constants = {
        2: (1.128, 0.8525, 1.880, 0, 3.267),
        3: (1.693, 0.8884, 1.023, 0, 2.574),
        4: (2.059, 0.8798, 0.729, 0, 2.282),
        5: (2.326, 0.8641, 0.577, 0, 2.114),
        6: (2.534, 0.8480, 0.483, 0, 2.004),
        7: (2.704, 0.8332, 0.419, 0.076, 1.924),
        8: (2.847, 0.8198, 0.373, 0.136, 1.864),
        9: (2.970, 0.8078, 0.337, 0.184, 1.816),
        10: (3.078, 0.7971, 0.308, 0.223, 1.777),
    }
    return constants.get(n, (3.0, 0.8, 0.5, 0, 2.0))
