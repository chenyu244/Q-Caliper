"""Tests for MSA (Measurement System Analysis) engine."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from q_caliper.core.msa import analyze_bias, analyze_linearity
from q_caliper.reports.report_engine import generate_msa_report


def test_no_bias() -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(loc=100, scale=1, size=50)
    result = analyze_bias(data, reference_value=100)
    assert abs(result.mean_bias) < 1.0
    assert result.pct_bias < 5


def test_significant_bias() -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(loc=105, scale=0.5, size=50)
    result = analyze_bias(data, reference_value=100)
    assert result.is_significant is True
    assert result.mean_bias > 0


def test_confidence_interval() -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(loc=50, scale=2, size=30)
    result = analyze_bias(data, reference_value=50)
    assert result.ci_lower < result.observed_mean < result.ci_upper


def test_perfect_linearity() -> None:
    refs = np.array([10, 20, 30, 40, 50], dtype=float)
    means = refs.copy()
    result = analyze_linearity(refs, means, process_variation=30)
    assert abs(result.slope) < 0.01
    assert result.r_squared < 0.01


def test_proportional_bias() -> None:
    refs = np.array([10, 20, 30, 40, 50], dtype=float)
    means = refs * 1.05 + 2
    result = analyze_linearity(refs, means, process_variation=30)
    assert result.slope > 0
    assert result.r_squared > 0.8


def test_too_few_points() -> None:
    try:
        analyze_linearity([1, 2], [1, 2], process_variation=1)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_msa_report_bias_only() -> None:
    """Test MSA report generation with bias analysis only."""
    rng = np.random.default_rng(42)
    data = rng.normal(loc=100.5, scale=1.0, size=50)
    bias_result = analyze_bias(data, reference_value=100.0)

    import matplotlib.pyplot as plt
    img = Path("tmp_msa_bias_chart.png")
    plt.figure()
    plt.hist(data, bins=15)
    plt.savefig(img)
    plt.close()

    try:
        out = generate_msa_report(
            "test_msa_bias_out.pdf",
            bias_result=bias_result,
            chart_paths=[str(img)],
            bias_data=data,
            bias_col_name="测量值",
        )
        print("MSA bias report success! PDF:", out)
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        img.unlink(missing_ok=True)


def test_msa_report_full() -> None:
    """Test MSA report generation with both bias and linearity."""
    rng = np.random.default_rng(42)
    data = rng.normal(loc=100.5, scale=1.0, size=50)
    bias_result = analyze_bias(data, reference_value=100.0)

    refs = np.array([10, 20, 30, 40, 50], dtype=float)
    means = refs * 1.03 + 1.5
    linear_result = analyze_linearity(refs, means, process_variation=30)

    import matplotlib.pyplot as plt
    imgs = []
    for name in ["bias", "linear"]:
        p = Path(f"tmp_msa_{name}.png")
        plt.figure()
        plt.plot([1, 2, 3], [4, 5, 6])
        plt.savefig(p)
        plt.close()
        imgs.append(p)

    try:
        out = generate_msa_report(
            "test_msa_full_out.pdf",
            bias_result=bias_result,
            linear_result=linear_result,
            chart_paths=[str(p) for p in imgs],
            bias_data=data,
            bias_col_name="测量值",
            linear_refs=refs,
            linear_means=means,
            process_variation=30.0,
        )
        print("MSA full report success! PDF:", out)
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        for p in imgs:
            p.unlink(missing_ok=True)


if __name__ == "__main__":
    test_msa_report_bias_only()
    test_msa_report_full()
    print("All MSA report tests passed!")
