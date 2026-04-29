"""Cpk Analysis Panel — column mapping, calculation, and histogram."""

# isort: skip_file
from __future__ import annotations

import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
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

from q_caliper.core.cpk import calculate_cpk, normality_test


def _setup_matplotlib_font() -> None:
    """Configure matplotlib to use a CJK font for Chinese labels."""
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


class ColumnMappingCard(CardWidget):
    """Column mapping: select measurement column, USL, LSL, subgroup."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("列映射")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(8)

        self.measure_combo = QComboBox()
        self.measure_combo.setMinimumWidth(180)
        self.measure_combo.setPlaceholderText("-- 选择测量数据列 --")
        form.addRow("测量列:", self.measure_combo)

        spec_row = QHBoxLayout()
        self.usl_spin = QDoubleSpinBox()
        self.usl_spin.setRange(-1e12, 1e12)
        self.usl_spin.setDecimals(4)
        self.usl_spin.setSpecialValueText("无")
        self.usl_spin.setValue(-1e12)
        spec_row.addWidget(QLabel("USL:"))
        spec_row.addWidget(self.usl_spin)

        self.lsl_spin = QDoubleSpinBox()
        self.lsl_spin.setRange(-1e12, 1e12)
        self.lsl_spin.setDecimals(4)
        self.lsl_spin.setSpecialValueText("无")
        self.lsl_spin.setValue(-1e12)
        spec_row.addWidget(QLabel("LSL:"))
        spec_row.addWidget(self.lsl_spin)
        form.addRow("规格限:", spec_row)

        self.subgroup_spin = QDoubleSpinBox()
        self.subgroup_spin.setRange(1, 100)
        self.subgroup_spin.setDecimals(0)
        self.subgroup_spin.setValue(1)
        form.addRow("子组大小:", self.subgroup_spin)

        layout.addLayout(form)

        self.calc_btn = PrimaryPushButton("计算 Cpk")
        self.calc_btn.setIcon(FluentIcon.PLAY)
        self.calc_btn.setFixedHeight(36)
        self.calc_btn.clicked.connect(self._on_calculate)
        layout.addWidget(self.calc_btn)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df
        self.measure_combo.clear()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.measure_combo.addItems([str(c) for c in numeric_cols])

    def _on_calculate(self) -> None:
        if self.df is None:
            InfoBar.warning("提示", "请先加载数据文件", parent=self)
            return

        col = self.measure_combo.currentText()
        if not col:
            InfoBar.warning("提示", "请选择测量数据列", parent=self)
            return

        data = self.df[col].dropna().values
        if len(data) < 8:
            InfoBar.warning("数据不足", "至少需要 8 个有效数据点", parent=self)
            return

        usl = self.usl_spin.value()
        lsl = self.lsl_spin.value()
        usl_val = None if usl <= -1e11 else usl
        lsl_val = None if lsl <= -1e11 else lsl

        if usl_val is None and lsl_val is None:
            InfoBar.warning("提示", "请至少设置一个规格限 (USL 或 LSL)", parent=self)
            return

        sg_size = int(self.subgroup_spin.value())

        try:
            norm_result = normality_test(data)
            cpk_result = calculate_cpk(data, usl_val, lsl_val, sg_size)
        except Exception as e:
            InfoBar.error("计算错误", str(e), parent=self)
            return

        parent = self.parent()
        while parent and not isinstance(parent, CpkPanelWidget):
            parent = parent.parent()
        if isinstance(parent, CpkPanelWidget):
            parent.show_results(data, norm_result, cpk_result, col)


class ResultsTable(CardWidget):
    """Display Cpk/Ppk results in a styled table."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        header = StrongBodyLabel("分析结果")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["指标", "值"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
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
        """)
        layout.addWidget(self.table)

    def show_results(self, norm_result, cpk_result) -> None:
        rows = [
            ("均值 (Mean)", f"{cpk_result.mean:.4f}"),
            ("组内标准差 (sigma_within)", f"{cpk_result.std_within:.4f}"),
            ("总体标准差 (sigma_overall)", f"{cpk_result.std_overall:.4f}"),
            ("Cp", f"{cpk_result.cp:.4f}"),
            ("Cpk", f"{cpk_result.cpk:.4f}"),
            ("Pp", f"{cpk_result.pp:.4f}"),
            ("Ppk", f"{cpk_result.ppk:.4f}"),
            ("USL", f"{cpk_result.usl}" if cpk_result.usl else "未设置"),
            ("LSL", f"{cpk_result.lsl}" if cpk_result.lsl else "未设置"),
            ("超 USL 比例", f"{cpk_result.pct_above_usl:.4%}"),
            ("低于 LSL 比例", f"{cpk_result.pct_below_lsl:.4%}"),
            ("总超规格比例", f"{cpk_result.pct_total_out:.4%}"),
            ("---", "---"),
            ("正态性检验", norm_result.test_name),
            ("检验统计量", f"{norm_result.statistic:.4f}"),
            ("p 值", f"{norm_result.p_value:.4f}"),
            ("正态性结论", "正态分布" if norm_result.is_normal else "非正态分布"),
        ]

        self.table.setRowCount(len(rows))
        for i, (name, val) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(str(val)))

        self.table.resizeRowsToContents()


class HistogramWidget(CardWidget):
    """Histogram with normal fit curve and spec limits."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.figure.set_facecolor("white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas)

    def plot(self, data: np.ndarray, cpk_result, col_name: str) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        n_bins = min(50, max(10, len(data) // 5))
        ax.hist(data, bins=n_bins, density=True, alpha=0.7, color="#4A90D9", edgecolor="white", linewidth=0.5, label="数据分布")

        xmin, xmax = ax.get_xlim()
        x = np.linspace(min(data.min(), xmin), max(data.max(), xmax), 300)
        mean = cpk_result.mean
        std = cpk_result.std_overall
        if std > 0:
            y = (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)
            ax.plot(x, y, "r-", linewidth=2, label="正态拟合曲线")

        if cpk_result.usl is not None:
            ax.axvline(cpk_result.usl, color="#E74C3C", linestyle="--", linewidth=2, label=f"USL = {cpk_result.usl}")
        if cpk_result.lsl is not None:
            ax.axvline(cpk_result.lsl, color="#E74C3C", linestyle="--", linewidth=2, label=f"LSL = {cpk_result.lsl}")

        ax.axvline(mean, color="#2ECC71", linestyle="-", linewidth=1.5, label=f"均值 = {mean:.3f}")

        cpk_val = cpk_result.cpk
        color = "#27AE60" if cpk_val >= 1.33 else "#E67E22" if cpk_val >= 1.0 else "#E74C3C"
        ax.text(
            0.02, 0.95, f"Cpk = {cpk_val:.3f}",
            transform=ax.transAxes, fontsize=14, fontweight="bold",
            color="white", backgroundcolor=color, verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=color, alpha=0.9),
        )

        ax.set_xlabel(col_name, fontsize=11)
        ax.set_ylabel("密度", fontsize=11)
        ax.set_title(f"{col_name} 直方图", fontsize=13, fontweight="bold")
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        self.figure.tight_layout()
        self.canvas.draw()


class CpkPanelWidget(QWidget):
    """Cpk analysis page with column mapping, results, and histogram."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cpk_panel")
        self.df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)

        header = TitleLabel("Cpk 过程能力分析")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        main_layout.addWidget(header)

        desc = BodyLabel("选择测量数据列和规格限, 计算 Cpk/Ppk 并生成直方图")
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        main_layout.addWidget(desc)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.mapping_card = ColumnMappingCard(self)
        left_layout.addWidget(self.mapping_card)
        self.results_table = ResultsTable(self)
        left_layout.addWidget(self.results_table, 1)

        self.histogram = HistogramWidget(self)

        splitter.addWidget(left_panel)
        splitter.addWidget(self.histogram)
        splitter.setSizes([380, 520])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, 1)

    def set_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self.df = df
        self.mapping_card.set_dataframe(df)

    def show_results(self, data, norm_result, cpk_result, col_name: str) -> None:
        self.results_table.show_results(norm_result, cpk_result)
        self.histogram.plot(data, cpk_result, col_name)
