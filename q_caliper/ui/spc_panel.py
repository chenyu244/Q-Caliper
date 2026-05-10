"""SPC 统计过程控制 Panel — control charts, violation detection, capability trend."""

# isort: skip_file
from __future__ import annotations

import contextlib

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
    QLabel,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
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

from q_caliper.core.cpk import calculate_capability
from q_caliper.core.spc import SpcChartResult, xbar_r_chart, imr_chart


def _setup_matplotlib_font() -> None:
    """Configure matplotlib to use a CJK font for Chinese labels."""
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["axes.unicode_minus"] = False


_setup_matplotlib_font()

TABLE_STYLE = """
    QTableWidget {
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        background: white;
        alternate-background-color: #f8f9fa;
        font-size: 12px;
    }
    QHeaderView::section {
        background: #f0f2f5;
        border: none;
        border-bottom: 2px solid #0078D4;
        padding: 5px;
        font-weight: bold;
    }
"""


class SpcInputCard(CardWidget):
    """SPC parameter input card with collapsible support."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
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

        self.report_btn = PushButton("导出 PDF")
        self.report_btn.setIcon(FluentIcon.PRINT)
        self.report_btn.setFixedWidth(130)
        self.report_btn.setFixedHeight(28)
        self.report_btn.clicked.connect(self._on_export_pdf)
        self.report_btn.setEnabled(False)
        header_row.addWidget(self.report_btn)

        self.toggle_btn = PushButton("")
        self.toggle_btn.setIcon(FluentIcon.UP)
        self.toggle_btn.setFixedSize(28, 28)
        self.toggle_btn.setStyleSheet("PushButton { border: none; }")
        self.toggle_btn.setToolTip("折叠/展开参数区")
        self.toggle_btn.clicked.connect(self._toggle_collapse)
        header_row.addWidget(self.toggle_btn)

        self.main_layout.addLayout(header_row)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 8, 0, 0)
        content_layout.setSpacing(0)

        form = QFormLayout()
        form.setSpacing(8)

        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["XBar-R 控制图", "I-MR 控制图"])
        self.chart_type_combo.currentIndexChanged.connect(self._on_chart_type_changed)
        form.addRow("图表类型:", self.chart_type_combo)

        self.measure_combo = QComboBox()
        self.measure_combo.setPlaceholderText("-- 测量数据列 --")
        self.measure_combo.setMinimumWidth(180)
        self.measure_combo.setFixedHeight(32)
        form.addRow("测量列:", self.measure_combo)

        self.subgroup_spin = QSpinBox()
        self.subgroup_spin.setRange(2, 10)
        self.subgroup_spin.setValue(5)
        self.subgroup_spin.setFixedHeight(32)
        self.subgroup_spin.setToolTip("XBar-R 图的子组大小 (2-10)")
        form.addRow("子组大小:", self.subgroup_spin)

        spec_lbl_row = QHBoxLayout()
        spec_lbl_row.setContentsMargins(0, 0, 0, 0)
        spec_lbl_row.addWidget(QLabel("规格限 (LSL / USL):"))
        self.magic_btn = PushButton("智能推荐")
        self.magic_btn.setFixedHeight(22)
        self.magic_btn.setStyleSheet("font-size: 11px; padding: 0 5px;")
        self.magic_btn.clicked.connect(self._show_spec_menu)
        spec_lbl_row.addWidget(self.magic_btn)
        spec_lbl_row.addStretch()
        form.addRow(spec_lbl_row)

        spec_input_row = QHBoxLayout()
        spec_input_row.setContentsMargins(0, 0, 0, 0)
        self.lsl_spin = QDoubleSpinBox()
        self.lsl_spin.setRange(-1e12, 1e12)
        self.lsl_spin.setDecimals(4)
        self.lsl_spin.setSpecialValueText("无")
        self.lsl_spin.setValue(-1e12)
        self.lsl_spin.setFixedHeight(32)
        spec_input_row.addWidget(self.lsl_spin)
        self.usl_spin = QDoubleSpinBox()
        self.usl_spin.setRange(-1e12, 1e12)
        self.usl_spin.setDecimals(4)
        self.usl_spin.setSpecialValueText("无")
        self.usl_spin.setValue(-1e12)
        self.usl_spin.setFixedHeight(32)
        spec_input_row.addWidget(self.usl_spin)
        form.addRow(spec_input_row)

        content_layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 8, 0, 0)
        self.calc_btn = PrimaryPushButton("生成控制图")
        self.calc_btn.setIcon(FluentIcon.PLAY)
        self.calc_btn.setFixedHeight(32)
        self.calc_btn.clicked.connect(self._on_calculate)
        btn_row.addWidget(self.calc_btn)
        btn_row.addStretch()
        content_layout.addLayout(btn_row)

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

    def _on_chart_type_changed(self, index: int) -> None:
        pass

    def _show_spec_menu(self) -> None:
        from qfluentwidgets import RoundMenu, Action
        if self.df is None:
            return

        col = self.measure_combo.currentText()
        if not col:
            return

        data = self.df[col].dropna().values
        if len(data) == 0:
            return

        mean = np.mean(data)
        std = np.std(data, ddof=1)

        menu = RoundMenu(parent=self.magic_btn)

        actions = [
            ("\u00b13 Sigma (99.7%)", mean + 3 * std, mean - 3 * std),
            ("\u00b16 Sigma (\u7cbe\u5bc6)", mean + 6 * std, mean - 6 * std),
            ("\u5168\u8303\u56f4 (Max/Min)", np.max(data), np.min(data)),
            ("\u91cd\u7f6e\u89c4\u683c", -1e12, -1e12),
        ]

        for text, usl, lsl in actions:
            act = Action(text, self)
            act.triggered.connect(lambda checked, u=usl, low=lsl, t=text: self._apply_spec(u, low, t))
            menu.addAction(act)

        menu.exec(self.magic_btn.mapToGlobal(self.magic_btn.rect().bottomLeft()))

    def _apply_spec(self, usl: float, lsl: float, text: str = "\u667a\u80fd\u63a8\u8350") -> None:
        self.usl_spin.setValue(usl)
        self.lsl_spin.setValue(lsl)
        self.magic_btn.setText(text)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df
        self.measure_combo.clear()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.measure_combo.addItems([str(c) for c in numeric_cols])

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        """Pre-select columns based on roles from Data Center."""
        if mapping.get("测量值"):
            col = mapping["测量值"][0]
            idx = self.measure_combo.findText(col)
            if idx >= 0:
                self.measure_combo.setCurrentIndex(idx)

    def _on_calculate(self) -> None:
        if self.df is None:
            InfoBar.warning("提示", "请先在数据中心加载数据文件", parent=self)
            return

        col = self.measure_combo.currentText()
        if not col:
            InfoBar.warning("提示", "请选择测量数据列", parent=self)
            return

        data = self.df[col].dropna().values
        if len(data) < 10:
            InfoBar.warning("数据不足", "至少需要 10 个有效数据点", parent=self)
            return

        chart_type = self.chart_type_combo.currentIndex()
        sg_size = self.subgroup_spin.value()

        try:
            if chart_type == 0:
                chart1, chart2 = xbar_r_chart(data, subgroup_size=sg_size)
                chart1_name = "XBar (均值图)"
                chart2_name = "R (极差图)"
            else:
                chart1, chart2 = imr_chart(data)
                chart1_name = "I (个体值图)"
                chart2_name = "MR (移动极差图)"

            usl_val = self.usl_spin.value()
            lsl_val = self.lsl_spin.value()
            usl = None if usl_val <= -1e11 else usl_val
            lsl = None if lsl_val <= -1e11 else lsl_val

            cpk_result = None
            if usl is not None or lsl is not None:
                with contextlib.suppress(Exception):
                    cpk_result = calculate_capability(data, usl, lsl, sg_size if chart_type == 0 else 1)

            parent_widget = self.parent()
            while parent_widget and not isinstance(parent_widget, SpcPanelWidget):
                parent_widget = parent_widget.parent()
            if isinstance(parent_widget, SpcPanelWidget):
                parent_widget.show_results(chart1, chart2, chart1_name, chart2_name, cpk_result, col)
                self.report_btn.setEnabled(True)

        except Exception as e:
            InfoBar.error("计算错误", str(e), parent=self)

    def _on_export_pdf(self) -> None:
        from q_caliper.reports.report_engine import generate_spc_report

        parent = self.parent()
        while parent and not isinstance(parent, SpcPanelWidget):
            parent = parent.parent()

        if not parent:
            return

        path, _ = QFileDialog.getSaveFileName(self, "导出分析报告", "SPC分析报告.pdf", "PDF 文件 (*.pdf)")
        if not path:
            return

        try:
            chart_paths = []
            figs = [parent.chart1_widget.figure, parent.chart2_widget.figure]
            if parent.trend_card.figure is not None:
                figs.append(parent.trend_card.figure)
            for i, fig in enumerate(figs):
                tmp_img = str(Path(f"tmp_spc_chart_{i}.png").resolve())
                fig.savefig(tmp_img, dpi=120)
                chart_paths.append(tmp_img)

            generate_spc_report(
                path,
                chart1=parent.last_chart1,
                chart2=parent.last_chart2,
                chart1_name=parent.last_chart1_name,
                chart2_name=parent.last_chart2_name,
                cpk_result=parent.last_cpk_result,
                chart_paths=chart_paths,
                col_name=parent.last_col_name,
                chart_type_name=parent.input_card.chart_type_combo.currentText(),
                subgroup_size=parent.input_card.subgroup_spin.value(),
                data_length=parent.last_data_length,
            )
            InfoBar.success("导出成功", f"报告已保存至: {path}", parent=self, duration=5000)
        except Exception as e:
            InfoBar.error("导出失败", f"PDF 生成过程中发生错误：\n{e!s}", parent=self, duration=-1)
        finally:
            for p in chart_paths:
                Path(p).unlink(missing_ok=True)


class ControlChartWidget(CardWidget):
    """Single control chart canvas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.figure = Figure(figsize=(6, 4), dpi=90)
        self.figure.set_facecolor("white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setMinimumHeight(280)
        layout.addWidget(self.canvas)

    def plot(self, chart: SpcChartResult, title: str) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        x = list(range(1, len(chart.values) + 1))
        ax.plot(x, chart.values, "o-", color="#4A90D9", markersize=5, linewidth=1.0, label="数据点", zorder=3)

        ax.axhline(chart.limits.ucl, color="#E74C3C", linestyle="--", linewidth=1.2, label=f"UCL={chart.limits.ucl:.3f}")
        ax.axhline(chart.limits.cl, color="#2ECC71", linestyle="-", linewidth=1.2, label=f"CL={chart.limits.cl:.3f}")
        ax.axhline(chart.limits.lcl, color="#E74C3C", linestyle="--", linewidth=1.2, label=f"LCL={chart.limits.lcl:.3f}")

        ucl = chart.limits.ucl
        cl = chart.limits.cl
        lcl = chart.limits.lcl
        sigma = (ucl - cl) / 3 if (ucl - cl) > 0 else 0
        if sigma > 0:
            ax.axhspan(cl + 2 * sigma, ucl, alpha=0.05, color="#E74C3C")
            ax.axhspan(lcl, cl - 2 * sigma, alpha=0.05, color="#E74C3C")
            ax.axhspan(cl + sigma, cl + 2 * sigma, alpha=0.03, color="#F39C12")
            ax.axhspan(cl - 2 * sigma, cl - sigma, alpha=0.03, color="#F39C12")

        if chart.violations:
            vx = [v.index + 1 for v in chart.violations]
            vy = [chart.values[v.index] for v in chart.violations]
            ax.scatter(vx, vy, color="#E74C3C", s=80, zorder=5, marker="x", linewidths=2, label="违规点")

        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.set_xlabel("子组编号", fontsize=10)
        ax.set_ylabel("值", fontsize=10)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        self.figure.tight_layout()
        self.canvas.draw()


class ViolationsTable(CardWidget):
    """Violation detection results table."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        self.header_label = StrongBodyLabel("判异规则检测结果")
        self.header_label.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(self.header_label)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["图表", "规则", "位置", "描述"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(TABLE_STYLE)
        layout.addWidget(self.table)

    def show_violations(self, chart1: SpcChartResult, chart1_name: str, chart2: SpcChartResult, chart2_name: str) -> None:
        all_v = []
        for v in chart1.violations:
            all_v.append((chart1_name, v.rule, f"第 {v.index + 1} 点", v.description))
        for v in chart2.violations:
            all_v.append((chart2_name, v.rule, f"第 {v.index + 1} 点", v.description))

        self.header_label.setText(f"判异规则检测结果 (共 {len(all_v)} 项违规)")

        if not all_v:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("-"))
            self.table.setItem(0, 1, QTableWidgetItem("-"))
            self.table.setItem(0, 2, QTableWidgetItem("-"))
            self.table.setItem(0, 3, QTableWidgetItem("未检测到违规, 过程受控"))
            return

        self.table.setRowCount(len(all_v))
        for i, (chart, rule, pos, desc) in enumerate(all_v):
            self.table.setItem(i, 0, QTableWidgetItem(chart))
            self.table.setItem(i, 1, QTableWidgetItem(rule))
            self.table.setItem(i, 2, QTableWidgetItem(pos))
            self.table.setItem(i, 3, QTableWidgetItem(desc))

        self.table.resizeRowsToContents()

    def get_violations_data(self) -> list[tuple[str, str, str, str]]:
        """Return violations as list of (chart, rule, position, description)."""
        result = []
        for row in range(self.table.rowCount()):
            items = [self.table.item(row, c) for c in range(4)]
            if all(item is not None for item in items):
                result.append(tuple(item.text() for item in items))
        return result


class CpkTrendCard(CardWidget):
    """Cpk trend analysis chart."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        header = StrongBodyLabel("过程能力趋势")
        header.setStyleSheet("font-size: 14px; margin-bottom: 4px;")
        layout.addWidget(header)

        self.figure = Figure(figsize=(6, 3), dpi=90)
        self.figure.set_facecolor("white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setMinimumHeight(200)
        layout.addWidget(self.canvas)

    def plot_trend(self, data: np.ndarray, usl: float | None, lsl: float | None, n_segments: int = 5, sg_size: int = 1) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        n = len(data)
        if n < 20 or (usl is None and lsl is None):
            ax.text(0.5, 0.5, "数据不足或未设置规格限", ha="center", va="center", fontsize=12, color="#999", transform=ax.transAxes)
            self.figure.tight_layout()
            self.canvas.draw()
            return

        segment_size = n // n_segments
        cpk_values = []
        labels = []

        for i in range(n_segments):
            start = i * segment_size
            end = start + segment_size if i < n_segments - 1 else n
            seg_data = data[start:end]
            try:
                result = calculate_capability(seg_data, usl, lsl, sg_size)
                cpk_values.append(result.cpk)
            except Exception:
                cpk_values.append(0.0)
            labels.append(f"{start + 1}-{end}")

        x = range(len(cpk_values))
        colors = ["#27AE60" if v >= 1.33 else "#E67E22" if v >= 1.0 else "#E74C3C" for v in cpk_values]
        bars = ax.bar(x, cpk_values, color=colors, alpha=0.8, edgecolor="white", width=0.6)

        ax.axhline(1.33, color="#27AE60", linestyle="--", linewidth=1, alpha=0.7, label="Cpk=1.33")
        ax.axhline(1.0, color="#E67E22", linestyle="--", linewidth=1, alpha=0.7, label="Cpk=1.0")

        for bar, val in zip(bars, cpk_values, strict=False):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, f"{val:.2f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_xlabel("数据段 (样本编号范围)", fontsize=9)
        ax.set_ylabel("Cpk", fontsize=9)
        ax.set_title("Cpk 趋势", fontsize=11, fontweight="bold")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True, alpha=0.3, axis="y")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        self.figure.tight_layout()
        self.canvas.draw()


class SpcPanelWidget(QWidget):
    """SPC analysis page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("spc_panel")
        self.df: pd.DataFrame | None = None
        self.last_chart1 = None
        self.last_chart2 = None
        self.last_chart1_name = ""
        self.last_chart2_name = ""
        self.last_cpk_result = None
        self.last_col_name = ""
        self.last_data_length = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(15)

        header_row = QHBoxLayout()
        header = TitleLabel("统计过程控制 (SPC)")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_row.addWidget(header)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        desc = BodyLabel("XBar-R / I-MR 控制图, 八大判异准则自动检测, 过程能力趋势分析")
        desc.setStyleSheet("color: #666; margin-bottom: 2px;")
        main_layout.addWidget(desc)

        self.input_card = SpcInputCard(self)
        main_layout.addWidget(self.input_card)

        charts_scroll = QScrollArea()
        charts_scroll.setWidgetResizable(True)
        charts_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        charts_container = QWidget()
        charts_layout = QVBoxLayout(charts_container)
        charts_layout.setSpacing(8)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(12)
        self.chart1_widget = ControlChartWidget(self)
        self.chart2_widget = ControlChartWidget(self)
        chart_row.addWidget(self.chart1_widget)
        chart_row.addWidget(self.chart2_widget)
        charts_layout.addLayout(chart_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        self.violations_table = ViolationsTable(self)
        bottom_row.addWidget(self.violations_table, 1)
        self.trend_card = CpkTrendCard(self)
        bottom_row.addWidget(self.trend_card, 1)
        charts_layout.addLayout(bottom_row)

        charts_scroll.setWidget(charts_container)
        main_layout.addWidget(charts_scroll, 1)

    def set_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self.df = df
        self.input_card.set_dataframe(df)

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        self.input_card.set_selected_columns(mapping)

    def show_results(self, chart1, chart2, chart1_name, chart2_name, cpk_result, col_name) -> None:
        self.last_chart1 = chart1
        self.last_chart2 = chart2
        self.last_chart1_name = chart1_name
        self.last_chart2_name = chart2_name
        self.last_cpk_result = cpk_result
        self.last_col_name = col_name

        self.chart1_widget.plot(chart1, f"{col_name} - {chart1_name}")
        self.chart2_widget.plot(chart2, f"{col_name} - {chart2_name}")
        self.violations_table.show_violations(chart1, chart1_name, chart2, chart2_name)

        data = self.df[col_name].dropna().values if self.df is not None else None
        self.last_data_length = len(data) if data is not None else 0
        usl = cpk_result.usl if cpk_result else None
        lsl = cpk_result.lsl if cpk_result else None
        if data is not None:
            chart_type = self.input_card.chart_type_combo.currentIndex()
            sg = self.input_card.subgroup_spin.value() if chart_type == 0 else 1
            self.trend_card.plot_trend(data, usl, lsl, n_segments=5, sg_size=sg)
