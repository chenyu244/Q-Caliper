"""DOE Panel — design generation, factor effects, Pareto chart."""

# isort: skip_file
from __future__ import annotations

import matplotlib

matplotlib.use("QtAgg")
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import statsmodels.api as sm
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

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy.typing as npt

from q_caliper.core.doe import full_factorial, fractional_factorial, DoeDesign


def _setup_matplotlib_font() -> None:
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "NSimSun",
        "FangSong",
        "KaiTi",
        "Microsoft JhengHei",
        "WenQuanYi Micro Hei",
        "Noto Sans CJK SC",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            matplotlib.rcParams["font.sans-serif"] = [name]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return


_setup_matplotlib_font()


class DoeInputCard(CardWidget):
    """DOE design generation input following Cpk panel style."""

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

        from qfluentwidgets import ToolButton

        self.toggle_btn = ToolButton(FluentIcon.UP, self)
        self.toggle_btn.setFixedSize(30, 30)
        self.toggle_btn.clicked.connect(self._toggle_input)
        header_row.addWidget(self.toggle_btn)

        layout.addLayout(header_row)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 8, 0, 0)

        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(20)

        # Labels
        form_layout.addWidget(QLabel("设计类型:"), 0, 0)
        form_layout.addWidget(QLabel("因子数:"), 0, 1)
        form_layout.addWidget(QLabel("关注结果数:"), 0, 2)

        # Controls
        self.design_type_combo = QComboBox()
        self.design_type_combo.addItems(["全因子 (2^k)", "部分因子 (2^(k-1))"])
        self.design_type_combo.setMinimumWidth(160)
        self.design_type_combo.setFixedHeight(32)
        form_layout.addWidget(self.design_type_combo, 1, 0)

        self.n_factors_spin = QSpinBox()
        self.n_factors_spin.setRange(2, 8)
        self.n_factors_spin.setValue(3)
        self.n_factors_spin.setFixedHeight(32)
        form_layout.addWidget(self.n_factors_spin, 1, 1)

        self.n_responses_spin = QSpinBox()
        self.n_responses_spin.setRange(1, 10)
        self.n_responses_spin.setValue(1)
        self.n_responses_spin.setFixedHeight(32)
        form_layout.addWidget(self.n_responses_spin, 1, 2)

        # Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        row_btn_layout = QHBoxLayout()
        self.gen_btn = PrimaryPushButton("生成设计")
        self.gen_btn.setIcon(FluentIcon.PLAY)
        self.gen_btn.setFixedWidth(100)
        self.gen_btn.setFixedHeight(32)
        self.gen_btn.clicked.connect(self._on_generate)
        row_btn_layout.addWidget(self.gen_btn)

        self.export_btn = PushButton("导出设计 Excel")
        self.export_btn.setIcon(FluentIcon.SAVE)
        self.export_btn.setFixedWidth(130)
        self.export_btn.setFixedHeight(32)
        self.export_btn.clicked.connect(self._on_export_excel)
        row_btn_layout.addWidget(self.export_btn)
        btn_layout.addLayout(row_btn_layout)

        self.report_btn = PushButton("导出 PDF")
        self.report_btn.setIcon(FluentIcon.PRINT)
        self.report_btn.setFixedHeight(32)
        self.report_btn.clicked.connect(self._on_export_pdf)
        self.report_btn.setEnabled(False)
        btn_layout.addWidget(self.report_btn)

        form_layout.addLayout(btn_layout, 0, 3, 2, 1, Qt.AlignmentFlag.AlignVCenter)
        form_layout.setColumnStretch(2, 1)

        content_layout.addLayout(form_layout)

        # Bottom: Response variable selection for analysis
        resp_layout = QHBoxLayout()
        resp_layout.setContentsMargins(0, 8, 0, 0)
        resp_layout.setSpacing(10)

        resp_layout.addWidget(QLabel("响应变量列:"))
        self.response_combo = QComboBox()
        self.response_combo.setPlaceholderText("-- 选择响应变量 --")
        self.response_combo.setMinimumWidth(180)
        self.response_combo.setFixedHeight(32)
        resp_layout.addWidget(self.response_combo)

        self.calc_btn = PrimaryPushButton("计算因子效应")
        self.calc_btn.setIcon(FluentIcon.PLAY)
        self.calc_btn.setFixedHeight(32)
        self.calc_btn.clicked.connect(self._on_calculate)
        resp_layout.addWidget(self.calc_btn)

        resp_layout.addStretch()
        content_layout.addLayout(resp_layout)

        layout.addWidget(self.content_widget)

    def _toggle_input(self) -> None:
        if self.content_widget.isVisible():
            self.content_widget.hide()
            self.toggle_btn.setIcon(FluentIcon.DOWN)
        else:
            self.content_widget.show()
            self.toggle_btn.setIcon(FluentIcon.UP)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df
        self.response_combo.clear()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.response_combo.addItems([str(c) for c in numeric_cols])

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        if mapping.get("响应"):
            col = mapping["响应"][0]
            idx = self.response_combo.findText(col)
            if idx >= 0:
                self.response_combo.setCurrentIndex(idx)
        if mapping.get("因子"):
            n_factors = len(mapping["因子"])
            self.n_factors_spin.setValue(min(n_factors, self.n_factors_spin.maximum()))

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
            InfoBar.error("生成错误", str(e), parent=self, duration=-1)

    def _on_export_excel(self) -> None:
        if not hasattr(self, "current_design"):
            return

        path, _ = QFileDialog.getSaveFileName(self, "导出设计矩阵", "doe_design.xlsx", "Excel 文件 (*.xlsx)")
        if not path:
            return

        design = self.current_design
        n_responses = self.n_responses_spin.value()
        df = pd.DataFrame(design.design_matrix, columns=design.factor_names)
        for r in range(n_responses):
            df[f"[Q]_Response_{r + 1}"] = ""
        df.insert(0, "Run", range(1, design.n_runs + 1))
        df.insert(1, "RunOrder", design.run_order)
        df.to_excel(path, index=False, engine="openpyxl")

        InfoBar.success(
            "导出成功",
            f"设计矩阵已保存至: {path}",
            parent=self,
            duration=5000,
        )

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

    def _on_export_pdf(self) -> None:
        from q_caliper.reports.report_engine import generate_doe_report
        from q_caliper.ui.utils import generate_report_filename

        parent = self.parent()
        while parent and not isinstance(parent, DoePanelWidget):
            parent = parent.parent()

        if not parent:
            return

        if parent.last_design is None:
            InfoBar.warning("提示", "请先生成设计矩阵", parent=self)
            return

        default_name = generate_report_filename("DOE实验设计报告.pdf", str(Path.cwd()))
        path, _ = QFileDialog.getSaveFileName(self, "导出分析报告", default_name, "PDF 文件 (*.pdf)")
        if not path:
            return

        try:
            chart_paths = []
            if parent.last_model is not None:
                figs = [
                    parent.effect_card.effect_fig,
                    parent.effect_card.pareto_fig,
                ]
                for i, fig in enumerate(figs):
                    tmp_img = str(Path(f"tmp_doe_chart_{i}.png").resolve())
                    fig.savefig(tmp_img, dpi=120)
                    chart_paths.append(tmp_img)

            generate_doe_report(
                path,
                design=parent.last_design,
                model=parent.last_model,
                response=parent.last_response,
                chart_paths=chart_paths,
            )
            InfoBar.success("导出成功", f"报告已保存至: {path}", parent=self, duration=5000)
        except Exception as e:
            InfoBar.error("导出失败", f"PDF 生成过程中发生错误：\n{e!s}", parent=self, duration=-1)
        finally:
            for p in chart_paths:
                Path(p).unlink(missing_ok=True)


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

        self.effect_fig = Figure(figsize=(5, 4), dpi=100)
        self.effect_fig.set_facecolor("white")
        self.effect_canvas = FigureCanvas(self.effect_fig)
        self.effect_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.effect_canvas.setMinimumHeight(280)
        chart_row.addWidget(self.effect_canvas)

        self.pareto_fig = Figure(figsize=(5, 4), dpi=100)
        self.pareto_fig.set_facecolor("white")
        self.pareto_canvas = FigureCanvas(self.pareto_fig)
        self.pareto_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.pareto_canvas.setMinimumHeight(280)
        chart_row.addWidget(self.pareto_canvas)

        layout.addLayout(chart_row)

    def plot_effects(self, design: DoeDesign, response: npt.NDArray[np.float64]) -> Any:
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
                ax2.axvline(sig_line, color="#E74C3C", linestyle="--", linewidth=1.2, label="alpha=0.05")
                ax2.legend(fontsize=8)

        ax2.grid(True, alpha=0.3, axis="x")
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        self.pareto_fig.tight_layout()
        self.pareto_canvas.draw()

        self.header_label.setText(
            f"因子效应分析 (R²={model.rsquared:.4f}, F={model.fvalue:.2f}, p={model.f_pvalue:.4f})"
        )

        return model


