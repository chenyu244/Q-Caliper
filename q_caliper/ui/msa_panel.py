"""MSA Panel — bias and linearity analysis."""

# isort: skip_file
from __future__ import annotations

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
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

from q_caliper.core.msa import analyze_bias, analyze_linearity


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


class BiasInputCard(CardWidget):
    """Bias analysis input."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("偏差分析设置")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(8)

        self.measure_combo = QComboBox()
        self.measure_combo.setPlaceholderText("-- 测量数据列 --")
        form.addRow("测量列:", self.measure_combo)

        self.ref_spin = QDoubleSpinBox()
        self.ref_spin.setRange(-1e12, 1e12)
        self.ref_spin.setDecimals(4)
        self.ref_spin.setValue(0.0)
        form.addRow("参考值:", self.ref_spin)

        layout.addLayout(form)

        self.calc_btn = PrimaryPushButton("分析偏差")
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
            InfoBar.warning("提示", "请先在数据中心加载数据文件", parent=self)
            return

        col = self.measure_combo.currentText()
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
            while parent and not isinstance(parent, MsaPanelWidget):
                parent = parent.parent()
            if isinstance(parent, MsaPanelWidget):
                parent.show_bias_results(data, result, col)
        except Exception as e:
            InfoBar.error("计算错误", str(e), parent=self)


class LinearInputCard(CardWidget):
    """Linearity analysis input."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("线性分析设置")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(8)

        self.ref_combo = QComboBox()
        self.ref_combo.setPlaceholderText("-- 参考值列 --")
        form.addRow("参考值列:", self.ref_combo)

        self.measure_combo = QComboBox()
        self.measure_combo.setPlaceholderText("-- 测量均值列 --")
        form.addRow("测量均值列:", self.measure_combo)

        self.pv_spin = QDoubleSpinBox()
        self.pv_spin.setRange(0.001, 1e12)
        self.pv_spin.setDecimals(4)
        self.pv_spin.setValue(1.0)
        self.pv_spin.setSpecialValueText("过程变异 (6s)")
        form.addRow("过程变异:", self.pv_spin)

        layout.addLayout(form)

        self.calc_btn = PrimaryPushButton("分析线性")
        self.calc_btn.setIcon(FluentIcon.PLAY)
        self.calc_btn.setFixedHeight(36)
        self.calc_btn.clicked.connect(self._on_calculate)
        layout.addWidget(self.calc_btn)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df
        self.ref_combo.clear()
        self.measure_combo.clear()
        cols = [str(c) for c in df.columns]
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.ref_combo.addItems(cols)
        self.measure_combo.addItems([str(c) for c in numeric_cols])

    def _on_calculate(self) -> None:
        if self.df is None:
            InfoBar.warning("提示", "请先在数据中心加载数据文件", parent=self)
            return

        ref_col = self.ref_combo.currentText()
        meas_col = self.measure_combo.currentText()
        if not all([ref_col, meas_col]):
            InfoBar.warning("提示", "请选择所有必要的列", parent=self)
            return

        try:
            df = self.df.dropna(subset=[ref_col, meas_col])
            df[ref_col] = pd.to_numeric(df[ref_col], errors="coerce")
            df[meas_col] = pd.to_numeric(df[meas_col], errors="coerce")
            df = df.dropna()

            refs = df[ref_col].values
            means = df[meas_col].values

            unique_refs = sorted(np.unique(refs))
            if len(unique_refs) < 3:
                InfoBar.warning("数据不足", "至少需要 3 个不同的参考值", parent=self)
                return

            avg_means = np.array([means[refs == r].mean() for r in unique_refs])
            pv = self.pv_spin.value()

            result = analyze_linearity(unique_refs, avg_means, pv)

            parent = self.parent()
            while parent and not isinstance(parent, MsaPanelWidget):
                parent = parent.parent()
            if isinstance(parent, MsaPanelWidget):
                parent.show_linear_results(result)
        except Exception as e:
            InfoBar.error("计算错误", str(e), parent=self)


