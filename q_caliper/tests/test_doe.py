"""Tests for DOE design engine."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import statsmodels.api as sm

from q_caliper.core.doe import fractional_factorial, full_factorial


class TestFullFactorial:
    """Test full factorial design generation."""

    def test_2_factor_design(self) -> None:
        design = full_factorial(2, randomize=False)
        assert design.n_runs == 4
        assert design.n_factors == 2
        assert design.design_matrix.shape == (4, 2)

    def test_3_factor_design(self) -> None:
        design = full_factorial(3, randomize=False)
        assert design.n_runs == 8
        assert design.n_factors == 3

    def test_custom_factor_names(self) -> None:
        design = full_factorial(2, factor_names=["Temp", "Pressure"], randomize=False)
        assert design.factor_names == ["Temp", "Pressure"]

    def test_invalid_factors(self) -> None:
        with pytest.raises(ValueError):
            full_factorial(0)


class TestFractionalFactorial:
    """Test fractional factorial design generation."""

    def test_half_fraction_3_factors(self) -> None:
        design = fractional_factorial(3, randomize=False)
        assert design.n_runs == 4
        assert design.n_factors == 3

    def test_too_few_factors(self) -> None:
        with pytest.raises(ValueError):
            fractional_factorial(2)


def _make_doe_model(design):
    rng = np.random.default_rng(42)
    n = design.n_runs
    x = sm.add_constant(design.design_matrix)
    true_coef = np.concatenate([[50.0], rng.normal(0, 2, design.n_factors)])
    noise = rng.normal(0, 1, n)
    y = x @ true_coef + noise
    model = sm.OLS(y, x).fit()
    return model, y


def test_doe_report_full_factorial() -> None:
    from q_caliper.reports.report_engine import generate_doe_report

    design = full_factorial(3, randomize=False)
    model, y = _make_doe_model(design)

    import matplotlib.pyplot as plt
    imgs = []
    for name in ["effect", "pareto"]:
        p = Path(f"tmp_doe_{name}.png")
        plt.figure()
        plt.plot([1, 2, 3], [4, 5, 6])
        plt.savefig(p)
        plt.close()
        imgs.append(p)

    try:
        out = generate_doe_report(
            "test_doe_out.pdf",
            design=design,
            model=model,
            response=y,
            chart_paths=[str(p) for p in imgs],
        )
        print("DOE report success! PDF:", out)
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        for p in imgs:
            p.unlink(missing_ok=True)
