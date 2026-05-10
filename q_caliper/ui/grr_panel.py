"""量具分析 Panel — data input, ANOVA calculation, 6-chart dashboard with key stats overlay."""

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
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    InfoBar,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    TitleLabel,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy.typing as npt

from q_caliper.core.grr import calculate_grr, validate_grr_data, GrrResult


def _setup_matplotlib_font() -> None:
    """Configure matplotlib to use a CJK font for Chinese labels."""
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["axes.unicode_minus"] = False


_setup_matplotlib_font()


class GrrInputCard(CardWidget):
    """GRR parameter and column mapping input with collapsible support."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self._collapsed = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(0)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header = StrongBodyLabel("分析参数设置")
        header.setStyleSheet("font-size: 14px;")
        header_row.addWidget(header)
        header_row.addStretch()

        self.toggle_btn = PushButton("")
        self.toggle_btn.setIcon(FluentIcon.UP)
        self.toggle_btn.setFixedSize(28, 28)
        self.toggle_btn.setStyleSheet("PushButton { border: none; }")
        self.toggle_btn.setToolTip("折叠/展开参数区")
        self.toggle_btn.clicked.connect(self._toggle_collapse)
        header_row.addWidget(self.toggle_btn)

        self.main_layout.addLayout(header_row)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 8, 0, 0)
        self.content_layout.setSpacing(0)

        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(20)

        form_layout.addWidget(QLabel("测量数据列:"), 0, 0)
        form_layout.addWidget(QLabel("操作者列:"), 0, 1)
        form_layout.addWidget(QLabel("零件列:"), 0, 2)

        self.measure_combo = QComboBox()
        self.measure_combo.setPlaceholderText("-- 测量数据列 --")
        self.measure_combo.setMinimumWidth(160)
        self.measure_combo.setFixedHeight(32)
        form_layout.addWidget(self.measure_combo, 1, 0)

        self.operator_combo = QComboBox()
        self.operator_combo.setPlaceholderText("-- 操作者列 --")
        self.operator_combo.setMinimumWidth(160)
        self.operator_combo.setFixedHeight(32)
        form_layout.addWidget(self.operator_combo, 1, 1)

        self.part_combo = QComboBox()
        self.part_combo.setPlaceholderText("-- 零件列 --")
        self.part_combo.setMinimumWidth(160)
        self.part_combo.setFixedHeight(32)
        form_layout.addWidget(self.part_combo, 1, 2)

        form_layout.addWidget(QLabel("零件数:"), 2, 0)
        form_layout.addWidget(QLabel("操作者数:"), 2, 1)
        form_layout.addWidget(QLabel("重复次数:"), 2, 2)

        self.n_parts_spin = QSpinBox()
        self.n_parts_spin.setRange(2, 100)
        self.n_parts_spin.setValue(10)
        self.n_parts_spin.setFixedHeight(32)
        form_layout.addWidget(self.n_parts_spin, 3, 0)

        self.n_ops_spin = QSpinBox()
        self.n_ops_spin.setRange(2, 20)
        self.n_ops_spin.setValue(3)
        self.n_ops_spin.setFixedHeight(32)
        form_layout.addWidget(self.n_ops_spin, 3, 1)

        self.n_trials_spin = QSpinBox()
        self.n_trials_spin.setRange(2, 20)
        self.n_trials_spin.setValue(3)
        self.n_trials_spin.setFixedHeight(32)
        form_layout.addWidget(self.n_trials_spin, 3, 2)

        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)
        self.calc_btn = PrimaryPushButton("执行分析")
        self.calc_btn.setIcon(FluentIcon.PLAY)
        self.calc_btn.setFixedWidth(120)
        self.calc_btn.setFixedHeight(32)
        self.calc_btn.clicked.connect(self._on_calculate)
        btn_layout.addWidget(self.calc_btn)

        self.report_btn = PushButton("导出 PDF")
        self.report_btn.setIcon(FluentIcon.PRINT)
        self.report_btn.setFixedWidth(120)
        self.report_btn.setFixedHeight(32)
        self.report_btn.clicked.connect(self._on_export_pdf)
        self.report_btn.setEnabled(False)
        btn_layout.addWidget(self.report_btn)

        form_layout.addLayout(btn_layout, 0, 3, 4, 1, Qt.AlignmentFlag.AlignVCenter)
        form_layout.setColumnStretch(1, 1)

        self.content_layout.addLayout(form_layout)
        self.main_layout.addWidget(self.content_widget)

    def _toggle_collapse(self) -> None:
        if self.content_widget.parent() is not None:
            self.main_layout.removeWidget(self.content_widget)
            self.content_widget.setParent(None)
            self.toggle_btn.setIcon(FluentIcon.DOWN)
        else:
            self.main_layout.addWidget(self.content_widget)
            self.toggle_btn.setIcon(FluentIcon.UP)
        self.main_layout.activate()

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df
        cols = [str(c) for c in df.columns]
        self.measure_combo.clear()
        self.operator_combo.clear()
        self.part_combo.clear()

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.measure_combo.addItems([str(c) for c in numeric_cols])
        self.operator_combo.addItems(cols)
        self.part_combo.addItems(cols)

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        """Pre-select columns based on roles from Data Center."""
        if mapping.get("测量值"):
            idx = self.measure_combo.findText(mapping["测量值"][0])
            if idx >= 0:
                self.measure_combo.setCurrentIndex(idx)

        if mapping.get("操作者"):
            idx = self.operator_combo.findText(mapping["操作者"][0])
            if idx >= 0:
                self.operator_combo.setCurrentIndex(idx)

        if mapping.get("零件"):
            idx = self.part_combo.findText(mapping["零件"][0])
            if idx >= 0:
                self.part_combo.setCurrentIndex(idx)

    def _on_calculate(self) -> None:
        if self.df is None:
            InfoBar.warning("提示", "请先在数据中心加载数据文件", parent=self)
            return

        measure_col = self.measure_combo.currentText()
        operator_col = self.operator_combo.currentText()
        part_col = self.part_combo.currentText()

        if not all([measure_col, operator_col, part_col]):
            InfoBar.warning("提示", "请选择所有必要的列", parent=self)
            return

        n_parts = self.n_parts_spin.value()
        n_ops = self.n_ops_spin.value()
        n_trials = self.n_trials_spin.value()

        df = self.df.copy()
        try:
            df[measure_col] = pd.to_numeric(df[measure_col], errors="coerce")
            df = df.dropna(subset=[measure_col, operator_col, part_col])

            parts = sorted(df[part_col].unique())
            operators = sorted(df[operator_col].unique())

            if len(parts) != n_parts:
                InfoBar.warning("零件数不匹配", f"数据中有 {len(parts)} 个不同零件, 设置为 {n_parts}", parent=self)
                n_parts = len(parts)
                self.n_parts_spin.setValue(n_parts)
            if len(operators) != n_ops:
                InfoBar.warning(
                    "操作者数不匹配", f"数据中有 {len(operators)} 个不同操作者, 设置为 {n_ops}", parent=self
                )
                n_ops = len(operators)
                self.n_ops_spin.setValue(n_ops)

            data_flat = []
            for p in parts:
                for o in operators:
                    subset = df[(df[part_col] == p) & (df[operator_col] == o)][measure_col].values
                    if len(subset) < n_trials:
                        InfoBar.error(
                            "数据不足", f"零件={p}, 操作者={o} 只有 {len(subset)} 条数据, 需要 {n_trials}", parent=self
                        )
                        return
                    data_flat.extend(subset[:n_trials])

            data_arr = np.array(data_flat, dtype=float)

            issues = validate_grr_data(n_parts, n_ops, n_trials, len(data_arr))
            if issues:
                for msg in issues:
                    InfoBar.warning("数据验证", msg, parent=self, duration=3000)

            result = calculate_grr(data_arr, n_parts, n_ops, n_trials)

            parent = self.parent()
            while parent and not isinstance(parent, GrrPanelWidget):
                parent = parent.parent()
            if isinstance(parent, GrrPanelWidget):
                parent.show_results(result, [str(p) for p in parts], [str(o) for o in operators])
                self.report_btn.setEnabled(True)

        except Exception as e:
            InfoBar.error("计算错误", str(e), parent=self)

    def _on_export_pdf(self) -> None:
        from q_caliper.reports.report_engine import generate_grr_report

        parent = self.parent()
        while parent and not isinstance(parent, GrrPanelWidget):
            parent = parent.parent()

        if not parent or parent.last_result is None:
            return

        path, _ = QFileDialog.getSaveFileName(self, "导出分析报告", "量具分析报告.pdf", "PDF 文件 (*.pdf)")
        if not path:
            return

        try:
            chart_paths = []
            for i, fig in enumerate(parent.charts.figures):
                tmp_img = str(Path(f"tmp_grr_chart_{i}.png").resolve())
                fig.savefig(tmp_img, dpi=120)
                chart_paths.append(tmp_img)

            generate_grr_report(path, parent.last_result, chart_paths)
            InfoBar.success("导出成功", f"报告已保存至: {path}", parent=self, duration=5000)
        except Exception as e:
            InfoBar.error("导出失败", f"PDF 生成过程中发生错误：\n{e!s}", parent=self, duration=-1)
        finally:
            for i in range(len(chart_paths)):
                Path(f"tmp_grr_chart_{i}.png").unlink(missing_ok=True)


class GrrChartsDashboard(QWidget):
    """6-chart GRR dashboard with key stats overlay."""

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
        self.grid_layout = QVBoxLayout(container)
        self.grid_layout.setSpacing(8)

        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        row3 = QHBoxLayout()

        self.fig1 = Figure(figsize=(5, 4), dpi=90)
        self.canvas1 = FigureCanvas(self.fig1)
        self.canvas1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas1.setMinimumHeight(280)
        row1.addWidget(self.canvas1)

        self.fig2 = Figure(figsize=(5, 4), dpi=90)
        self.canvas2 = FigureCanvas(self.fig2)
        self.canvas2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas2.setMinimumHeight(280)
        row1.addWidget(self.canvas2)

        self.fig3 = Figure(figsize=(5, 4), dpi=90)
        self.canvas3 = FigureCanvas(self.fig3)
        self.canvas3.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas3.setMinimumHeight(280)
        row2.addWidget(self.canvas3)

        self.fig4 = Figure(figsize=(5, 4), dpi=90)
        self.canvas4 = FigureCanvas(self.fig4)
        self.canvas4.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas4.setMinimumHeight(280)
        row2.addWidget(self.canvas4)

        self.fig5 = Figure(figsize=(5, 4), dpi=90)
        self.canvas5 = FigureCanvas(self.fig5)
        self.canvas5.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas5.setMinimumHeight(280)
        row3.addWidget(self.canvas5)

        self.fig6 = Figure(figsize=(5, 4), dpi=90)
        self.canvas6 = FigureCanvas(self.fig6)
        self.canvas6.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas6.setMinimumHeight(280)
        row3.addWidget(self.canvas6)

        self.grid_layout.addLayout(row1)
        self.grid_layout.addLayout(row2)
        self.grid_layout.addLayout(row3)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        self.figures = [self.fig1, self.fig2, self.fig3, self.fig4, self.fig5, self.fig6]

    def plot_all(self, result: GrrResult, part_names: list[str], operator_names: list[str]) -> None:
        arr = result.raw_data
        n_parts = result.n_parts
        n_ops = result.n_operators

        self._plot_by_part(self.fig1, self.canvas1, arr, n_parts, n_ops, part_names)
        self._plot_by_operator(self.fig2, self.canvas2, arr, n_parts, n_ops, operator_names)
        self._plot_operator_control(self.fig3, self.canvas3, result, operator_names)
        self._plot_part_control(self.fig4, self.canvas4, result, part_names)
        self._plot_interaction(self.fig5, self.canvas5, arr, n_parts, n_ops, part_names, operator_names)
        self._plot_variance_contribution(self.fig6, self.canvas6, result)

    def _plot_by_part(
        self,
        fig: Figure,
        canvas: FigureCanvas,
        arr: npt.NDArray[np.float64],
        n_parts: int,
        n_ops: int,
        part_names: list[str],
    ) -> None:
        fig.clear()
        ax = fig.add_subplot(111)
        part_data = [arr[i, :, :].flatten() for i in range(n_parts)]
        bp = ax.boxplot(part_data, patch_artist=True, labels=part_names[:n_parts])  # type: ignore
        colors = [
            "#4A90D9",
            "#50C878",
            "#FFB347",
            "#FF6B6B",
            "#9B59B6",
            "#1ABC9C",
            "#E74C3C",
            "#3498DB",
            "#F39C12",
            "#2ECC71",
        ]
        for i, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(colors[i % len(colors)])
            patch.set_alpha(0.7)
        ax.set_title("按零件分组", fontsize=11, fontweight="bold")
        ax.set_ylabel("测量值")
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis="x", rotation=45, labelsize=8)
        fig.tight_layout()
        canvas.draw()

    def _plot_by_operator(
        self,
        fig: Figure,
        canvas: FigureCanvas,
        arr: npt.NDArray[np.float64],
        n_parts: int,
        n_ops: int,
        operator_names: list[str],
    ) -> None:
        fig.clear()
        ax = fig.add_subplot(111)
        op_data = [arr[:, j, :].flatten() for j in range(n_ops)]
        bp = ax.boxplot(op_data, patch_artist=True, labels=operator_names[:n_ops])  # type: ignore
        colors = ["#4A90D9", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6"]
        for i, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(colors[i % len(colors)])
            patch.set_alpha(0.7)
        ax.set_title("按操作者分组", fontsize=11, fontweight="bold")
        ax.set_ylabel("测量值")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        canvas.draw()

    def _plot_operator_control(self, fig: Figure, canvas: FigureCanvas, result: GrrResult, operator_names: list[str]) -> None:
        fig.clear()
        ax = fig.add_subplot(111)
        means = result.operator_means
        x = range(len(means))
        ax.bar(x, means, color="#4A90D9", alpha=0.8, edgecolor="white")
        ax.axhline(
            result.grand_mean, color="#E74C3C", linestyle="--", linewidth=1.2, label=f"总均值={result.grand_mean:.3f}"
        )
        ax.set_title("操作者均值图", fontsize=11, fontweight="bold")
        ax.set_xticks(list(x))
        ax.set_xticklabels(operator_names[: len(means)], rotation=45, fontsize=8)
        ax.set_ylabel("均值")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis="y")
        fig.tight_layout()
        canvas.draw()

    def _plot_part_control(self, fig: Figure, canvas: FigureCanvas, result: GrrResult, part_names: list[str]) -> None:
        fig.clear()
        ax = fig.add_subplot(111)
        means = result.part_means
        x = range(len(means))
        ax.bar(x, means, color="#50C878", alpha=0.8, edgecolor="white")
        ax.axhline(
            result.grand_mean, color="#E74C3C", linestyle="--", linewidth=1.2, label=f"总均值={result.grand_mean:.3f}"
        )
        ax.set_title("零件均值图", fontsize=11, fontweight="bold")
        ax.set_xticks(list(x))
        ax.set_xticklabels(part_names[: len(means)], rotation=45, fontsize=7)
        ax.set_ylabel("均值")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis="y")
        fig.tight_layout()
        canvas.draw()

    def _plot_interaction(
        self,
        fig: Figure,
        canvas: FigureCanvas,
        arr: npt.NDArray[np.float64],
        n_parts: int,
        n_ops: int,
        part_names: list[str],
        operator_names: list[str],
    ) -> None:
        fig.clear()
        ax = fig.add_subplot(111)
        cell_means = np.mean(arr, axis=2)
        colors = ["#4A90D9", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6"]
        for j in range(n_ops):
            ax.plot(
                range(n_parts),
                cell_means[:, j],
                marker="o",
                color=colors[j % len(colors)],
                linewidth=1.2,
                markersize=6,
                label=operator_names[j],
            )
        ax.set_title("零件x操作者 交互图", fontsize=11, fontweight="bold")
        ax.set_xticks(range(n_parts))
        ax.set_xticklabels(part_names[:n_parts], rotation=45, fontsize=7)
        ax.set_ylabel("均值")
        ax.legend(fontsize=8, loc="best")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        canvas.draw()

    def _plot_variance_contribution(self, fig: Figure, canvas: FigureCanvas, result: GrrResult) -> None:
        fig.clear()
        gs = fig.add_gridspec(1, 2, width_ratios=[3, 1.8], wspace=0.15)
        ax = fig.add_subplot(gs[0])

        var_total = result.var_total if result.var_total > 0 else 1.0
        components = [
            ("重复性 (EV)", result.var_repeatability, "#4A90D9"),
            ("再现性 (AV)", result.var_reproducibility, "#E74C3C"),
            ("交互 (INT)", result.var_interaction, "#F39C12"),
            ("零件 (PV)", result.var_parts, "#50C878"),
        ]
        non_zero = [(name, val, color) for name, val, color in components if val > 0]

        if non_zero:
            names, vals, clrs = zip(*non_zero, strict=False)
            pcts = [v / var_total * 100 for v in vals]
            y_pos = range(len(names))
            bars = ax.barh(y_pos, pcts, color=clrs, alpha=0.85, edgecolor="white", height=0.6)
            ax.set_yticks(list(y_pos))
            ax.set_yticklabels(names, fontsize=9)
            for bar, pct in zip(bars, pcts, strict=False):
                ax.text(
                    bar.get_width() + 0.5,
                    bar.get_y() + bar.get_height() / 2,
                    f"{pct:.1f}%",
                    va="center",
                    fontsize=9,
                    fontweight="bold",
                )
            ax.set_xlim(0, max(pcts) * 1.2 if pcts else 100)
            ax.set_xlabel("贡献率 (%)", fontsize=9)
            ax.invert_yaxis()
        ax.set_title("方差分量贡献率", fontsize=11, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="x")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        pct_grr_grade = "<10% 可接受" if result.pct_grr < 10 else "<30% 可接受" if result.pct_grr < 30 else "不可接受"
        ndc_grade = ">=5 可接受" if result.ndc >= 5 else "<5 不可接受"

        ax_stats = fig.add_subplot(gs[1])
        ax_stats.axis("off")
        stats_text = (
            f"关键指标\n"
            f"%GRR:  {result.pct_grr:.2f}%  {pct_grr_grade}\n"
            f"%PV:   {result.pct_part_variation:.2f}%\n"
            f"ndc:   {result.ndc}  {ndc_grade}\n"
            f"\n"
            f"方差分量\n"
            f"重复性 (EV): {result.var_repeatability:.6f}\n"
            f"再现性 (AV): {result.var_reproducibility:.6f}\n"
            f"交互 (INT): {result.var_interaction:.6f}\n"
            f"零件 (PV):  {result.var_parts:.6f}\n"
            f"总变异:     {result.var_total:.6f}\n"
        )
        ax_stats.text(
            0, 1, stats_text, transform=ax_stats.transAxes, verticalalignment="top", fontsize=9, linespacing=1.6
        )

        fig.tight_layout()
        canvas.draw()


class GrrPanelWidget(QWidget):
    """量具分析 page with input card and 6-chart dashboard."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("grr_panel")
        self.df: pd.DataFrame | None = None
        self.last_result: GrrResult | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(15)

        header_row = QHBoxLayout()
        header = TitleLabel("量具分析")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_row.addWidget(header)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        desc = BodyLabel("基于 ANOVA 方法的 GRR 分析, 符合 IATF 16949 MSA 要求")
        desc.setStyleSheet("color: #666; margin-bottom: 2px;")
        main_layout.addWidget(desc)

        # 顶部参数区 (可折叠)
        self.input_card = GrrInputCard(self)
        main_layout.addWidget(self.input_card)

        # 底部图表区
        self.charts = GrrChartsDashboard(self)
        main_layout.addWidget(self.charts, 1)

    def set_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self.df = df
        self.input_card.set_dataframe(df)

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        self.input_card.set_selected_columns(mapping)

    def show_results(self, result: GrrResult, part_names: list[str], operator_names: list[str]) -> None:
        self.last_result = result
        self.charts.plot_all(result, part_names, operator_names)
