"""Normal Analysis Panel — histogram, normality test, and capability analysis."""

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
    QGridLayout,
    QHBoxLayout,
    QLabel,
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

from q_caliper.core.cpk import calculate_capability, normality_test


def _setup_matplotlib_font() -> None:
    """Configure matplotlib to use a CJK font for Chinese labels."""
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["axes.unicode_minus"] = False


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

        header_row = QHBoxLayout()
        header = StrongBodyLabel("分析参数设置")
        header.setStyleSheet("font-size: 14px;")
        header_row.addWidget(header)
        header_row.addStretch()
        layout.addLayout(header_row)

        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(20)

        # Row 0: Labels
        form_layout.addWidget(QLabel("测量数据列:"), 0, 0)

        spec_lbl_layout = QHBoxLayout()
        spec_lbl_layout.setContentsMargins(0, 0, 0, 0)
        spec_lbl_layout.addWidget(QLabel("规格限 (LSL / USL):"))
        self.magic_btn = PushButton("智能推荐")
        self.magic_btn.setFixedHeight(22)
        self.magic_btn.setStyleSheet("font-size: 11px; padding: 0 5px;")
        self.magic_btn.clicked.connect(self._show_spec_menu)
        spec_lbl_layout.addWidget(self.magic_btn)
        spec_lbl_layout.addStretch()
        form_layout.addLayout(spec_lbl_layout, 0, 1)

        sg_lbl_layout = QHBoxLayout()
        sg_lbl_layout.setContentsMargins(0, 0, 0, 0)
        sg_lbl_layout.addWidget(QLabel("子组大小:"))
        self.sg_help = PushButton("")
        self.sg_help.setIcon(FluentIcon.QUESTION)
        self.sg_help.setFixedSize(20, 20)
        self.sg_help.setToolTip(
            "推荐原则：\n"
            "1. 子组内样本应在短时间内产生，子组间应有时间差。\n"
            "2. 默认推荐 n=5，即使数据连续，人为分组也能诊断过程漂移。\n"
            "3. Cpk (短期潜力) 依赖子组变异，Ppk (长期性能) 依赖全变异。"
        )
        sg_lbl_layout.addWidget(self.sg_help)
        sg_lbl_layout.addStretch()
        form_layout.addLayout(sg_lbl_layout, 0, 2)

        # Row 1: Controls
        self.measure_combo = QComboBox()
        self.measure_combo.setMinimumWidth(180)
        self.measure_combo.setFixedHeight(32)
        self.measure_combo.setPlaceholderText("-- 选择列 --")
        form_layout.addWidget(self.measure_combo, 1, 0)

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
        form_layout.addLayout(spec_input_row, 1, 1)

        self.subgroup_spin = QDoubleSpinBox()
        self.subgroup_spin.setRange(1, 100)
        self.subgroup_spin.setDecimals(0)
        self.subgroup_spin.setValue(5)
        self.subgroup_spin.setFixedHeight(32)
        form_layout.addWidget(self.subgroup_spin, 1, 2)

        # Buttons on the right
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

        form_layout.addLayout(btn_layout, 0, 3, 2, 1, Qt.AlignmentFlag.AlignVCenter)
        form_layout.setColumnStretch(1, 1)

        layout.addLayout(form_layout)

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
            ("±3 Sigma (99.7%)", mean + 3 * std, mean - 3 * std),
            ("±6 Sigma (精密)", mean + 6 * std, mean - 6 * std),
            ("全范围 (Max/Min)", np.max(data), np.min(data)),
            ("重置规格", -1e12, -1e12),
        ]

        for text, usl, lsl in actions:
            act = Action(text, self)
            # 注意：triggered 信号会发送一个 bool 类型的 checked 参数，
            # 如果不显式接收，它会覆盖 lambda 中的第一个默认参数 u
            act.triggered.connect(lambda checked, u=usl, low=lsl, t=text: self._apply_spec(u, low, t))
            menu.addAction(act)

        menu.exec(self.magic_btn.mapToGlobal(self.magic_btn.rect().bottomLeft()))

    def _apply_spec(self, usl: float, lsl: float, text: str = "智能推荐") -> None:
        self.usl_spin.setValue(usl)
        self.lsl_spin.setValue(lsl)
        self.magic_btn.setText(text)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df
        self.measure_combo.clear()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.measure_combo.addItems([str(c) for c in numeric_cols])

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        """Pre-select measurement column based on roles from Data Center."""
        if mapping.get("测量值"):
            col = mapping["测量值"][0]
            index = self.measure_combo.findText(col)
            if index >= 0:
                self.measure_combo.setCurrentIndex(index)

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

        sg_size = int(self.subgroup_spin.value())

        try:
            norm_result = normality_test(data)
            cpk_result = calculate_capability(data, usl_val, lsl_val, sg_size)
        except Exception as e:
            InfoBar.error("分析错误", str(e), parent=self)
            return

        parent = self.parent()
        while parent and not isinstance(parent, CpkPanelWidget):
            parent = parent.parent()
        if isinstance(parent, CpkPanelWidget):
            parent.show_results(data, norm_result, cpk_result, col)
            self.report_btn.setEnabled(True)

    def _on_export_pdf(self) -> None:
        from q_caliper.reports.report_engine import generate_cpk_report

        parent = self.parent()
        while parent and not isinstance(parent, CpkPanelWidget):
            parent = parent.parent()

        if not parent or parent.last_result is None:
            return

        path, _ = QFileDialog.getSaveFileName(self, "导出分析报告", "正态分析报告.pdf", "PDF 文件 (*.pdf)")
        if not path:
            return

        try:
            # 使用绝对路径避免路径问题
            tmp_img = str(Path("tmp_capability.png").resolve())
            parent.histogram.figure.savefig(tmp_img, dpi=120)

            generate_cpk_report(path, parent.last_result, parent.last_norm, tmp_img)
            InfoBar.success("导出成功", f"报告已保存至: {path}", parent=self, duration=5000)
        except Exception as e:
            # 使用 InfoBar 显示长效错误，不阻塞 UI 线程
            InfoBar.error("导出失败", f"PDF 生成过程中发生错误：\n{e!s}", parent=self, duration=-1)


