"""DOE Panel — design generation, factor effects, Pareto chart."""

# isort: skip_file
from __future__ import annotations

import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
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

from q_caliper.core.doe import full_factorial, fractional_factorial


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


class DoeInputCard(CardWidget):
    """DOE design generation input."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("实验设计生成")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(8)

        self.design_type_combo = QComboBox()
        self.design_type_combo.addItems(["全因子 (2^k)", "部分因子 (2^(k-1))"])
        form.addRow("设计类型:", self.design_type_combo)

        self.n_factors_spin = QSpinBox()
        self.n_factors_spin.setRange(2, 8)
        self.n_factors_spin.setValue(3)
        form.addRow("因子数:", self.n_factors_spin)

        layout.addLayout(form)

        self.gen_btn = PrimaryPushButton("生成设计矩阵")
        self.gen_btn.setIcon(FluentIcon.PLAY)
        self.gen_btn.setFixedHeight(36)
        self.gen_btn.clicked.connect(self._on_generate)
        layout.addWidget(self.gen_btn)

        self.export_btn = PrimaryPushButton("导出 Excel")
        self.export_btn.setIcon(FluentIcon.SAVE)
        self.export_btn.setFixedHeight(36)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export)
        layout.addWidget(self.export_btn)

    def _on_generate(self) -> None:
        n_factors = self.n_factors_spin.value()
        design_type = self.design_type_combo.currentIndex()

        try:
            if design_type == 0:
                design = full_factorial(n_factors, randomize=False)
            else:
                if n_factors < 3:
                    InfoBar.warning("参数错误", "部分因子至少需要 3 个因子", parent=self)
                    return
                design = fractional_factorial(n_factors, randomize=False)

            self.current_design = design
            self.export_btn.setEnabled(True)

            parent = self.parent()
            while parent and not isinstance(parent, DoePanelWidget):
                parent = parent.parent()
            if isinstance(parent, DoePanelWidget):
                parent.show_design(design)

        except Exception as e:
            InfoBar.error("生成错误", str(e), parent=self)

    def _on_export(self) -> None:
        if not hasattr(self, "current_design"):
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "导出设计矩阵", "doe_design.xlsx", "Excel 文件 (*.xlsx)"
        )
        if not path:
            return

        design = self.current_design
        df = pd.DataFrame(design.design_matrix, columns=design.factor_names)
        df.insert(0, "Run", range(1, design.n_runs + 1))
        df.insert(1, "RunOrder", design.run_order)
        df.to_excel(path, index=False, engine="openpyxl")
        InfoBar.success("导出成功", f"已保存到 {path}", parent=self, duration=2000)


class DesignTableCard(CardWidget):
    """Design matrix display table."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        self.header_label = StrongBodyLabel("设计矩阵")
        self.header_label.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(self.header_label)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(TABLE_STYLE)
        layout.addWidget(self.table)

    def show_design(self, design) -> None:
        self.header_label.setText(f"设计矩阵 — {design.design_type} ({design.n_runs} 次运行)")

        headers = ["Run", "顺序", *design.factor_names]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(design.n_runs)

        for i in range(design.n_runs):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(str(design.run_order[i] + 1)))
            for j, val in enumerate(design.design_matrix[i]):
                item = QTableWidgetItem(f"{val:+.0f}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, j + 2, item)

        self.table.resizeColumnsToContents()


class FactorEffectCard(CardWidget):
    """Factor effect and Pareto charts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.header_label = StrongBodyLabel("因子效应分析")
        self.header_label.setStyleSheet("font-size: 14px; margin-bottom: 4px;")
        layout.addWidget(self.header_label)

        hint = BodyLabel("加载响应数据后自动计算因子效应和 Pareto 排序")
        hint.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(hint)

        chart_row = QHBoxLayout()

        self.effect_fig = Figure(figsize=(4.5, 3), dpi=100)
        self.effect_fig.set_facecolor("white")
        self.effect_canvas = FigureCanvas(self.effect_fig)
        chart_row.addWidget(self.effect_canvas)

        self.pareto_fig = Figure(figsize=(4.5, 3), dpi=100)
        self.pareto_fig.set_facecolor("white")
        self.pareto_canvas = FigureCanvas(self.pareto_fig)
        chart_row.addWidget(self.pareto_canvas)

        layout.addLayout(chart_row)

    def plot_effects(self, design, response: np.ndarray) -> None:
        x_mat = design.design_matrix
        x_with_const = sm.add_constant(x_mat)
        model = sm.OLS(response, x_with_const).fit()

        effects = model.params[1:]
        pvalues = model.pvalues[1:]
        factor_names = design.factor_names

        self.effect_fig.clear()
        ax1 = self.effect_fig.add_subplot(111)

        x = range(len(effects))
        colors = ["#4A90D9" if p < 0.05 else "#CCCCCC" for p in pvalues]
        ax1.bar(x, effects, color=colors, alpha=0.8, edgecolor="white")
        ax1.axhline(0, color="black", linewidth=0.8)
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(factor_names, rotation=45, ha="right", fontsize=9)
        ax1.set_ylabel("效应值", fontsize=10)
        ax1.set_title("主效应图", fontsize=11, fontweight="bold")
        ax1.grid(True, alpha=0.3, axis="y")
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)
        self.effect_fig.tight_layout()
        self.effect_canvas.draw()

        self.pareto_fig.clear()
        ax2 = self.pareto_fig.add_subplot(111)

        abs_effects = np.abs(effects)
        sorted_idx = np.argsort(abs_effects)[::-1]
        sorted_names = [factor_names[i] for i in sorted_idx]
        sorted_abs = abs_effects[sorted_idx]
        sorted_p = pvalues[sorted_idx]

        colors2 = ["#E74C3C" if p < 0.05 else "#AAAAAA" for p in sorted_p]
        y = range(len(sorted_abs))
        ax2.barh(list(y), sorted_abs, color=colors2, alpha=0.8, edgecolor="white")
        ax2.set_yticks(list(y))
        ax2.set_yticklabels(sorted_names, fontsize=9)
        ax2.set_xlabel("|效应|", fontsize=10)
        ax2.set_title("Pareto 效应排序", fontsize=11, fontweight="bold")
        ax2.invert_yaxis()

        if len(sorted_abs) > 0:
            from scipy import stats as sp_stats
            df_resid = model.df_resid
            if df_resid > 0:
                mse = model.mse_resid
                se_effect = np.sqrt(4 * mse / len(response))
                t_crit = sp_stats.t.ppf(1 - 0.025, df_resid)
                sig_line = t_crit * se_effect
                ax2.axvline(sig_line, color="#E74C3C", linestyle="--", linewidth=1.5, label="alpha=0.05")
                ax2.legend(fontsize=8)

        ax2.grid(True, alpha=0.3, axis="x")
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        self.pareto_fig.tight_layout()
        self.pareto_canvas.draw()

        self.header_label.setText(f"因子效应分析 (R²={model.rsquared:.4f}, F={model.fvalue:.2f}, p={model.f_pvalue:.4f})")


class DoeResponseCard(CardWidget):
    """Response input for DOE analysis."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("响应数据")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(8)

        self.response_combo = QComboBox()
        self.response_combo.setPlaceholderText("-- 响应变量列 --")
        form.addRow("响应列:", self.response_combo)

        layout.addLayout(form)

        self.calc_btn = PrimaryPushButton("计算因子效应")
        self.calc_btn.setIcon(FluentIcon.PLAY)
        self.calc_btn.setFixedHeight(36)
        self.calc_btn.clicked.connect(self._on_calculate)
        layout.addWidget(self.calc_btn)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df
        self.response_combo.clear()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.response_combo.addItems([str(c) for c in numeric_cols])

    def _on_calculate(self) -> None:
        if self.df is None:
            InfoBar.warning("提示", "请先在数据中心加载包含响应数据的文件", parent=self)
            return

        col = self.response_combo.currentText()
        if not col:
            InfoBar.warning("提示", "请选择响应变量列", parent=self)
            return

        parent = self.parent()
        while parent and not isinstance(parent, DoePanelWidget):
            parent = parent.parent()
        if isinstance(parent, DoePanelWidget):
            parent.analyze_response(self.df[col].dropna().values)


class DoePanelWidget(QWidget):
    """DOE analysis page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("doe_panel")
        self.current_design = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)

        header = TitleLabel("DOE 实验设计")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        main_layout.addWidget(header)

        desc = BodyLabel("生成全因子/部分因子设计矩阵, 分析因子效应和 Pareto 排序")
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        main_layout.addWidget(desc)

        top_row = QHBoxLayout()

        self.input_card = DoeInputCard(self)
        top_row.addWidget(self.input_card)

        self.response_card = DoeResponseCard(self)
        top_row.addWidget(self.response_card)

        main_layout.addLayout(top_row)

        self.design_table = DesignTableCard(self)
        main_layout.addWidget(self.design_table, 1)

        self.effect_card = FactorEffectCard(self)
        main_layout.addWidget(self.effect_card, 1)

    def set_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self.response_card.set_dataframe(df)

    def show_design(self, design) -> None:
        self.current_design = design
        self.design_table.show_design(design)

    def analyze_response(self, response: np.ndarray) -> None:
        if self.current_design is None:
            InfoBar.warning("提示", "请先生成设计矩阵", parent=self)
            return

        if len(response) != self.current_design.n_runs:
            InfoBar.warning(
                "数据不匹配",
                f"响应数据 ({len(response)} 个) 与设计矩阵 ({self.current_design.n_runs} 次运行) 不匹配",
                parent=self,
            )
            return

        self.effect_card.plot_effects(self.current_design, response)
