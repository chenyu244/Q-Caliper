"""GRR Analysis Panel — data input, ANOVA calculation, 6-chart dashboard."""

# isort: skip_file
from __future__ import annotations

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
    QScrollArea,
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

from q_caliper.core.grr import calculate_grr, validate_grr_data


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


class GrrInputCard(CardWidget):
    """GRR parameter and column mapping input."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("GRR 参数设置")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(8)

        self.measure_combo = QComboBox()
        self.measure_combo.setPlaceholderText("-- 测量数据列 --")
        form.addRow("测量列:", self.measure_combo)

        self.operator_combo = QComboBox()
        self.operator_combo.setPlaceholderText("-- 操作者列 --")
        form.addRow("操作者列:", self.operator_combo)

        self.part_combo = QComboBox()
        self.part_combo.setPlaceholderText("-- 零件列 --")
        form.addRow("零件列:", self.part_combo)

        self.n_parts_spin = QSpinBox()
        self.n_parts_spin.setRange(2, 100)
        self.n_parts_spin.setValue(10)
        form.addRow("零件数:", self.n_parts_spin)

        self.n_ops_spin = QSpinBox()
        self.n_ops_spin.setRange(2, 20)
        self.n_ops_spin.setValue(3)
        form.addRow("操作者数:", self.n_ops_spin)

        self.n_trials_spin = QSpinBox()
        self.n_trials_spin.setRange(2, 20)
        self.n_trials_spin.setValue(3)
        form.addRow("重复次数:", self.n_trials_spin)

        layout.addLayout(form)

        self.calc_btn = PrimaryPushButton("计算 GRR")
        self.calc_btn.setIcon(FluentIcon.PLAY)
        self.calc_btn.setFixedHeight(36)
        self.calc_btn.clicked.connect(self._on_calculate)
        layout.addWidget(self.calc_btn)

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
                InfoBar.warning("操作者数不匹配", f"数据中有 {len(operators)} 个不同操作者, 设置为 {n_ops}", parent=self)
                n_ops = len(operators)
                self.n_ops_spin.setValue(n_ops)

            data_flat = []
            for p in parts:
                for o in operators:
                    subset = df[(df[part_col] == p) & (df[operator_col] == o)][measure_col].values
                    if len(subset) < n_trials:
                        InfoBar.error("数据不足", f"零件={p}, 操作者={o} 只有 {len(subset)} 条数据, 需要 {n_trials}", parent=self)
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

        except Exception as e:
            InfoBar.error("计算错误", str(e), parent=self)


class GrrResultsTable(CardWidget):
    """GRR ANOVA results and variance components."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        header = StrongBodyLabel("GRR 分析结果")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(2)
        self.summary_table.setHorizontalHeaderLabels(["指标", "值"])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setStyleSheet(TABLE_STYLE)
        layout.addWidget(self.summary_table)

        anova_label = StrongBodyLabel("ANOVA 方差分析表")
        anova_label.setStyleSheet("font-size: 13px; margin-top: 8px;")
        layout.addWidget(anova_label)

        self.anova_table = QTableWidget()
        self.anova_table.setColumnCount(6)
        self.anova_table.setHorizontalHeaderLabels(["来源", "SS", "df", "MS", "F", "p-value"])
        self.anova_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.anova_table.verticalHeader().setVisible(False)
        self.anova_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.anova_table.setAlternatingRowColors(True)
        self.anova_table.setStyleSheet(TABLE_STYLE)
        layout.addWidget(self.anova_table)

    def show_results(self, result) -> None:
        pct_grr_grade = "<10% 可接受" if result.pct_grr < 10 else "<30% 可接受" if result.pct_grr < 30 else "不可接受"
        ndc_grade = ">=5 可接受" if result.ndc >= 5 else "<5 不可接受"

        summary_rows = [
            ("变异分量", ""),
            ("  重复性 (EV)", f"{result.var_repeatability:.6f}"),
            ("  再现性 (AV)", f"{result.var_reproducibility:.6f}"),
            ("  交互 (INT)", f"{result.var_interaction:.6f}"),
            ("  零件 (PV)", f"{result.var_parts:.6f}"),
            ("  总变异", f"{result.var_total:.6f}"),
            ("---", "---"),
            ("GRR 指标", ""),
            ("  %GRR", f"{result.pct_grr:.2f}%  {pct_grr_grade}"),
            ("  %PV", f"{result.pct_part_variation:.2f}%"),
            ("  ndc (分级数)", f"{result.ndc}  {ndc_grade}"),
            ("  F 统计量", f"{result.f_statistic:.4f}"),
            ("  p 值", f"{result.p_value:.4f}"),
        ]

        self.summary_table.setRowCount(len(summary_rows))
        for i, (name, val) in enumerate(summary_rows):
            self.summary_table.setItem(i, 0, QTableWidgetItem(name))
            self.summary_table.setItem(i, 1, QTableWidgetItem(str(val)))
        self.summary_table.resizeRowsToContents()

        self.anova_table.setRowCount(len(result.anova_table))
        for i, row in enumerate(result.anova_table):
            self.anova_table.setItem(i, 0, QTableWidgetItem(row.source))
            self.anova_table.setItem(i, 1, QTableWidgetItem(f"{row.ss:.4f}"))
            self.anova_table.setItem(i, 2, QTableWidgetItem(str(row.df)))
            self.anova_table.setItem(i, 3, QTableWidgetItem(f"{row.ms:.4f}"))
            self.anova_table.setItem(i, 4, QTableWidgetItem(f"{row.f_value:.4f}" if row.f_value else "-"))
            self.anova_table.setItem(i, 5, QTableWidgetItem(f"{row.p_value:.4f}" if row.p_value else "-"))
        self.anova_table.resizeRowsToContents()