class HistogramWidget(CardWidget):
    """Histogram with normal fit curve and spec limits."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.figure.set_facecolor("white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas)

    def plot(self, data: np.ndarray, norm_result, cpk_result, col_name: str) -> None:
        self.figure.clear()

        # 调整布局留出右侧空间给统计框, 使用 1x2 布局
        gs = self.figure.add_gridspec(1, 2, width_ratios=[4, 1.2], wspace=0.1)
        ax = self.figure.add_subplot(gs[0])

        # 1. 绘制直方图
        n_bins = min(50, max(10, len(data) // 5))
        ax.hist(
            data,
            bins=n_bins,
            density=True,
            alpha=0.6,
            color="#4A90D9",
            edgecolor="white",
            linewidth=0.5,
            label="数据分布",
        )

        # 2. 绘制正态拟合
        xmin, xmax = ax.get_xlim()
        x = np.linspace(min(data.min(), xmin), max(data.max(), xmax), 300)

        # 整体正态曲线 (实线)
        y_overall = (1 / (cpk_result.std_overall * np.sqrt(2 * np.pi))) * np.exp(
            -0.5 * ((x - cpk_result.mean) / cpk_result.std_overall) ** 2
        )
        ax.plot(x, y_overall, color="#E74C3C", linewidth=1.5, label="整体正态")

        # 组内正态曲线 (虚线)
        y_within = (1 / (cpk_result.std_within * np.sqrt(2 * np.pi))) * np.exp(
            -0.5 * ((x - cpk_result.mean) / cpk_result.std_within) ** 2
        )
        ax.plot(x, y_within, color="#27AE60", linestyle="--", linewidth=1.5, label="组内正态")

        # 3. 规格限
        if cpk_result.usl is not None:
            ax.axvline(cpk_result.usl, color="#E67E22", linestyle="-", linewidth=2)
            ax.text(cpk_result.usl, ax.get_ylim()[1] * 1.02, "USL", color="#E67E22", ha="center", fontweight="bold")
        if cpk_result.lsl is not None:
            ax.axvline(cpk_result.lsl, color="#E67E22", linestyle="-", linewidth=2)
            ax.text(cpk_result.lsl, ax.get_ylim()[1] * 1.02, "LSL", color="#E67E22", ha="center", fontweight="bold")

        ax.set_title(f"{col_name} 过程能力报告", fontsize=14, fontweight="bold", pad=20)
        ax.grid(True, alpha=0.2)
        ax.legend(loc="upper left", fontsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # 4. 统计信息文本框 (右侧)
        ax_stats = self.figure.add_subplot(gs[1])
        ax_stats.axis("off")

        stats_text = (
            f"过程数据\n"
            f"LSL: {cpk_result.lsl if cpk_result.lsl is not None else '无':>8}\n"
            f"目标: {'-':>8}\n"
            f"USL: {cpk_result.usl if cpk_result.usl is not None else '无':>8}\n"
            f"样本均值: {cpk_result.mean:.4f}\n"
            f"样本 N: {cpk_result.sample_size}\n"
            f"标准差(整体): {cpk_result.std_overall:.4f}\n"
            f"标准差(组内): {cpk_result.std_within:.4f}\n"
        )

        if cpk_result.cpk is not None:
            stats_text += (
                f"\n能力指标 (组内 / 整体)\n"
                f"Cp : {cpk_result.cp:<5.2f}    Pp : {cpk_result.pp:<5.2f}\n"
                f"Cpk: {cpk_result.cpk:<5.2f}    Ppk: {cpk_result.ppk:<5.2f}\n"
            )

        ax_stats.text(
            0, 1, stats_text, transform=ax_stats.transAxes, verticalalignment="top", fontsize=9, linespacing=1.6
        )

        self.figure.tight_layout()
        self.canvas.draw()


class CpkPanelWidget(QWidget):
    """Normal analysis page with column mapping and professional histogram."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cpk_panel")
        self.df: pd.DataFrame | None = None
        self.last_result = None
        self.last_norm = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(15)

        header_row = QHBoxLayout()
        header = TitleLabel("正态性与过程能力分析")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_row.addWidget(header)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        desc = BodyLabel("执行正态性检验、直方图拟合及 Cpk/Ppk 能力评估")
        desc.setStyleSheet("color: #666; margin-bottom: 2px;")
        main_layout.addWidget(desc)

        # 顶部参数区 (横向排列)
        self.mapping_card = ColumnMappingCard(self)
        main_layout.addWidget(self.mapping_card)

        # 底部图表区
        self.histogram = HistogramWidget(self)
        main_layout.addWidget(self.histogram, 1)

    def set_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self.df = df
        self.mapping_card.set_dataframe(df)

    def set_selected_columns(self, mapping: dict[str, list[str]]) -> None:
        self.mapping_card.set_selected_columns(mapping)

    def show_results(self, data, norm_result, cpk_result, col_name: str) -> None:
        self.last_result = cpk_result
        self.last_norm = norm_result
        self.histogram.plot(data, norm_result, cpk_result, col_name)
