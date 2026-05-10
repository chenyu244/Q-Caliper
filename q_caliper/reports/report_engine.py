"""Report engine — Typst template rendering and PDF generation via Python typst package."""

from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typst

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

    from q_caliper.core.cpk import CapabilityResult, NormalityResult
    from q_caliper.core.doe import DoeDesign
    from q_caliper.core.grr import GrrResult
    from q_caliper.core.msa import BiasResult, LinearResult
    from q_caliper.core.spc import SpcChartResult


def _get_template_dir() -> Path:
    """Resolve template directory for both dev and Nuitka onefile modes."""
    base = Path(__file__).parent / "templates"
    if base.exists():
        return base

    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "q_caliper" / "reports" / "templates"
        if base.exists():
            return base

    return Path(__file__).parent / "templates"


@dataclass
class ReportConfig:
    """Report generation configuration."""

    company_name: str = "Q-Caliper"
    logo_path: str = ""
    report_title: str = "质量分析报告"
    author: str = ""
    date: str = ""


@dataclass
class ReportData:
    """Data to inject into a report template."""

    module: str
    title: str
    summary: dict = field(default_factory=dict)
    tables: list[dict] = field(default_factory=list)
    chart_paths: list[str] = field(default_factory=list)
    custom_data: dict = field(default_factory=dict)


def _escape_typst_content(text: str) -> str:
    """Escape characters that Typst interprets as markup inside content blocks."""
    return str(text).replace("[", "(").replace("]", ")").replace("<", "\\<").replace(">", "\\>")


def to_roman(n: int) -> str:
    """Convert integer to Roman numeral (1-10)."""
    vals = [10, 9, 5, 4, 1]
    syms = ["X", "IX", "V", "IV", "I"]
    result = ""
    for v, s in zip(vals, syms, strict=False):
        while n >= v:
            result += s
            n -= v
    return result


def _format_typst_table(headers: list[str], rows: list[list[str]]) -> str:
    """Helper to format a raw Typst table from headers and rows."""
    if not headers and not rows:
        return ""
    col_count = len(headers) if headers else len(rows[0])
    cols_str = "(" + ", ".join(["auto"] * col_count) + ")"
    block = f"#table(\n  columns: {cols_str},\n  inset: 8pt,\n  stroke: 0.5pt,\n  align: center,\n"
    if headers:
        header_str = ", ".join([f"[*{_escape_typst_content(h)}*]" for h in headers])
        block += f"  table.header({header_str}),\n"
    for row in rows:
        row_str = ", ".join([f"[{_escape_typst_content(v)}]" for v in row])
        block += f"  {row_str},\n"
    block += ")\n"
    return block


TEMPLATE_DIR = _get_template_dir()


def render_report(
    template_name: str,
    output_path: str,
    data: ReportData,
    config: ReportConfig | None = None,
) -> str:
    """Render a Typst template to PDF using the Python typst package.

    Args:
        template_name: Name of the .typ template file (without extension).
        output_path: Path for the output PDF.
        data: Report data to inject.
        config: Optional report configuration.

    Returns:
        Absolute path to the generated PDF.

    Raises:
        FileNotFoundError: If template not found.
        RuntimeError: If Typst compilation fails.
    """
    import shutil

    if config is None:
        config = ReportConfig()

    template_path = TEMPLATE_DIR / f"{template_name}.typ"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Create an isolated temporary workspace for Typst compilation
    tmp_dir = Path(tempfile.mkdtemp(prefix="qcaliper_report_"))

    try:
        # 1. Copy the main unified template if it exists
        unified_template = TEMPLATE_DIR / "template.typ"
        if unified_template.exists():
            shutil.copy2(unified_template, tmp_dir / "template.typ")

        # 2. Copy all chart images into the workspace and update their paths
        new_chart_paths = []
        for i, p in enumerate(data.chart_paths):
            src = Path(p)
            if src.exists():
                dst = tmp_dir / f"chart_{i}{src.suffix}"
                shutil.copy2(src, dst)
                new_chart_paths.append(dst.name)  # Use relative path in workspace
        data.chart_paths = new_chart_paths

        # 3. Render and write the specific report template
        rendered = _render_template(template_path, data, config)
        main_typ_path = tmp_dir / "main.typ"
        main_typ_path.write_text(rendered, encoding="utf-8")

        # 4. Compile the document with root bounded to the workspace
        typst.compile(str(main_typ_path), output=output_path, root=str(tmp_dir))
    except Exception as e:
        raise RuntimeError(f"Typst compilation failed: {e}") from e
    finally:
        # Cleanup workspace
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return str(Path(output_path).resolve())


