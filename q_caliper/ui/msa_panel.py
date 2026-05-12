"""MSA 测量系统分析 Panel — bias and linearity analysis with chart overlay."""

# isort: skip_file
from __future__ import annotations

import matplotlib

matplotlib.use("QtAgg")
import numpy as np
import pandas as pd
from pathlib import Path
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CardWidget,
    FluentIcon,
    InfoBar,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    TitleLabel,
    SegmentedWidget,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy.typing as npt

from q_caliper.core.msa import analyze_bias, analyze_linearity, BiasResult, LinearResult
from q_caliper.ui.grr_panel import GrrInputCard, GrrChartsDashboard, GrrResult


def _setup_matplotlib_font() -> None:
    """Configure matplotlib to use a CJK font for Chinese labels."""
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["axes.unicode_minus"] = False


_setup_matplotlib_font()


class MsaInputCard(CardWidget):
    """Unified MSA parameter input following Cpk panel style."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header_row = QHBoxLayout()
        header = StrongBodyLabel("分析参数设置")
        header.setStyleSheet("font-size: 14px;")
        header_row.addWidget(header)
        header_row.addStretch()

        self.report_btn = PushButton("导出 PDF 报告")
        self.report_btn.setIcon(FluentIcon.PRINT)
        self.report_btn.setFixedWidth(130)
        self.report_btn.setFixedHeight(30)
        self.report_btn.clicked.connect(self._on_export_pdf)
        self.report_btn.setEnabled(False)
        header_row.addWidget(self.report_btn)
        layout.addLayout(header_row)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 8, 0, 0)
        content_layout.setSpacing(20)

        # ── Left: Bias inputs ──
        bias_card = CardWidget()
        bias_card.setStyleSheet("CardWidget { border: 1px solid #e0e0e0; border-radius: 6px; background: #fbfbfb; }")
        bias_layout = QVBoxLayout(bias_card)
        bias_layout.setContentsMargins(12, 8, 12, 8)

        bias_title = StrongBodyLabel("偏差分析 (Bias)")
        bias_title.setStyleSheet("font-size: 13px; color: #0078D4;")
        bias_layout.addWidget(bias_title)

        bias_form = QFormLayout()
        bias_form.setSpacing(6)

        self.bias_measure_combo = QComboBox()
        self.bias_measure_combo.setPlaceholderText("-- 选择测量列 --")
        self.bias_measure_combo.setMinimumWidth(160)
        self.bias_measure_combo.setFixedHeight(30)
        bias_form.addRow("测量数据列:", self.bias_measure_combo)

        self.ref_spin = QDoubleSpinBox()
        self.ref_spin.setRange(-1e12, 1e12)
        self.ref_spin.setDecimals(4)
        self.ref_spin.setValue(0.0)
        self.ref_spin.setFixedHeight(30)
        bias_form.addRow("参考值 (标称真值):", self.ref_spin)

        bias_layout.addLayout(bias_form)

        self.bias_calc_btn = PrimaryPushButton("执行偏差分析")
        self.bias_calc_btn.setIcon(FluentIcon.PLAY)
        self.bias_calc_btn.setFixedHeight(32)
        self.bias_calc_btn.clicked.connect(self._on_bias_calculate)
        bias_layout.addWidget(self.bias_calc_btn)

        content_layout.addWidget(bias_card)

        # ── Right: Linearity inputs ──
        lin_card = CardWidget()
        lin_card.setStyleSheet("CardWidget { border: 1px solid #e0e0e0; border-radius: 6px; background: #fbfbfb; }")
        lin_layout = QVBoxLayout(lin_card)
        lin_layout.setContentsMargins(12, 8, 12, 8)

        lin_title = StrongBodyLabel("线性分析 (Linearity)")
        lin_title.setStyleSheet("font-size: 13px; color: #0078D4;")
        lin_layout.addWidget(lin_title)

        lin_form = QFormLayout()
        lin_form.setSpacing(6)

        self.lin_ref_combo = QComboBox()
        self.lin_ref_combo.setPlaceholderText("-- 选择参考值列 --")
        self.lin_ref_combo.setMinimumWidth(160)
        self.lin_ref_combo.setFixedHeight(30)
        lin_form.addRow("参考值列:", self.lin_ref_combo)

        self.lin_measure_combo = QComboBox()
        self.lin_measure_combo.setPlaceholderText("-- 选择测量列 --")
        self.lin_measure_combo.setMinimumWidth(160)
        self.lin_measure_combo.setFixedHeight(30)
        lin_form.addRow("测量值列:", self.lin_measure_combo)

        self.pv_spin = QDoubleSpinBox()
        self.pv_spin.setRange(0, 1e12)
        self.pv_spin.setDecimals(4)
        self.pv_spin.setValue(0.0)
        self.pv_spin.setFixedHeight(30)
        lin_form.addRow("过程变异 (6\u03c3):", self.pv_spin)

        lin_layout.addLayout(lin_form)

        self.lin_calc_btn = PrimaryPushButton("执行线性分析")
        self.lin_calc_btn.setIcon(FluentIcon.PLAY)
        self.lin_calc_btn.setFixedHeight(32)
        self.lin_calc_btn.clicked.connect(self._on_linear_calculate)
        lin_layout.addWidget(self.lin_calc_btn)

        content_layout.addWidget(lin_card)

        layout.addLayout(content_layout)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df
        numeric_cols = [str(c) for c in df.select_dtypes(include=[np.number]).columns]
        all_cols = [str(c) for c in df.columns]

        self.bias_measure_combo.clear()
        self.bias_measure_combo.addItems(numeric_cols)

        self.lin_ref_combo.clear()
        self.lin_ref_combo.addItems(all_cols)
        self.lin_measure_combo.clear()
        self.lin_measure_combo.addItems(numeric_cols)

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        """Pre-select columns based on roles from Data Center."""
        if mapping.get("测量值"):
            col = mapping["测量值"][0]
            idx = self.bias_measure_combo.findText(col)
            if idx >= 0:
                self.bias_measure_combo.setCurrentIndex(idx)
            idx2 = self.lin_measure_combo.findText(col)
            if idx2 >= 0:
                self.lin_measure_combo.setCurrentIndex(idx2)

    def _on_bias_calculate(self) -> None:
        if self.df is None:
            InfoBar.warning("提示", "请先在数据中心加载数据文件", parent=self)
            return

        col = self.bias_measure_combo.currentText()
        if not col:
            InfoBar.warning("提示", "请选择测量数据列", parent=self)
            return

        data = self.df[col].dropna().values
        if len(data) < 3:
            InfoBar.warning("数据不足", "至少需要 3 个有效数据点", parent=self)
            return

        ref_val = self.ref_spin.value()

        try:
            result = analyze_bias(data, ref_val)
            parent = self.parent()
            while parent and not isinstance(parent, PositionAnalysisPanel):
                parent = parent.parent()
            if isinstance(parent, PositionAnalysisPanel):
                parent.show_bias_results(data, result, col)
                self.report_btn.setEnabled(True)
        except Exception as e:
            InfoBar.error("计算错误", str(e), parent=self, duration=-1)

    def _on_linear_calculate(self) -> None:
        if self.df is None:
            InfoBar.warning("提示", "请先在数据中心加载数据文件", parent=self)
            return

        ref_col = self.lin_ref_combo.currentText()
        meas_col = self.lin_measure_combo.currentText()
        if not all([ref_col, meas_col]):
            InfoBar.warning("提示", "请选择所有必要的列", parent=self)
            return

        try:
            df = self.df.copy()
            df[ref_col] = pd.to_numeric(df[ref_col], errors="coerce")
            df[meas_col] = pd.to_numeric(df[meas_col], errors="coerce")
            df = df.dropna(subset=[ref_col, meas_col])

            refs_raw = df[ref_col].values
            meas_raw = df[meas_col].values

            unique_refs = np.sort(np.unique(refs_raw)).astype(np.float64)
            if len(unique_refs) < 3:
                InfoBar.warning("数据不足", "至少需要 3 个不同的参考值", parent=self)
                return

            avg_means = np.array([meas_raw[refs_raw == r].mean() for r in unique_refs], dtype=np.float64)

            # Calculate process variation from USL/LSL or fallback to 6*StdDev
            usl = self.usl_spin.value()
            lsl = self.lsl_spin.value()
            pv = (usl - lsl) if (usl > -1e11 and lsl < 1e11) else float(np.std(meas_raw, ddof=1) * 6)

            result = analyze_linearity(unique_refs, avg_means, pv)

            parent = self.parent()
            while parent and not isinstance(parent, PositionAnalysisPanel):
                parent = parent.parent()
            if isinstance(parent, PositionAnalysisPanel):
                parent.show_linear_results(unique_refs, avg_means, result, pv)
                self.report_btn.setEnabled(True)
        except Exception as e:
            InfoBar.error("计算错误", str(e), parent=self, duration=-1)

    def _on_export_pdf(self) -> None:
        from q_caliper.reports.report_engine import generate_msa_report
        from q_caliper.ui.utils import generate_report_filename

        parent = self.parent()
        while parent and not isinstance(parent, PositionAnalysisPanel):
            parent = parent.parent()

        if not parent:
            return

        default_name = generate_report_filename("MSA分析报告.pdf", str(Path.cwd()))
        path, _ = QFileDialog.getSaveFileName(self, "导出分析报告", default_name, "PDF 文件 (*.pdf)")
        if not path:
            return

        try:
            chart_paths = []
            for i, fig in enumerate(parent.charts.figures):
                tmp_img = str(Path(f"tmp_msa_chart_{i}.png").resolve())
                fig.savefig(tmp_img, dpi=120)
                chart_paths.append(tmp_img)

            generate_msa_report(
                path,
                bias_result=parent.last_bias_result,
                linear_result=parent.last_linear_result,
                chart_paths=chart_paths,
                bias_data=parent.last_bias_data,
                bias_col_name=parent.last_bias_col,
                linear_refs=parent.last_linear_refs,
                linear_means=parent.last_linear_means,
                process_variation=parent.last_process_variation,
            )
            InfoBar.success("导出成功", f"报告已保存至: {path}", parent=self, duration=5000)
        except Exception as e:
            InfoBar.error("导出失败", f"PDF 生成过程中发生错误：\n{e!s}", parent=self, duration=-1)
        finally:
            for p in chart_paths:
                Path(p).unlink(missing_ok=True)


class MsaChartsDashboard(QWidget):
    """Charts dashboard with key stats overlay."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        row = QHBoxLayout(container)
        row.setSpacing(12)

        self.fig_bias = Figure(figsize=(5, 4), dpi=90)
        self.canvas_bias = FigureCanvas(self.fig_bias)
        self.canvas_bias.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas_bias.setMinimumHeight(320)
        row.addWidget(self.canvas_bias)

        self.fig_linear = Figure(figsize=(5, 4), dpi=90)
        self.canvas_linear = FigureCanvas(self.fig_linear)
        self.canvas_linear.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas_linear.setMinimumHeight(320)
        row.addWidget(self.canvas_linear)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        self.figures = [self.fig_bias, self.fig_linear]

    def plot_bias(self, data: npt.NDArray[np.float64], result: BiasResult, col_name: str) -> None:
        fig = self.fig_bias
        fig.clear()
        gs = fig.add_gridspec(1, 2, width_ratios=[3, 1.6], wspace=0.1)
        ax = fig.add_subplot(gs[0])

        n_bins = min(30, max(10, len(data) // 3))
        ax.hist(
            data,
            bins=n_bins,
            density=True,
            alpha=0.7,
            color="#4A90D9",
            edgecolor="white",
            linewidth=0.5,
            label="数据分布",
        )

        x = np.linspace(data.min(), data.max(), 200)
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        if std > 0:
            y = (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)
            ax.plot(x, y, color="#E74C3C", linewidth=1.5, label="正态拟合")

        ax.axvline(
            float(result.reference_value),
            color="#27AE60",
            linestyle="--",
            linewidth=1.5,
            label=f"参考值={result.reference_value}",
        )
        ax.axvline(float(mean), color="#E74C3C", linestyle="-", linewidth=1.5, label=f"均值={mean:.4f}")

        ax.set_title(f"{col_name} 偏差分析", fontsize=12, fontweight="bold")
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(True, alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        ax_stats = fig.add_subplot(gs[1])
        ax_stats.axis("off")
        sig_text = "显著 (存在偏差)" if result.is_significant else "不显著 (无显著偏差)"
        stats_text = (
            f"偏差分析结果\n"
            f"\n"
            f"观测均值:    {result.observed_mean:.4f}\n"
            f"参考值:      {result.reference_value:.4f}\n"
            f"偏差 (Bias): {result.mean_bias:.4f}\n"
            f"偏差百分比:  {result.pct_bias:.2f}%\n"
            f"\n"
            f"t 统计量:    {result.t_statistic:.4f}\n"
            f"p 值:        {result.p_value:.4f}\n"
            f"95% CI:      [{result.ci_lower:.4f},\n"
            f"              {result.ci_upper:.4f}]\n"
            f"\n"
            f"结论: {sig_text}\n"
        )
        ax_stats.text(
            0, 1, stats_text, transform=ax_stats.transAxes, verticalalignment="top", fontsize=9, linespacing=1.5
        )

        fig.tight_layout()
        self.canvas_bias.draw()

    def plot_linearity(self, result: LinearResult, col_name: str = "") -> None:
        fig = self.fig_linear
        fig.clear()
        gs = fig.add_gridspec(1, 2, width_ratios=[3, 1.6], wspace=0.1)
        ax = fig.add_subplot(gs[0])

        refs = [p.reference for p in result.points]
        biases = [p.bias for p in result.points]

        ax.scatter(refs, biases, color="#4A90D9", s=60, zorder=5, label="观测偏差")
        ax.plot(
            result.regression_line_x,
            result.regression_line_y,
            color="#E74C3C",
            linewidth=1.5,
            label=f"回归线 (y={result.slope:.4f}x+{result.intercept:.4f})",
        )
        ax.axhline(0, color="#27AE60", linestyle="--", linewidth=1, alpha=0.7, label="零偏差线")

        ax.set_xlabel("参考值", fontsize=10)
        ax.set_ylabel("偏差", fontsize=10)
        ax.set_title("线性分析 (偏差 vs 参考值)", fontsize=12, fontweight="bold")
        ax.legend(fontsize=8, loc="best")
        ax.grid(True, alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        ax_stats = fig.add_subplot(gs[1])
        ax_stats.axis("off")
        pt_grade = "可接受" if result.pt_ratio < 0.1 else "有条件接受" if result.pt_ratio < 0.3 else "不可接受"
        stats_text = (
            f"线性分析结果\n"
            f"\n"
            f"斜率 (Slope):     {result.slope:.6f}\n"
            f"截距 (Intercept): {result.intercept:.6f}\n"
            f"R-squared:         {result.r_squared:.4f}\n"
            f"斜率 p 值:         {result.p_slope:.4f}\n"
            f"\n"
            f"P/T 比:            {result.pt_ratio:.4f}\n"
            f"判定:              {pt_grade}\n"
            f"线性度:            {result.linearity:.4f}\n"
        )
        ax_stats.text(
            0, 1, stats_text, transform=ax_stats.transAxes, verticalalignment="top", fontsize=9, linespacing=1.5
        )

        fig.tight_layout()
        self.canvas_linear.draw()


class PositionAnalysisPanel(QWidget):
    """Original MSA analysis page (bias and linearity) renamed for integration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self.last_bias_result: BiasResult | None = None
        self.last_linear_result: LinearResult | None = None
        self.last_bias_data: npt.NDArray[np.float64] | None = None
        self.last_bias_col: str | None = None
        self.last_linear_refs: npt.NDArray[np.float64] | None = None
        self.last_linear_means: npt.NDArray[np.float64] | None = None
        self.last_process_variation: float | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(15)

        self.input_card = MsaInputCard(self)
        layout.addWidget(self.input_card)

        self.charts = MsaChartsDashboard(self)
        layout.addWidget(self.charts, 1)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df
        self.input_card.set_dataframe(df)

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        self.input_card.set_selected_columns(mapping)

    def show_bias_results(self, data: npt.NDArray[np.float64], result: BiasResult, col_name: str) -> None:
        self.last_bias_result = result
        self.last_bias_data = data
        self.last_bias_col = col_name
        self.charts.plot_bias(data, result, col_name)

    def show_linear_results(
        self,
        refs: npt.NDArray[np.float64],
        means: npt.NDArray[np.float64],
        result: LinearResult,
        process_variation: float,
    ) -> None:
        self.last_linear_result = result
        self.last_linear_refs = refs
        self.last_linear_means = means
        self.last_process_variation = process_variation
        self.charts.plot_linearity(result)


class GrrAnalysisPanel(QWidget):
    """GRR analysis page integrated from grr_panel.py."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self.last_result: GrrResult | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(15)

        self.input_card = GrrInputCard(self)
        layout.addWidget(self.input_card)

        self.charts = GrrChartsDashboard(self)
        layout.addWidget(self.charts, 1)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df
        self.input_card.set_dataframe(df)

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        self.input_card.set_selected_columns(mapping)

    def show_results(self, result: GrrResult, part_names: list[str], operator_names: list[str]) -> None:
        self.last_result = result
        self.charts.plot_all(result, part_names, operator_names)


class MsaPanelWidget(QWidget):
    """Unified MSA interface with GRR and Position Analysis tabs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("msa_panel")
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 10, 20, 20)
        self.main_layout.setSpacing(10)

        # Header
        header_row = QHBoxLayout()
        header = TitleLabel("测量系统分析 (MSA)")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_row.addWidget(header)
        header_row.addStretch()
        self.main_layout.addLayout(header_row)

        # Tab Switcher
        self.pivot = SegmentedWidget(self)
        self.pivot.setFixedWidth(400)

        from PySide6.QtWidgets import QStackedWidget

        self.stacked_widget = QStackedWidget(self)

        self.grr_interface = GrrAnalysisPanel(self)
        self.pos_interface = PositionAnalysisPanel(self)

        self._add_tab(self.grr_interface, "grr", "量具 R&R (GRR)")
        self._add_tab(self.pos_interface, "position", "位置分析 (偏倚/线性)")

        self.main_layout.addWidget(self.pivot, 0, Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.stacked_widget, 1)

        self.pivot.setCurrentItem("grr")
        self.stacked_widget.setCurrentWidget(self.grr_interface)

    def _add_tab(self, widget: QWidget, name: str, text: str) -> None:
        widget.setObjectName(name)
        self.stacked_widget.addWidget(widget)
        self.pivot.addItem(routeKey=name, text=text, onClick=lambda: self.stacked_widget.setCurrentWidget(widget))

    def set_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self.grr_interface.set_dataframe(df)
        self.pos_interface.set_dataframe(df)

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        self.grr_interface.set_selected_columns(mapping)
        self.pos_interface.set_selected_columns(mapping)
