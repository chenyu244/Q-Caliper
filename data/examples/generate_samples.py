"""Generate sample test datasets for Q-Caliper."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate_cpk_data(output_dir: Path) -> None:
    """Generate Cpk example dataset."""
    rng = np.random.default_rng(42)
    data = rng.normal(loc=50.0, scale=2.5, size=200)
    df = pd.DataFrame({
        "测量值": data,
        "零件编号": [f"P{i // 5 + 1:03d}" for i in range(200)],
    })
    path = output_dir / "cpk_example.xlsx"
    df.to_excel(path, index=False, engine="openpyxl")
    print(f"Generated: {path}")


def generate_grr_data(output_dir: Path) -> None:
    """Generate GRR example dataset."""
    rng = np.random.default_rng(42)
    n_parts, n_ops, n_trials = 10, 3, 3
    records = []
    for p in range(n_parts):
        for o in range(n_ops):
            for _t in range(n_trials):
                val = 50 + p * 2 + rng.normal(0, 0.5)
                records.append({
                    "零件": f"P{p + 1:02d}",
                    "操作者": f"Operator_{o + 1}",
                    "测量值": val,
                })
    df = pd.DataFrame(records)
    path = output_dir / "grr_example.xlsx"
    df.to_excel(path, index=False, engine="openpyxl")
    print(f"Generated: {path}")


def generate_spc_data(output_dir: Path) -> None:
    """Generate SPC example dataset."""
    rng = np.random.default_rng(42)
    data = rng.normal(loc=100, scale=3, size=100)
    df = pd.DataFrame({
        "时间点": [f"T{i + 1:03d}" for i in range(100)],
        "测量值": data,
    })
    path = output_dir / "spc_example.xlsx"
    df.to_excel(path, index=False, engine="openpyxl")
    print(f"Generated: {path}")


def generate_msa_data(output_dir: Path) -> None:
    """Generate MSA example dataset (bias + linearity)."""
    rng = np.random.default_rng(77)

    # Bias: 50 samples, true mean ~100.3 (ref=100.0)
    bias_data = rng.normal(loc=100.3, scale=0.6, size=50)

    # Linearity: 5 reference points with proportional bias
    refs = np.array([10, 20, 30, 40, 50], dtype=float)
    linearity_means = refs * 1.02 + 0.5 + rng.normal(0, 0.15, size=len(refs))

    n = max(len(bias_data), len(refs))
    rows = []
    for i in range(n):
        row = {}
        if i < len(bias_data):
            row["测量值"] = round(float(bias_data[i]), 4)
        if i < len(refs):
            row["参考值_线性"] = int(refs[i])
            row["测量均值_线性"] = round(float(linearity_means[i]), 4)
        rows.append(row)

    df = pd.DataFrame(rows)
    path = output_dir / "msa_example.xlsx"
    df.to_excel(path, index=False, engine="openpyxl")
    print(f"Generated: {path}")


if __name__ == "__main__":
    output_dir = Path(__file__).parent
    generate_cpk_data(output_dir)
    generate_grr_data(output_dir)
    generate_spc_data(output_dir)
    generate_msa_data(output_dir)
    print("All sample datasets generated.")