def _render_template(template_path: Path, data: ReportData, config: ReportConfig) -> str:
    """Read and render a Typst template with data substitution."""
    template = template_path.read_text(encoding="utf-8")

    template = template.replace("{{COMPANY}}", config.company_name)
    template = template.replace("{{TITLE}}", data.title)
    template = template.replace("{{AUTHOR}}", config.author)
    template = template.replace("{{DATE}}", config.date)
    template = template.replace("{{MODULE}}", data.module)

    # Replace all custom fields
    for key, val in data.custom_data.items():
        template = template.replace(f"{{{{{key}}}}}", str(val))

    summary_lines = []
    for key, val in data.summary.items():
        summary_lines.append(f"[{_escape_typst_content(key)}], [{_escape_typst_content(val)}],")
    template = template.replace("{{SUMMARY_ROWS}}", "\n".join(summary_lines))

    table_blocks = []
    for tbl in data.tables:
        headers = tbl.get("headers", [])
        rows = tbl.get("rows", [])

        cols_str = "(" + ", ".join(["auto"] * len(headers)) + ")"
        block = f"#table(\n  columns: {cols_str},\n  inset: 8pt,\n  stroke: 0.5pt,\n"

        if headers:
            header_str = ", ".join([f"[{_escape_typst_content(h)}]" for h in headers])
            block += f"  table.header({header_str}),\n"

        for row in rows:
            row_str = ", ".join([f"[{_escape_typst_content(v)}]" for v in row])
            block += f"  {row_str},\n"

        block += ")\n"
        table_blocks.append(block)
    template = template.replace("{{TABLES}}", "\n\n".join(table_blocks))

    chart_lines = []
    for p in data.chart_paths:
        chart_lines.append(f'#image("{p}", width: 90%)')
    template = template.replace("{{CHARTS}}", "\n\n".join(chart_lines))

    return template


def generate_cpk_report(
    output_path: str,
    cpk_result: CapabilityResult,
    norm_result: NormalityResult,
    chart_path: str,
    config: ReportConfig | None = None,
) -> str:
    """Generate a Cpk analysis PDF report."""
    sg_size = (
        int(cpk_result.sample_size / cpk_result.num_subgroups)
        if cpk_result.num_subgroups and cpk_result.analysis_mode == "cpk_grouped"
        else 1
    )

    basic_headers = ["参数", "统计值", "参数", "统计值"]
    basic_rows = [
        [
            "样本数量 (N)",
            str(cpk_result.sample_size),
            "规格上限 (USL)",
            str(cpk_result.usl) if cpk_result.usl is not None else "无",
        ],
        ["子组大小", str(sg_size), "规格下限 (LSL)", str(cpk_result.lsl) if cpk_result.lsl is not None else "无"],
        ["样本均值 (Mean)", f"{cpk_result.mean:.4f}", "总体标准差 (长期)", f"{cpk_result.std_overall:.4f}"],
        ["目标值", "-", "组内标准差 (短期)", f"{cpk_result.std_within:.4f}"],
    ]

    norm_headers = ["检验方法", "统计量", "P 值", "显著性水平", "结论"]
    norm_rows = [
        [
            norm_result.test_name,
            f"{norm_result.statistic:.4f}",
            f"{norm_result.p_value:.4f}",
            "α = 0.05",
            "服从正态分布" if norm_result.is_normal else "非正态分布 (建议调查特殊变异)",
        ]
    ]

    cap_headers = ["指标类型", "指标名称", "计算值"]
    cap_rows = [
        ["过程能力 (短期潜力)", "Cpk", f"{cpk_result.cpk:.4f}" if cpk_result.cpk is not None else "-"],
        ["过程能力 (短期潜力)", "Cp", f"{cpk_result.cp:.4f}" if cpk_result.cp is not None else "-"],
        ["过程性能 (长期表现)", "Ppk", f"{cpk_result.ppk:.4f}" if cpk_result.ppk is not None else "-"],
        ["过程性能 (长期表现)", "Pp", f"{cpk_result.pp:.4f}" if cpk_result.pp is not None else "-"],
        ["设备能力 (硬件精度)", "Cmk", f"{cpk_result.cmk:.4f}" if cpk_result.cmk is not None else "-"],
    ]

    ppm_headers = ["性能类别", "预期/观测值 (PPM)"]
    ppm_rows = [
        ["实际观测缺陷率", f"{cpk_result.ppm_observed_total:.2f}"],
        ["预期缺陷率 (组内/短期)", f"{cpk_result.ppm_expected_within_total:.2f}"],
        ["预期缺陷率 (整体/长期)", f"{cpk_result.ppm_expected_overall_total:.2f}"],
    ]

    custom_data = {
        "TABLE_BASIC": _format_typst_table(basic_headers, basic_rows),
        "TABLE_NORM": _format_typst_table(norm_headers, norm_rows),
        "TABLE_CAP": _format_typst_table(cap_headers, cap_rows),
        "TABLE_PPM": _format_typst_table(ppm_headers, ppm_rows),
    }

    data = ReportData(
        module="正态分析",
        title="正态性与过程能力分析报告",
        chart_paths=[chart_path] if chart_path else [],
        custom_data=custom_data,
    )

    return render_report("cpk_report", output_path, data, config)


