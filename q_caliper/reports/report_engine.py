"""Report engine — Typst template rendering and PDF generation via Python typst package."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import typst


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


TEMPLATE_DIR = Path(__file__).parent / "templates"


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
    if config is None:
        config = ReportConfig()

    template_path = TEMPLATE_DIR / f"{template_name}.typ"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    rendered = _render_template(template_path, data, config)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".typ", delete=False, encoding="utf-8") as f:
        f.write(rendered)
        temp_path = f.name

    try:
        typst.compile(temp_path, output=output_path)
    except Exception as e:
        raise RuntimeError(f"Typst compilation failed: {e}") from e
    finally:
        Path(temp_path).unlink(missing_ok=True)

    return str(Path(output_path).resolve())


def _render_template(template_path: Path, data: ReportData, config: ReportConfig) -> str:
    """Read and render a Typst template with data substitution."""
    template = template_path.read_text(encoding="utf-8")

    template = template.replace("{{COMPANY}}", config.company_name)
    template = template.replace("{{TITLE}}", data.title)
    template = template.replace("{{AUTHOR}}", config.author)
    template = template.replace("{{DATE}}", config.date)
    template = template.replace("{{MODULE}}", data.module)

    summary_lines = []
    for key, val in data.summary.items():
        summary_lines.append(f"| {key} | {val} |")
    template = template.replace("{{SUMMARY_ROWS}}", "\n".join(summary_lines))

    table_blocks = []
    for tbl in data.tables:
        headers = tbl.get("headers", [])
        rows = tbl.get("rows", [])
        block = "| " + " | ".join(headers) + " |\n"
        block += "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in rows)
        table_blocks.append(block)
    template = template.replace("{{TABLES}}", "\n\n".join(table_blocks))

    chart_lines = []
    for p in data.chart_paths:
        abs_p = str(Path(p).resolve()).replace("\\", "/")
        chart_lines.append(f'#image("{abs_p}", width: 90%)')
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
    data = ReportData(
        module="Cpk",
        title="Cpk 过程能力分析报告",
        summary={
            "均值": f"{cpk_result.mean:.4f}",
            "Cpk": f"{cpk_result.cpk:.4f}",
            "Ppk": f"{cpk_result.ppk:.4f}",
            "USL": str(cpk_result.usl) if cpk_result.usl else "未设置",
            "LSL": str(cpk_result.lsl) if cpk_result.lsl else "未设置",
            "总超规格比例": f"{cpk_result.pct_total_out:.4%}",
            "正态性": "正态" if norm_result.is_normal else "非正态",
        },
        tables=[
            {
                "headers": ["指标", "值"],
                "rows": [
                    ["Cp", f"{cpk_result.cp:.4f}"],
                    ["Cpk", f"{cpk_result.cpk:.4f}"],
                    ["Pp", f"{cpk_result.pp:.4f}"],
                    ["Ppk", f"{cpk_result.ppk:.4f}"],
                ],
            }
        ],
        chart_paths=[chart_path] if chart_path else [],
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