class BiasResultsTable(CardWidget):
    """Bias analysis results."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        header = StrongBodyLabel("偏差分析结果")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["指标", "值"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(TABLE_STYLE)
        layout.addWidget(self.table)

    def show_results(self, result) -> None:
        sig = "显著" if result.is_significant else "不显著"
        rows = [
            ("观测均值", f"{result.observed_mean:.4f}"),
            ("参考值", f"{result.reference_value:.4f}"),
            ("偏差 (Bias)", f"{result.mean_bias:.4f}"),
            ("偏差百分比", f"{result.pct_bias:.2f}%"),
            ("t 统计量", f"{result.t_statistic:.4f}"),
            ("p 值", f"{result.p_value:.4f}"),
            ("95% CI 下限", f"{result.ci_lower:.4f}"),
            ("95% CI 上限", f"{result.ci_upper:.4f}"),
            ("显著性", sig),
        ]
        self.table.setRowCount(len(rows))
        for i, (name, val) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(str(val)))
        self.table.resizeRowsToContents()


class LinearResultsTable(CardWidget):
    """Linearity analysis results."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        header = StrongBodyLabel("线性分析结果")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["指标", "值"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(TABLE_STYLE)
        layout.addWidget(self.table)

    def show_results(self, result) -> None:
        rows = [
            ("斜率 (Slope)", f"{result.slope:.6f}"),
            ("截距 (Intercept)", f"{result.intercept:.6f}"),
            ("R-squared", f"{result.r_squared:.4f}"),
            ("斜率 p 值", f"{result.p_slope:.4f}"),
            ("P/T 比", f"{result.pt_ratio:.4f}"),
            ("线性度", f"{result.linearity:.4f}"),
        ]
        self.table.setRowCount(len(rows))
        for i, (name, val) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(str(val)))
        self.table.resizeRowsToContents()


class BiasChartWidget(CardWidget):
    """Bias analysis chart."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.figure = Figure(figsize=(5, 3.5), dpi=100)
        self.figure.set_facecolor("white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas)

    def plot(self, data, result, col_name: str) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        ax.hist(data, bins=min(30, max(10, len(data) // 3)), density=True, alpha=0.7, color="#4A90D9", edgecolor="white")

        x = np.linspace(data.min(), data.max(), 200)
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        if std > 0:
            y = (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)
            ax.plot(x, y, "r-", linewidth=1.2)

        ax.axvline(result.reference_value, color="#2ECC71", linestyle="--", linewidth=1.2, label=f"参考值={result.reference_value}")
        ax.axvline(mean, color="#E74C3C", linestyle="-", linewidth=1.2, label=f"均值={mean:.3f}")

        ax.set_title(f"{col_name} 偏差分析", fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        self.figure.tight_layout()
        self.canvas.draw()


class LinearChartWidget(CardWidget):
    """Linearity analysis chart."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.figure = Figure(figsize=(5, 3.5), dpi=100)
        self.figure.set_facecolor("white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas)

    def plot(self, result) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        refs = [p.reference for p in result.points]
        biases = [p.bias for p in result.points]

        ax.scatter(refs, biases, color="#4A90D9", s=60, zorder=5, label="观测偏差")
        ax.plot(result.regression_line_x, result.regression_line_y, "r-", linewidth=1.2, label=f"回归线 (y={result.slope:.4f}x+{result.intercept:.4f})")
        ax.axhline(0, color="#2ECC71", linestyle="--", linewidth=1, alpha=0.7, label="零偏差线")

        ax.set_xlabel("参考值", fontsize=10)
        ax.set_ylabel("偏差", fontsize=10)
        ax.set_title("线性分析 (偏差 vs 参考值)", fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        self.figure.tight_layout()
        self.canvas.draw()


class MsaPanelWidget(QWidget):
    """MSA analysis page with bias and linearity."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("msa_panel")
        self.df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)

        header = TitleLabel("MSA 测量系统分析")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        main_layout.addWidget(header)

        desc = BodyLabel("偏差分析与线性分析, 符合 IATF 16949 MSA 要求")
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        main_layout.addWidget(desc)

        top_row = QHBoxLayout()

        self.bias_input = BiasInputCard(self)
        top_row.addWidget(self.bias_input)

        self.linear_input = LinearInputCard(self)
        top_row.addWidget(self.linear_input)

        main_layout.addLayout(top_row)

        mid_row = QHBoxLayout()

        self.bias_results = BiasResultsTable(self)
        mid_row.addWidget(self.bias_results)

        self.linear_results = LinearResultsTable(self)
        mid_row.addWidget(self.linear_results)

        main_layout.addLayout(mid_row)

        chart_row = QHBoxLayout()

        self.bias_chart = BiasChartWidget(self)
        chart_row.addWidget(self.bias_chart)

        self.linear_chart = LinearChartWidget(self)
        chart_row.addWidget(self.linear_chart)

        main_layout.addLayout(chart_row, 1)

    def set_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self.df = df
        self.bias_input.set_dataframe(df)
        self.linear_input.set_dataframe(df)

    def show_bias_results(self, data, result, col_name: str) -> None:
        self.bias_results.show_results(result)
        self.bias_chart.plot(data, result, col_name)

    def show_linear_results(self, result) -> None:
        self.linear_results.show_results(result)
        self.linear_chart.plot(result)
