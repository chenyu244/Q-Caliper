"""SPC Panel — control charts, violation detection, capability trend."""

# isort: skip_file
from __future__ import annotations

import contextlib

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QSpinBox,
    QSplitter,
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
    StrongBodyLabel,
    TitleLabel,
)

from q_caliper.core.cpk import calculate_capability
from q_caliper.core.spc import SpcChartResult, xbar_r_chart, imr_chart


def _setup_matplotlib_font() -> None:
    candidates = [
        "Microsoft YaHei", "SimHei", "SimSun", "NSimSun",
        "FangSong", "KaiTi", "Microsoft JhengHei",
        "WenQuanYi Micro Hei", "Noto Sans CJK SC",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            matplotlib.rcParams["font.sans-serif"] = [name]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return


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
    """SPC parameter input card."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("SPC 参数设置")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(8)

        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["XBar-R 控制图", "I-MR 控制图"])
        self.chart_type_combo.currentIndexChanged.connect(self._on_chart_type_changed)
        form.addRow("图表类型:", self.chart_type_combo)

        self.measure_combo = QComboBox()
        self.measure_combo.setPlaceholderText("-- 测量数据列 --")
        form.addRow("测量列:", self.measure_combo)

        self.subgroup_spin = QSpinBox()
        self.subgroup_spin.setRange(2, 10)
        self.subgroup_spin.setValue(5)
        self.subgroup_spin.setToolTip("XBar-R 图的子组大小 (2-10)")
        form.addRow("子组大小:", self.subgroup_spin)

        self.usl_combo = QComboBox()
        self.usl_combo.setPlaceholderText("-- 可选 --")
        self.usl_combo.setEditable(True)
        self.usl_combo.setCurrentText("")
        form.addRow("USL (可选):", self.usl_combo)

        self.lsl_combo = QComboBox()
        self.lsl_combo.setPlaceholderText("-- 可选 --")
        self.lsl_combo.setEditable(True)
        self.lsl_combo.setCurrentText("")
        form.addRow("LSL (可选):", self.lsl_combo)

        layout.addLayout(form)

        btn_row = QHBoxLayout()

        self.calc_btn = PrimaryPushButton("生成控制图")
        self.calc_btn.setIcon(FluentIcon.PLAY)
        self.calc_btn.setFixedHeight(36)
        self.calc_btn.clicked.connect(self._on_calculate)
        btn_row.addWidget(self.calc_btn)

        layout.addLayout(btn_row)

    def _on_chart_type_changed(self, index: int) -> None:
        self.subgroup_spin.setEnabled(index == 0)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df
        self.measure_combo.clear()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.measure_combo.addItems([str(c) for c in numeric_cols])
        self.usl_combo.clear()
        self.usl_combo.addItems([""] + [str(c) for c in numeric_cols])
        self.lsl_combo.clear()
        self.lsl_combo.addItems([""] + [str(c) for c in numeric_cols])

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

            usl_text = self.usl_combo.currentText().strip()
            lsl_text = self.lsl_combo.currentText().strip()

            usl_val = None
            lsl_val = None
            if usl_text:
                try:
                    usl_val = float(usl_text)
                except ValueError:
                    if usl_text in self.df.columns:
                        usl_val = float(self.df[usl_text].dropna().mean())
            if lsl_text:
                try:
                    lsl_val = float(lsl_text)
                except ValueError:
                    if lsl_text in self.df.columns:
                        lsl_val = float(self.df[lsl_text].dropna().mean())

            cpk_result = None
            if usl_val is not None or lsl_val is not None:
                with contextlib.suppress(Exception):
                    cpk_result = calculate_capability(data, usl_val, lsl_val, sg_size if chart_type == 0 else 1)

            parent_widget = self.parent()
            while parent_widget and not isinstance(parent_widget, SpcPanelWidget):
                parent_widget = parent_widget.parent()
            if isinstance(parent_widget, SpcPanelWidget):
                parent_widget.show_results(chart1, chart2, chart1_name, chart2_name, cpk_result, col)

        except Exception as e:
            InfoBar.error("计算错误", str(e), parent=self)


class ControlChartWidget(CardWidget):
    """Single control chart canvas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.figure = Figure(figsize=(6, 3.5), dpi=100)
        self.figure.set_facecolor("white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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


class CpkTrendCard(CardWidget):
    """Cpk trend analysis chart."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        header = StrongBodyLabel("过程能力趋势")
        header.setStyleSheet("font-size: 14px; margin-bottom: 4px;")
        layout.addWidget(header)

        self.figure = Figure(figsize=(6, 2.5), dpi=100)
        self.figure.set_facecolor("white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)

        header = TitleLabel("SPC 统计过程控制")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        main_layout.addWidget(header)

        desc = BodyLabel("XBar-R / I-MR 控制图, 自动检测八大判异准则, 过程能力趋势分析")
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        main_layout.addWidget(desc)

        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.input_card = SpcInputCard(self)
        top_splitter.addWidget(self.input_card)

        self.violations_table = ViolationsTable(self)
        top_splitter.addWidget(self.violations_table)

        top_splitter.setSizes([300, 600])

        charts_container = QWidget()
        charts_layout = QVBoxLayout(charts_container)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        charts_layout.setSpacing(8)

        chart_row = QHBoxLayout()
        self.chart1_widget = ControlChartWidget(self)
        self.chart2_widget = ControlChartWidget(self)
        chart_row.addWidget(self.chart1_widget)
        chart_row.addWidget(self.chart2_widget)
        charts_layout.addLayout(chart_row)

        self.trend_card = CpkTrendCard(self)
        charts_layout.addWidget(self.trend_card)

        main_layout.addWidget(top_splitter, 1)
        main_layout.addWidget(charts_container, 2)

    def set_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self.df = df
        self.input_card.set_dataframe(df)

    def show_results(self, chart1, chart2, chart1_name, chart2_name, cpk_result, col_name) -> None:
        self.chart1_widget.plot(chart1, f"{col_name} - {chart1_name}")
        self.chart2_widget.plot(chart2, f"{col_name} - {chart2_name}")
        self.violations_table.show_violations(chart1, chart1_name, chart2, chart2_name)

        data = self.df[col_name].dropna().values if self.df is not None else None
        usl = cpk_result.usl if cpk_result else None
        lsl = cpk_result.lsl if cpk_result else None
        if data is not None:
            chart_type = self.input_card.chart_type_combo.currentIndex()
            sg = self.input_card.subgroup_spin.value() if chart_type == 0 else 1
            self.trend_card.plot_trend(data, usl, lsl, n_segments=5, sg_size=sg)