def generate_grr_report(
    output_path: str,
    grr_result: GrrResult,
    chart_paths: list[str],
    config: ReportConfig | None = None,
) -> str:
    """Generate a GRR analysis PDF report following Minitab output conventions."""
    import math

    n = grr_result.n_parts * grr_result.n_operators * grr_result.n_trials

    # ── 1. Data Summary ──
    data_summary_headers = ["参数", "值", "参数", "值"]
    data_summary_rows = [
        ["零件数", str(grr_result.n_parts), "总测量次数", str(n)],
        ["操作者数", str(grr_result.n_operators), "分析方法", "双因素 ANOVA (含交互作用)"],
        ["重复次数", str(grr_result.n_trials), "总均值", f"{grr_result.grand_mean:.4f}"],
    ]

    # ── 2. ANOVA Table (with interaction) ──
    anova_headers = ["来源", "自由度", "SS", "MS", "F", "P"]
    anova_rows = []
    for row in grr_result.anova_table:
        anova_rows.append(
            [
                row.source,
                str(row.df),
                f"{row.ss:.2f}",
                f"{row.ms:.3f}",
                f"{row.f_value:.2f}" if row.f_value else "-",
                f"{row.p_value:.3f}" if row.p_value else "-",
            ]
        )

    # ── 3. Variance Components ──
    var_total = grr_result.var_total if grr_result.var_total > 0 else 1e-12
    var_grr = grr_result.var_repeatability + grr_result.var_reproducibility + grr_result.var_interaction

    def _contrib(v: float) -> str:
        return f"{v / var_total * 100:.2f}" if var_total > 0 else "-"

    var_comp_headers = ["来源", "方差分量", "贡献率 (%)"]
    var_comp_rows = [
        ["合计量具 R&R", f"{var_grr:.4f}", _contrib(var_grr)],
        ["  重复性", f"{grr_result.var_repeatability:.4f}", _contrib(grr_result.var_repeatability)],
        ["  再现性", f"{grr_result.var_reproducibility:.4f}", _contrib(grr_result.var_reproducibility)],
        ["    操作者", f"{grr_result.var_reproducibility:.4f}", _contrib(grr_result.var_reproducibility)],
        ["部件间", f"{grr_result.var_parts:.4f}", _contrib(grr_result.var_parts)],
        ["合计变异", f"{var_total:.4f}", _contrib(var_total)],
    ]

    # ── 4. Study Variation ──
    def _sd(v: float) -> float:
        return math.sqrt(v) if v > 0 else 0.0

    sd_grr = _sd(var_grr)
    sd_ev = _sd(grr_result.var_repeatability)
    sd_av = _sd(grr_result.var_reproducibility)
    sd_pv = _sd(grr_result.var_parts)
    sd_total = _sd(var_total)

    def _pct_sv(sd_val: float) -> str:
        return f"{sd_val / sd_total * 100:.2f}" if sd_total > 0 else "-"

    study_var_headers = ["来源", "标准差 (SD)", "研究变异 (6 x SD)", "%研究变异 (%SV)"]
    study_var_rows = [
        ["合计量具 R&R", f"{sd_grr:.4f}", f"{sd_grr * 6:.4f}", _pct_sv(sd_grr)],
        ["  重复性", f"{sd_ev:.4f}", f"{sd_ev * 6:.4f}", _pct_sv(sd_ev)],
        ["  再现性", f"{sd_av:.4f}", f"{sd_av * 6:.4f}", _pct_sv(sd_av)],
        ["    操作者", f"{sd_av:.4f}", f"{sd_av * 6:.4f}", _pct_sv(sd_av)],
        ["部件间", f"{sd_pv:.4f}", f"{sd_pv * 6:.4f}", _pct_sv(sd_pv)],
        ["合计变异", f"{sd_total:.4f}", f"{sd_total * 6:.4f}", "100.00"],
    ]

    # ── 5. Conclusion summary ──
    pct_grr_grade = "可接受" if grr_result.pct_grr < 10 else "有条件接受" if grr_result.pct_grr < 30 else "不可接受"
    ndc_grade = "可接受" if grr_result.ndc >= 5 else "不可接受"

    conclusion_headers = ["指标", "值", "判定"]
    conclusion_rows = [
        ["%GRR", f"{grr_result.pct_grr:.2f}%", pct_grr_grade],
        ["%PV", f"{grr_result.pct_part_variation:.2f}%", "-"],
        ["ndc (分级数)", str(grr_result.ndc), ndc_grade],
    ]

    custom_data = {
        "TABLE_DATA_SUMMARY": _format_typst_table(data_summary_headers, data_summary_rows),
        "TABLE_ANOVA": _format_typst_table(anova_headers, anova_rows),
        "TABLE_VAR_COMP": _format_typst_table(var_comp_headers, var_comp_rows),
        "TABLE_STUDY_VAR": _format_typst_table(study_var_headers, study_var_rows),
        "TABLE_CONCLUSION": _format_typst_table(conclusion_headers, conclusion_rows),
    }

    data = ReportData(
        module="量具分析",
        title="量具重复性与再现性深度分析报告",
        chart_paths=chart_paths,
        custom_data=custom_data,
    )

    return render_report("grr_report", output_path, data, config)