class GrrChartsDashboard(QWidget):
    """6-chart GRR dashboard."""

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

        self.fig1 = Figure(figsize=(4, 3), dpi=90)
        self.canvas1 = FigureCanvas(self.fig1)
        row1.addWidget(self.canvas1)

        self.fig2 = Figure(figsize=(4, 3), dpi=90)
        self.canvas2 = FigureCanvas(self.fig2)
        row1.addWidget(self.canvas2)

        self.fig3 = Figure(figsize=(4, 3), dpi=90)
        self.canvas3 = FigureCanvas(self.fig3)
        row2.addWidget(self.canvas3)

        self.fig4 = Figure(figsize=(4, 3), dpi=90)
        self.canvas4 = FigureCanvas(self.fig4)
        row2.addWidget(self.canvas4)

        self.fig5 = Figure(figsize=(4, 3), dpi=90)
        self.canvas5 = FigureCanvas(self.fig5)
        row3.addWidget(self.canvas5)

        self.fig6 = Figure(figsize=(4, 3), dpi=90)
        self.canvas6 = FigureCanvas(self.fig6)
        row3.addWidget(self.canvas6)

        self.grid_layout.addLayout(row1)
        self.grid_layout.addLayout(row2)
        self.grid_layout.addLayout(row3)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def plot_all(self, result, part_names: list[str], operator_names: list[str]) -> None:
        arr = result.raw_data
        n_parts = result.n_parts
        n_ops = result.n_operators

        self._plot_by_part(self.fig1, self.canvas1, arr, n_parts, n_ops, part_names)
        self._plot_by_operator(self.fig2, self.canvas2, arr, n_parts, n_ops, operator_names)
        self._plot_operator_control(self.fig3, self.canvas3, result, operator_names)
        self._plot_part_control(self.fig4, self.canvas4, result, part_names)
        self._plot_interaction(self.fig5, self.canvas5, arr, n_parts, n_ops, part_names, operator_names)
        self._plot_variance_pie(self.fig6, self.canvas6, result)

    def _plot_by_part(self, fig, canvas, arr, n_parts, n_ops, part_names):
        fig.clear()
        ax = fig.add_subplot(111)
        part_data = [arr[i, :, :].flatten() for i in range(n_parts)]
        bp = ax.boxplot(part_data, patch_artist=True, labels=part_names[:n_parts])
        colors = ["#4A90D9", "#50C878", "#FFB347", "#FF6B6B", "#9B59B6", "#1ABC9C", "#E74C3C", "#3498DB", "#F39C12", "#2ECC71"]
        for i, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(colors[i % len(colors)])
            patch.set_alpha(0.7)
        ax.set_title("按零件分组", fontsize=11, fontweight="bold")
        ax.set_ylabel("测量值")
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis="x", rotation=45, labelsize=8)
        fig.tight_layout()
        canvas.draw()

    def _plot_by_operator(self, fig, canvas, arr, n_parts, n_ops, operator_names):
        fig.clear()
        ax = fig.add_subplot(111)
        op_data = [arr[:, j, :].flatten() for j in range(n_ops)]
        bp = ax.boxplot(op_data, patch_artist=True, labels=operator_names[:n_ops])
        colors = ["#4A90D9", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6"]
        for i, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(colors[i % len(colors)])
            patch.set_alpha(0.7)
        ax.set_title("按操作者分组", fontsize=11, fontweight="bold")
        ax.set_ylabel("测量值")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        canvas.draw()

    def _plot_operator_control(self, fig, canvas, result, operator_names):
        fig.clear()
        ax = fig.add_subplot(111)
        means = result.operator_means
        x = range(len(means))
        ax.bar(x, means, color="#4A90D9", alpha=0.8, edgecolor="white")
        ax.axhline(result.grand_mean, color="#E74C3C", linestyle="--", linewidth=1.5, label=f"总均值={result.grand_mean:.3f}")
        ax.set_title("操作者均值图", fontsize=11, fontweight="bold")
        ax.set_xticks(list(x))
        ax.set_xticklabels(operator_names[:len(means)], rotation=45, fontsize=8)
        ax.set_ylabel("均值")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis="y")
        fig.tight_layout()
        canvas.draw()

    def _plot_part_control(self, fig, canvas, result, part_names):
        fig.clear()
        ax = fig.add_subplot(111)
        means = result.part_means
        x = range(len(means))
        ax.bar(x, means, color="#50C878", alpha=0.8, edgecolor="white")
        ax.axhline(result.grand_mean, color="#E74C3C", linestyle="--", linewidth=1.5, label=f"总均值={result.grand_mean:.3f}")
        ax.set_title("零件均值图", fontsize=11, fontweight="bold")
        ax.set_xticks(list(x))
        ax.set_xticklabels(part_names[:len(means)], rotation=45, fontsize=7)
        ax.set_ylabel("均值")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis="y")
        fig.tight_layout()
        canvas.draw()

    def _plot_interaction(self, fig, canvas, arr, n_parts, n_ops, part_names, operator_names):
        fig.clear()
        ax = fig.add_subplot(111)
        cell_means = np.mean(arr, axis=2)
        colors = ["#4A90D9", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6"]
        for j in range(n_ops):
            ax.plot(
                range(n_parts), cell_means[:, j],
                marker="o", color=colors[j % len(colors)],
                linewidth=2, markersize=6, label=operator_names[j],
            )
        ax.set_title("零件x操作者 交互图", fontsize=11, fontweight="bold")
        ax.set_xticks(range(n_parts))
        ax.set_xticklabels(part_names[:n_parts], rotation=45, fontsize=7)
        ax.set_ylabel("均值")
        ax.legend(fontsize=8, loc="best")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        canvas.draw()

    def _plot_variance_pie(self, fig, canvas, result):
        fig.clear()
        ax = fig.add_subplot(111)
        labels = ["重复性(EV)", "再现性(AV)", "交互(INT)", "零件(PV)"]
        sizes = [result.var_repeatability, result.var_reproducibility, result.var_interaction, result.var_parts]
        colors = ["#4A90D9", "#E74C3C", "#F39C12", "#50C878"]
        non_zero = [(lb, s, c) for lb, s, c in zip(labels, sizes, colors, strict=False) if s > 0]
        if non_zero:
            lz, sz, cz = zip(*non_zero, strict=False)
            _wedges, _texts, autotexts = ax.pie(
                sz, labels=lz, colors=cz, autopct="%1.1f%%",
                startangle=90, pctdistance=0.75,
                textprops={"fontsize": 9},
            )
            for t in autotexts:
                t.set_fontsize(8)
                t.set_fontweight("bold")
        ax.set_title("变异分量占比", fontsize=11, fontweight="bold")
        fig.tight_layout()
        canvas.draw()


class GrrPanelWidget(QWidget):
    """GRR analysis page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("grr_panel")
        self.df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)

        header = TitleLabel("GRR 量具重复性与再现性分析")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        main_layout.addWidget(header)

        desc = BodyLabel("基于 ANOVA 方法的 GRR 分析, 符合 IATF 16949 MSA 要求")
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        main_layout.addWidget(desc)

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setSizes([320, 600])

        self.input_card = GrrInputCard(self)
        top_splitter.addWidget(self.input_card)

        self.results_table = GrrResultsTable(self)
        top_splitter.addWidget(self.results_table)

        self.charts = GrrChartsDashboard(self)

        main_layout.addWidget(top_splitter, 1)
        main_layout.addWidget(self.charts, 2)

    def set_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self.df = df
        self.input_card.set_dataframe(df)

    def show_results(self, result, part_names: list[str], operator_names: list[str]) -> None:
        self.results_table.show_results(result)
        self.charts.plot_all(result, part_names, operator_names)
