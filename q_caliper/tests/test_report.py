import sys
from pathlib import Path
import matplotlib.pyplot as plt

# Add the project root to the path so we can import q_caliper
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from q_caliper.reports.report_engine import generate_cpk_report
from q_caliper.core.cpk import CapabilityResult, NormalityResult

def test():
    cpk_result = CapabilityResult(
        mean=50.1234, std_within=1.5, std_overall=1.8, cp=1.33, cpk=1.2, pp=1.1, ppk=0.9, cmk=1.5,
        usl=55, lsl=45, pct_above_usl=0.01, pct_below_lsl=0.01, pct_total_out=0.02,
        sample_size=100, num_subgroups=20, analysis_mode="cpk_grouped",
        ppm_observed_total=20000, ppm_expected_within_total=15000, ppm_expected_overall_total=25000
    )
    norm_result = NormalityResult(test_name="Shapiro-Wilk", statistic=0.98, p_value=0.15, is_normal=True)
    
    # Create a dummy image
    img_path = Path("tmp_test_chart.png")
    plt.figure()
    plt.plot([1, 2, 3], [4, 5, 2])
    plt.title("Test Chart")
    plt.savefig(img_path)
    plt.close()
    
    try:
        out = generate_cpk_report("test_out.pdf", cpk_result, norm_result, str(img_path))
        print("Success! PDF generated at:", out)
    except Exception as e:
        import traceback
        print("Error during generation:")
        traceback.print_exc()
    finally:
        img_path.unlink(missing_ok=True)

if __name__ == "__main__":
    test()