def generate_msa_report(
    output_path: str,
    bias_result: BiasResult | None = None,
    linear_result: LinearResult | None = None,
    chart_paths: list[str] | None = None,
    bias_data: npt.ArrayLike | None = None,
    bias_col_name: str = "",
    linear_refs: npt.ArrayLike | None = None,
    linear_means: npt.ArrayLike | None = None,
    process_variation: float | None = None,
    config: ReportConfig | None = None,
) -> str:
    """Generate an MSA analysis PDF report following Minitab output conventions."""
    import numpy as np

    if chart_paths is None:
        chart_paths = []

    custom_data: dict[str, str] = {}

    # ── 1. Bias Data Summary ──
    if bias_result is not None and bias_data is not None:
        bias_arr = np.asarray(bias_data)
        bias_sum_headers = ["参数", "值"]
        bias_sum_rows = [
            ["分析类型", "偏差分析 (Bias) - 单样本 t 检验"],
            ["测量列", bias_col_name],
            ["有效样本量", str(len(bias_arr))],
            ["参考值 (标称真值)", f"{bias_result.reference_value:.4f}"],
            ["显著性水平 (alpha)", "0.05"],
        ]
        custom_data["TABLE_BIAS_SUMMARY"] = _format_typst_table(bias_sum_headers, bias_sum_rows)
    else:
        custom_data["TABLE_BIAS_SUMMARY"] = ""

    # ── 2. Bias Result ──
    if bias_result is not None:
        sig_text = "显著 (存在偏差)" if bias_result.is_significant else "不显著 (无显著偏差)"
        bias_headers = ["指标", "值"]
        bias_rows = [
            ["观测均值", f"{bias_result.observed_mean:.4f}"],
            ["参考值", f"{bias_result.reference_value:.4f}"],
            ["偏差 (Bias)", f"{bias_result.mean_bias:.4f}"],
            ["偏差百分比", f"{bias_result.pct_bias:.2f}%"],
            ["t 统计量", f"{bias_result.t_statistic:.4f}"],
            ["p 值", f"{bias_result.p_value:.4f}"],
            ["95% CI 下限", f"{bias_result.ci_lower:.4f}"],
            ["95% CI 上限", f"{bias_result.ci_upper:.4f}"],
            ["显著性结论", sig_text],
        ]
        custom_data["TABLE_BIAS_RESULT"] = _format_typst_table(bias_headers, bias_rows)
    else:
        custom_data["TABLE_BIAS_RESULT"] = ""

    # ── 3. Linearity Data Summary ──
    if linear_result is not None and linear_refs is not None:
        lin_refs_arr = np.asarray(linear_refs)
        lin_sum_headers = ["参数", "值"]
        lin_sum_rows = [
            ["分析类型", "线性分析 (Linearity) - 最小二乘回归"],
            ["参考值个数", str(len(lin_refs_arr))],
            ["参考值范围", f"{float(np.min(lin_refs_arr)):.2f} ~ {float(np.max(lin_refs_arr)):.2f}"],
            ["过程变异 (6\u03c3)", f"{process_variation:.4f}" if process_variation is not None else "未设置"],
        ]
        custom_data["TABLE_LINEAR_SUMMARY"] = _format_typst_table(lin_sum_headers, lin_sum_rows)
    else:
        custom_data["TABLE_LINEAR_SUMMARY"] = ""

    # ── 4. Linearity Result ──
    if linear_result is not None:
        pt_grade = (
            "可接受" if linear_result.pt_ratio < 0.1 else "有条件接受" if linear_result.pt_ratio < 0.3 else "不可接受"
        )
        lin_headers = ["指标", "值"]
        lin_rows = [
            ["斜率 (Slope)", f"{linear_result.slope:.6f}"],
            ["截距 (Intercept)", f"{linear_result.intercept:.6f}"],
            ["R-squared", f"{linear_result.r_squared:.4f}"],
            ["斜率 p 值", f"{linear_result.p_slope:.4f}"],
            ["P/T 比", f"{linear_result.pt_ratio:.4f}"],
            ["P/T 判定", pt_grade],
            ["线性度", f"{linear_result.linearity:.4f}"],
        ]
        custom_data["TABLE_LINEAR_RESULT"] = _format_typst_table(lin_headers, lin_rows)

        point_headers = ["参考值", "观测均值", "偏差"]
        point_rows = [[f"{p.reference:.4f}", f"{p.observed_mean:.4f}", f"{p.bias:.4f}"] for p in linear_result.points]
        custom_data["TABLE_LINEAR_POINTS"] = _format_typst_table(point_headers, point_rows)
    else:
        custom_data["TABLE_LINEAR_RESULT"] = ""
        custom_data["TABLE_LINEAR_POINTS"] = ""

    data = ReportData(
        module="MSA",
        title="测量系统分析 (MSA) 报告",
        chart_paths=chart_paths,
        custom_data=custom_data,
    )

    return render_report("msa_report", output_path, data, config)