class DoePanelWidget(QWidget):
    """DOE analysis page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("doe_panel")
        self.last_design: DoeDesign | None = None
        self.last_response: npt.NDArray[np.float64] | None = None
        self.last_model: Any | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(15)

        header_row = QHBoxLayout()
        header = TitleLabel("实验设计 (DOE)")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_row.addWidget(header)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        desc = BodyLabel("生成全因子/部分因子设计矩阵, 分析因子效应和 Pareto 排序")
        desc.setStyleSheet("color: #666; margin-bottom: 2px;")
        main_layout.addWidget(desc)

        self.input_card = DoeInputCard(self)
        main_layout.addWidget(self.input_card)

        charts_scroll = QScrollArea()
        charts_scroll.setWidgetResizable(True)
        charts_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        charts_container = QWidget()
        charts_layout = QVBoxLayout(charts_container)
        charts_layout.setSpacing(8)

        self.effect_card = FactorEffectCard(self)
        charts_layout.addWidget(self.effect_card)

        charts_scroll.setWidget(charts_container)
        main_layout.addWidget(charts_scroll, 1)

    def set_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self.input_card.set_dataframe(df)

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        self.input_card.set_selected_columns(mapping)

    def show_design(self, design: DoeDesign) -> None:
        self.last_design = design

    def analyze_response(self, response: np.ndarray) -> None:
        if self.last_design is None:
            InfoBar.warning("提示", "请先生成设计矩阵", parent=self)
            return

        if len(response) != self.last_design.n_runs:
            InfoBar.warning(
                "数据不匹配",
                f"响应数据 ({len(response)} 个) 与设计矩阵 ({self.last_design.n_runs} 次运行) 不匹配",
                parent=self,
            )
            return

        self.last_response = response
        model = self.effect_card.plot_effects(self.last_design, response)
        self.last_model = model
        self.input_card.report_btn.setEnabled(True)
