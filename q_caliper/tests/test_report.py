import sys
from pathlib import Path
import matplotlib.pyplot as plt

# Add the project root to the path so we can import q_caliper
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from q_caliper.reports.report_engine import generate_cpk_report, generate_grr_report
from q_caliper.core.cpk import CapabilityResult, NormalityResult
from q_caliper.core.grr import GrrResult, AnovaRow
import numpy as np

def test_cpk():
    cpk_result = CapabilityResult(
        mean=50.1234, std_within=1.5, std_overall=1.8, cp=1.33, cpk=1.2, pp=1.1, ppk=0.9, cmk=1.5,
        usl=55, lsl=45, pct_above_usl=0.01, pct_below_lsl=0.01, pct_total_out=0.02,
        sample_size=100, num_subgroups=20, analysis_mode="cpk_grouped",
        ppm_observed_total=20000, ppm_expected_within_total=15000, ppm_expected_overall_total=25000
    )
    norm_result = NormalityResult(test_name="Shapiro-Wilk", statistic=0.98, p_value=0.15, is_normal=True)

    img_path = Path("tmp_test_chart.png")
    plt.figure()
    plt.plot([1, 2, 3], [4, 5, 2])
    plt.title("Test Chart")
    plt.savefig(img_path)
    plt.close()

    try:
        out = generate_cpk_report("test_cpk_out.pdf", cpk_result, norm_result, str(img_path))
        print("Cpk report success! PDF generated at:", out)
    except Exception as e:
        import traceback
        print("Error during Cpk generation:")
        traceback.print_exc()
    finally:
        img_path.unlink(missing_ok=True)


def test_grr():
    anova_table = [
        AnovaRow("零件 (Parts)", 12.5, 9, 1.3889, 45.23, 0.00001),
        AnovaRow("操作者 (Operators)", 0.8, 2, 0.4, 13.04, 0.0003),
        AnovaRow("交互 (Interaction)", 1.2, 18, 0.0667, 2.17, 0.045),
        AnovaRow("重复性 (Error)", 1.85, 60, 0.0308, 0.0, 0.0),
        AnovaRow("合计 (Total)", 16.35, 89, 0.0, 0.0, 0.0),
    ]

    grr_result = GrrResult(
        var_repeatability=0.0308,
        var_reproducibility=0.0155,
        var_interaction=0.0186,
        var_parts=0.1158,
        var_total=0.1807,
        pct_grr=35.64,
        pct_part_variation=64.36,
        ndc=3,
        f_statistic=45.23,
        p_value=0.00001,
        anova_table=anova_table,
        grand_mean=50.5,
        part_means=[49.8, 50.1, 50.3, 50.5, 50.7, 50.9, 51.1, 51.3, 51.5, 51.7],
        operator_means=[50.2, 50.6, 50.7],
        cell_means=[[49.5, 49.9, 50.0]] * 10,
        raw_data=np.random.default_rng(42).normal(50.5, 0.8, (10, 3, 3)),
        n_parts=10,
        n_operators=3,
        n_trials=3,
    )

    img_path = Path("tmp_test_grr_chart.png")
    plt.figure()
    plt.pie([0.3, 0.2, 0.5], labels=["EV", "AV", "PV"])
    plt.title("Test GRR Chart")
    plt.savefig(img_path)
    plt.close()

    try:
        out = generate_grr_report("test_grr_out.pdf", grr_result, [str(img_path)])
        print("GRR report success! PDF generated at:", out)
    except Exception as e:
        import traceback
        print("Error during GRR generation:")
        traceback.print_exc()
    finally:
        img_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_cpk()
    test_grr()