def generate_spc_report(
    output_path: str,
    chart1: SpcChartResult | None = None,
    chart2: SpcChartResult | None = None,
    chart1_name: str = "",
    chart2_name: str = "",
    cpk_result: CapabilityResult | None = None,
    chart_paths: list[str] | None = None,
    col_name: str = "",
    chart_type_name: str = "",
    subgroup_size: int = 5,
    data_length: int = 0,
    config: ReportConfig | None = None,
) -> str:
    """Generate an SPC analysis PDF report."""
    if chart_paths is None:
        chart_paths = []

    custom_data: dict[str, str] = {}

    # ── 1. Data Summary ──
    sum_headers = ["参数", "值"]
    sum_rows = [
        ["测量列", col_name],
        ["图表类型", chart_type_name],
        ["数据点数", str(data_length)],
    ]
    if "XBar" in chart_type_name:
        sum_rows.append(["子组大小", str(subgroup_size)])
        n_subgroups = data_length // subgroup_size if subgroup_size > 0 else 0
        sum_rows.append(["子组数", str(n_subgroups)])
    custom_data["TABLE_DATA_SUMMARY"] = _format_typst_table(sum_headers, sum_rows)

    # ── 2. Control Limits ──
    if chart1 is not None and chart2 is not None:
        lim_headers = ["图表", "UCL", "CL (中心线)", "LCL"]
        lim_rows = [
            [
                chart1_name,
                f"{chart1.limits.ucl:.4f}",
                f"{chart1.limits.cl:.4f}",
                f"{chart1.limits.lcl:.4f}",
            ],
            [
                chart2_name,
                f"{chart2.limits.ucl:.4f}",
                f"{chart2.limits.cl:.4f}",
                f"{chart2.limits.lcl:.4f}",
            ],
        ]
        custom_data["TABLE_LIMITS"] = _format_typst_table(lim_headers, lim_rows)
    else:
        custom_data["TABLE_LIMITS"] = ""

    # ── 3. Violations ──
    if chart1 is not None and chart2 is not None:
        all_v = []
        for v in chart1.violations:
            all_v.append([chart1_name, v.rule, f"第 {v.index + 1} 点", v.description])
        for v in chart2.violations:
            all_v.append([chart2_name, v.rule, f"第 {v.index + 1} 点", v.description])

        if all_v:
            viol_headers = ["图表", "规则", "位置", "描述"]
            custom_data["TABLE_VIOLATIONS"] = _format_typst_table(viol_headers, all_v)
        else:
            custom_data["TABLE_VIOLATIONS"] = _format_typst_table(
                ["结论"],
                [["未检测到违规, 过程受控"]],
            )
    else:
        custom_data["TABLE_VIOLATIONS"] = ""

    # ── 4. Cpk Trend ──
    if cpk_result is not None:
        cpk_headers = ["指标", "值"]
        cpk_rows = [
            ["Cpk", f"{cpk_result.cpk:.4f}" if cpk_result.cpk is not None else "-"],
            ["Cp", f"{cpk_result.cp:.4f}" if cpk_result.cp is not None else "-"],
            ["Ppk", f"{cpk_result.ppk:.4f}" if cpk_result.ppk is not None else "-"],
            ["USL", f"{cpk_result.usl:.4f}" if cpk_result.usl is not None else "无"],
            ["LSL", f"{cpk_result.lsl:.4f}" if cpk_result.lsl is not None else "无"],
            ["均值", f"{cpk_result.mean:.4f}"],
        ]
        custom_data["TABLE_CPK"] = _format_typst_table(cpk_headers, cpk_rows)
    else:
        custom_data["TABLE_CPK"] = _format_typst_table(
            ["说明"],
            [["未设置规格限, 跳过过程能力趋势分析"]],
        )

    data = ReportData(
        module="SPC",
        title="统计过程控制 (SPC) 分析报告",
        chart_paths=chart_paths,
        custom_data=custom_data,
    )

    return render_report("spc_report", output_path, data, config)


