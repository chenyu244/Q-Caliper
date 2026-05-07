"""Report engine — Typst template rendering and PDF generation via Python typst package."""

from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import typst


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


def _format_typst_table(headers: list[str], rows: list[list[str]]) -> str:
    """Helper to format a raw Typst table from headers and rows."""
    if not headers and not rows:
        return ""
    col_count = len(headers) if headers else len(rows[0])
    cols_str = "(" + ", ".join(["auto"] * col_count) + ")"
    block = f"#table(\n  columns: {cols_str},\n  inset: 8pt,\n  stroke: 0.5pt,\n  align: center,\n"
    if headers:
        header_str = ", ".join([f"[*{(h)}*]" for h in headers])
        block += f"  table.header({header_str}),\n"
    for row in rows:
        row_str = ", ".join([f"[{str(v).replace('[', '(').replace(']', ')')}]" for v in row])
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
    import tempfile
    
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
                new_chart_paths.append(dst.name) # Use relative path in workspace
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
        summary_lines.append(f"[{key}], [{val}],")
    template = template.replace("{{SUMMARY_ROWS}}", "\n".join(summary_lines))

    table_blocks = []
    for tbl in data.tables:
        headers = tbl.get("headers", [])
        rows = tbl.get("rows", [])
        
        cols_str = "(" + ", ".join(["auto"] * len(headers)) + ")"
        block = f"#table(\n  columns: {cols_str},\n  inset: 8pt,\n  stroke: 0.5pt,\n"
        
        if headers:
            header_str = ", ".join([f"[{h}]" for h in headers])
            block += f"  table.header({header_str}),\n"
            
        for row in rows:
            row_str = ", ".join([f"[{str(v).replace('[', '(').replace(']', ')')}]" for v in row])
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
    cpk_result,
    norm_result,
    chart_path: str,
    config: ReportConfig | None = None,
) -> str:
    """Generate a Cpk analysis PDF report."""
    sg_size = int(cpk_result.sample_size / cpk_result.num_subgroups) if cpk_result.num_subgroups and cpk_result.analysis_mode == "cpk_grouped" else 1
    
    basic_headers = ["参数", "统计值", "参数", "统计值"]
    basic_rows = [
        ["样本数量 (N)", str(cpk_result.sample_size), "规格上限 (USL)", str(cpk_result.usl) if cpk_result.usl is not None else "无"],
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
            "服从正态分布" if norm_result.is_normal else "非正态分布 (建议调查特殊变异)"
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
    grr_result,
    chart_paths: list[str],
    config: ReportConfig | None = None,
) -> str:
    """Generate a GRR analysis PDF report."""
    anova_rows = []
    for row in grr_result.anova_table:
        anova_rows.append([
            row.source,
            f"{row.ss:.4f}",
            str(row.df),
            f"{row.ms:.4f}",
            f"{row.f_value:.2f}" if row.f_value else "-",
            f"{row.p_value:.4f}" if row.p_value else "-",
        ])

    data = ReportData(
        module="GRR",
        title="GRR 量具重复性与再现性分析报告",
        summary={
            "%GRR": f"{grr_result.pct_grr:.2f}%",
            "ndc": str(grr_result.ndc),
            "重复性 (EV)": f"{grr_result.var_repeatability:.6f}",
            "再现性 (AV)": f"{grr_result.var_reproducibility:.6f}",
            "零件 (PV)": f"{grr_result.var_parts:.6f}",
        },
        tables=[
            {
                "headers": ["来源", "SS", "df", "MS", "F", "p-value"],
                "rows": anova_rows,
            }
        ],
        chart_paths=chart_paths,
    )

    return render_report("grr_report", output_path, data, config)


def check_typst_available() -> bool:
    """Check if Python typst package is available."""
    try:
        import typst  # noqa: F401

        return True
    except ImportError:
        return False
