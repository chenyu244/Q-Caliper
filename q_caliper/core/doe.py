"""DOE (Design of Experiments) engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import numpy.typing as npt


@dataclass
class DoeDesign:
    """A DOE design matrix."""

    design_type: str
    n_factors: int
    n_runs: int
    factor_names: list[str]
    design_matrix: npt.NDArray[np.float64]
    run_order: list[int]


def full_factorial(
    n_factors: int,
    factor_names: list[str] | None = None,
    randomize: bool = True,
) -> DoeDesign:
    """Generate a full factorial (2^k) design matrix.

    Args:
        n_factors: Number of factors (k).
        factor_names: Optional names for each factor.
        randomize: Whether to randomize run order.

    Returns:
        DoeDesign with the generated design matrix.
    """
    if n_factors < 1 or n_factors > 10:
        raise ValueError("Number of factors must be between 1 and 10")

    if factor_names is None:
        factor_names = [f"Factor_{i + 1}" for i in range(n_factors)]
    elif len(factor_names) != n_factors:
        raise ValueError("factor_names length must match n_factors")

    from itertools import product

    levels = [-1, 1]
    combinations = list(product(levels, repeat=n_factors))
    design_matrix = np.array(combinations, dtype=float)
    n_runs = len(combinations)

    run_order = list(range(n_runs))
    if randomize:
        np.random.shuffle(run_order)

    return DoeDesign(
        design_type=f"2^{n_factors} Full Factorial",
        n_factors=n_factors,
        n_runs=n_runs,
        factor_names=factor_names,
        design_matrix=design_matrix,
        run_order=run_order,
    )


def fractional_factorial(
    n_factors: int,
    generator: str | None = None,
    factor_names: list[str] | None = None,
    randomize: bool = True,
) -> DoeDesign:
    """Generate a 2^(k-p) fractional factorial design.

    For simplicity, this generates a half-fraction for k >= 3 factors.

    Args:
        n_factors: Number of factors (k).
        generator: Generator string (e.g., "AB=C"). Not yet implemented.
        factor_names: Optional names for each factor.
        randomize: Whether to randomize run order.

    Returns:
        DoeDesign with the generated design matrix.
    """
    if n_factors < 3:
        raise ValueError("Fractional factorial requires at least 3 factors")

    if factor_names is None:
        factor_names = [f"Factor_{i + 1}" for i in range(n_factors)]

    base_factors = n_factors - 1
    from itertools import product

    levels = [-1, 1]
    base_combinations = list(product(levels, repeat=base_factors))
    base_matrix = np.array(base_combinations, dtype=float)

    interaction_col = np.prod(base_matrix, axis=1, keepdims=True)
    design_matrix = np.hstack([base_matrix, interaction_col])
    n_runs = len(design_matrix)

    run_order = list(range(n_runs))
    if randomize:
        np.random.shuffle(run_order)

    return DoeDesign(
        design_type=f"2^{n_factors - 1} Fractional Factorial",
        n_factors=n_factors,
        n_runs=n_runs,
        factor_names=factor_names,
        design_matrix=design_matrix,
        run_order=run_order,
    )