def generate_doe_report(
    output_path: str,
    design: DoeDesign,
    model: Any = None,
    response: Any = None,
    chart_paths: list[str] | None = None,
    config: ReportConfig | None = None,
) -> str:
    """Generate a DOE analysis PDF report."""

    if chart_paths is None:
        chart_paths = []

    custom_data: dict[str, str] = {}

    # ── 1. Data Summary ──
    sum_headers = ["参数", "值"]
    sum_rows = [
        ["设计类型", design.design_type],
        ["因子数", str(design.n_factors)],
        ["运行次数", str(design.n_runs)],
        ["因子名称", ", ".join(design.factor_names)],
    ]
    custom_data["TABLE_DATA_SUMMARY"] = _format_typst_table(sum_headers, sum_rows)

    # ── Design Type Specific Info ──
    is_fractional = "Fractional" in design.design_type
    if is_fractional:
        base_factors = design.n_factors - 1
        base_names = design.factor_names[:base_factors]
        interaction_str = " #sym.times ".join(base_names)
        resolution = design.n_factors
        alias_pairs = []
        for i in range(base_factors):
            others = [design.factor_names[j] for j in range(base_factors) if j != i]
            others.append(design.factor_names[-1])
            alias_pairs.append(
                f"  - *{design.factor_names[i]}* 与 {design.factor_names[-1]} 的交互别名 (即 {' #sym.times '.join(others)})"
            )

        aliasing_block = "\n".join(alias_pairs)
        custom_data["DESIGN_TYPE_INFO"] = (
            f"\n== 设计类型说明: 部分因子设计 (2^{{{design.n_factors}-1}})\n\n"
            f"本报告采用 *半分式因子设计*, 仅需 {design.n_runs} 次实验即可估计 {design.n_factors} 个因子的主效应"
            f" (全因子设计需要 {2**design.n_factors} 次)。\n\n"
            f"*生成关系*: {design.factor_names[-1]} = {interaction_str}\n\n"
            f"*设计分辨力*: Resolution {to_roman(resolution)} (主效应与 {resolution - 1} 阶交互混杂)\n\n"
            f"*混杂结构 (Aliasing)*:\n"
            f"{aliasing_block}\n\n"
            f"*注意*: 由于采用部分因子设计, 部分效应存在混杂。"
            f" 当某一因子效应显著时, 需结合工程知识判断是主效应还是交互效应的贡献。\n"
        )
    else:
        custom_data["DESIGN_TYPE_INFO"] = (
            "\n== 设计类型说明: 全因子设计 (2^{" + str(design.n_factors) + "})\n\n"
            f"本报告采用 *全因子设计*, 共 {design.n_runs} 次实验, 可独立估计所有 {design.n_factors} 个主效应及其交互效应, "
            f"无任何混杂 (Confounding)。\n\n"
            f"*优势*: 所有效应均可独立估计, 结论可靠性最高。\n\n"
            f"*适用场景*: 因子数较少 (通常 k #sym.lt.eq 5) 且需要分析交互效应时。\n"
        )

    # ── 2. Design Matrix ──
    dm_headers = ["Run", "顺序", *design.factor_names]
    dm_rows = []
    for i in range(design.n_runs):
        row = [str(i + 1), str(design.run_order[i] + 1)]
        for val in design.design_matrix[i]:
            row.append(f"{val:+.0f}")
        dm_rows.append(row)
    custom_data["TABLE_DESIGN_MATRIX"] = _format_typst_table(dm_headers, dm_rows)

    # ── 3. Factor Effects ──
    if model is not None:
        effects = model.params[1:]
        pvalues = model.pvalues[1:]
        factor_names = design.factor_names

        effect_headers = ["因子", "效应值", "回归系数", "t 值", "p 值", "显著性"]
        effect_rows = []
        for idx, name in enumerate(factor_names):
            effect_val = effects[idx]
            coef = model.params[idx + 1]
            t_val = model.tvalues[idx + 1]
            p_val = pvalues[idx]
            sig = "显著" if p_val < 0.05 else "边际显著" if p_val < 0.10 else "不显著"
            effect_rows.append(
                [
                    name,
                    f"{effect_val:.4f}",
                    f"{coef:.4f}",
                    f"{t_val:.4f}",
                    f"{p_val:.4f}",
                    sig,
                ]
            )
        custom_data["TABLE_EFFECTS"] = _format_typst_table(effect_headers, effect_rows)

        # ── 4. Model Statistics ──
        stat_headers = ["统计量", "值"]
        stat_rows = [
            ["R²", f"{model.rsquared:.4f}"],
            ["R²-adjusted", f"{model.rsquared_adj:.4f}"],
            ["F 统计量", f"{model.fvalue:.4f}"],
            ["模型 p 值", f"{model.f_pvalue:.4f}"],
            ["残差自由度", str(int(model.df_resid))],
            ["MSE (残差均方)", f"{model.mse_resid:.4f}"],
        ]
        custom_data["TABLE_MODEL_STATS"] = _format_typst_table(stat_headers, stat_rows)
    else:
        custom_data["TABLE_EFFECTS"] = ""
        custom_data["TABLE_MODEL_STATS"] = ""

    data = ReportData(
        module="DOE",
        title="实验设计 (DOE) 分析报告",
        chart_paths=chart_paths,
        custom_data=custom_data,
    )

    return render_report("doe_report", output_path, data, config)


def check_typst_available() -> bool:
    """Check if Python typst package is available."""
    try:
        import typst  # noqa: F401

        return True
    except ImportError:
        return False
