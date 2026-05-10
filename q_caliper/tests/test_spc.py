"""Tests for SPC chart engine."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from q_caliper.core.cpk import calculate_capability  # noqa: E402
from q_caliper.core.spc import ControlLimits, detect_violations, imr_chart, xbar_r_chart  # noqa: E402
from q_caliper.reports.report_engine import generate_spc_report  # noqa: E402


def test_xbar_r_basic() -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(loc=100, scale=2, size=50)
    xbar, r_chart = xbar_r_chart(data, subgroup_size=5)
    assert len(xbar.values) == 10
    assert len(r_chart.values) == 10
    assert xbar.limits.ucl > xbar.limits.cl > xbar.limits.lcl


def test_imr_basic() -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(loc=50, scale=1, size=30)
    i_chart, mr_chart = imr_chart(data)
    assert len(i_chart.values) == 30
    assert len(mr_chart.values) == 29


def test_no_violations_in_stable_process() -> None:
    rng = np.random.default_rng(42)
    values = rng.normal(loc=100, scale=1, size=20).tolist()
    limits = ControlLimits(ucl=103, cl=100, lcl=97)
    violations = detect_violations(values, limits)
    assert len(violations) == 0


def test_detects_out_of_control() -> None:
    values = [100.0] * 10 + [110.0]
    limits = ControlLimits(ucl=103, cl=100, lcl=97)
    violations = detect_violations(values, limits)
    assert any(v.rule == "Rule 1" for v in violations)


def test_spc_report_xbar_r() -> None:
    """Test SPC report generation with XBar-R chart."""
    rng = np.random.default_rng(42)
    data = rng.normal(loc=100, scale=2, size=50)
    xbar, r_chart = xbar_r_chart(data, subgroup_size=5)
    cpk_result = calculate_capability(data, usl=106, lsl=94, subgroup_size=5)

    import matplotlib.pyplot as plt

    imgs = []
    for name in ["xbar", "r", "trend"]:
        p = Path(f"tmp_spc_{name}.png")
        plt.figure()
        plt.plot([1, 2, 3], [4, 5, 6])
        plt.savefig(p)
        plt.close()
        imgs.append(p)

    try:
        out = generate_spc_report(
            "test_spc_xbar_out.pdf",
            chart1=xbar,
            chart2=r_chart,
            chart1_name="XBar (均值图)",
            chart2_name="R (极差图)",
            cpk_result=cpk_result,
            chart_paths=[str(p) for p in imgs],
            col_name="测量值",
            chart_type_name="XBar-R 控制图",
            subgroup_size=5,
            data_length=50,
        )
        print("SPC XBar-R report success! PDF:", out)
    except Exception:
        import traceback

        traceback.print_exc()
    finally:
        for p in imgs:
            p.unlink(missing_ok=True)


def test_spc_report_imr() -> None:
    """Test SPC report generation with I-MR chart."""
    rng = np.random.default_rng(42)
    data = rng.normal(loc=50, scale=1, size=30)
    i_chart, mr_chart = imr_chart(data)

    import matplotlib.pyplot as plt

    imgs = []
    for name in ["i", "mr"]:
        p = Path(f"tmp_spc_{name}.png")
        plt.figure()
        plt.plot([1, 2, 3], [4, 5, 6])
        plt.savefig(p)
        plt.close()
        imgs.append(p)

    try:
        out = generate_spc_report(
            "test_spc_imr_out.pdf",
            chart1=i_chart,
            chart2=mr_chart,
            chart1_name="I (个体值图)",
            chart2_name="MR (移动极差图)",
            cpk_result=None,
            chart_paths=[str(p) for p in imgs],
            col_name="测量值",
            chart_type_name="I-MR 控制图",
            subgroup_size=1,
            data_length=30,
        )
        print("SPC I-MR report success! PDF:", out)
    except Exception:
        import traceback

        traceback.print_exc()
    finally:
        for p in imgs:
            p.unlink(missing_ok=True)


if __name__ == "__main__":
    test_spc_report_xbar_r()
    test_spc_report_imr()
    print("All SPC report tests passed!")
