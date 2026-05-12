"""Settings Panel — application preferences and product information."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    HyperlinkButton,
    InfoBar,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    TitleLabel,
)

from q_caliper.core.config import AppConfig
from q_caliper.reports.report_engine import TEMPLATE_DIR, check_typst_available


class ReportSettingsCard(CardWidget):
    """Report generation settings."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = AppConfig.load()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("报告默认设置")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)

        self.company_edit = LineEdit()
        self.company_edit.setPlaceholderText("请输入公司名称")
        self.company_edit.setText(self.config.company_name)
        form.addRow("默认公司:", self.company_edit)

        self.author_edit = LineEdit()
        self.author_edit.setPlaceholderText("请输入编制人姓名")
        self.author_edit.setText(self.config.author)
        form.addRow("默认编制人:", self.author_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.save_btn = PrimaryPushButton("保存设置")
        self.save_btn.setIcon(FluentIcon.SAVE)
        self.save_btn.setFixedHeight(32)
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_save(self) -> None:
        self.config.company_name = self.company_edit.text()
        self.config.author = self.author_edit.text()
        self.config.save()
        InfoBar.success("保存成功", "全局报告设置已持久化存储", parent=self.window(), duration=2000)


class TemplateGuidanceCard(CardWidget):
    """Guidance for report templates."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("报告模板指引")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        desc = BodyLabel("本程序使用 Typst 引擎生成报告，您可以根据需要修改 .typ 模板文件。")
        desc.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(desc)

        path_label = BodyLabel(f"当前路径: {TEMPLATE_DIR}")
        path_label.setStyleSheet("font-size: 11px; color: #888; margin-top: 4px;")
        layout.addWidget(path_label)

        btn_layout = QHBoxLayout()
        self.open_btn = PushButton("打开模板文件夹")
        self.open_btn.setIcon(FluentIcon.FOLDER)
        self.open_btn.setFixedHeight(32)
        self.open_btn.clicked.connect(self._open_template_dir)
        btn_layout.addWidget(self.open_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _open_template_dir(self) -> None:
        if TEMPLATE_DIR.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(TEMPLATE_DIR)))
        else:
            InfoBar.error("错误", "无法定位模板目录", parent=self.window())


class HelpDocsCard(CardWidget):
    """Access to help documents listed individually."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = StrongBodyLabel("帮助文档与手册")
        header.setStyleSheet("font-size: 14px; margin-bottom: 2px;")
        layout.addWidget(header)

        desc = BodyLabel("点击下方手册名称，直接导出并预览 PDF 指南。")
        desc.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 5px;")
        layout.addWidget(desc)

        # Get docs dir
        self.docs_dir = Path(__file__).parents[2] / "docs"
        if not self.docs_dir.exists() and hasattr(sys, "_MEIPASS"):
            self.docs_dir = Path(sys._MEIPASS) / "docs"

        # Document mapping for better display
        self.doc_titles = {
            "qcaliper_capability_guide": "📈 过程能力分析 (Cpk) 指南",
            "qcaliper_doe_guide": "🧪 实验设计 (DOE) 实战指南",
            "qcaliper_msa_guide": "📏 测量系统分析 (MSA) 手册",
            "qcaliper_spc_guide": "📊 统计过程控制 (SPC) 手册",
        }

        if self.docs_dir.exists():
            typ_files = list(self.docs_dir.glob("*.typ"))
            # Sort by priority
            typ_files.sort(key=lambda f: f.name)

            for typ_file in typ_files:
                if typ_file.name == "template.typ":
                    continue

                row = QHBoxLayout()
                title_text = self.doc_titles.get(typ_file.stem, f"📄 {typ_file.stem}")
                lbl = BodyLabel(title_text)
                lbl.setStyleSheet("font-size: 13px;")
                row.addWidget(lbl)

                row.addStretch()

                export_btn = PushButton("导出并查看")
                export_btn.setIcon(FluentIcon.PRINT)
                export_btn.setFixedHeight(28)
                export_btn.clicked.connect(lambda checked, f=typ_file: self._export_and_open(f))
                row.addWidget(export_btn)

                layout.addLayout(row)
        else:
            layout.addWidget(BodyLabel("未找到文档资源"))

    def _export_and_open(self, typ_file: Path) -> None:
        if not check_typst_available():
            InfoBar.warning("组件缺失", "未检测到 Typst 渲染引擎，无法生成 PDF", parent=self.window())
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "导出手册", f"{typ_file.stem}.pdf", "PDF 文件 (*.pdf)")
        if not out_path:
            return

        import typst

        try:
            typst.compile(str(typ_file), output=str(out_path), root=str(self.docs_dir))
            InfoBar.success("成功", f"手册已生成至: {out_path}", parent=self.window())
            QDesktopServices.openUrl(QUrl.fromLocalFile(out_path))
        except Exception as e:
            InfoBar.error("导出失败", f"编译过程中出错: {e}", parent=self.window())


class AboutCard(CardWidget):
    """Product information and links."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("关于 Q-Caliper")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        # Product Info
        info_layout = QFormLayout()
        info_layout.setSpacing(6)

        import PySide6.QtCore

        info_layout.addRow("版本:", BodyLabel("1.0.3 (Stable)"))
        info_layout.addRow("内核:", BodyLabel(f"Python {sys.version.split()[0]} / Qt {PySide6.QtCore.__version__}"))  # type: ignore
        info_layout.addRow("状态:", BodyLabel("Typst 渲染引擎: " + ("就绪" if check_typst_available() else "未安装")))

        layout.addLayout(info_layout)

        # Links
        link_layout = QHBoxLayout()
        self.github_btn = HyperlinkButton(
            url="https://github.com/chenyu244/Q-Caliper", text="GitHub 源代码仓库", parent=self
        )
        self.github_btn.setIcon(FluentIcon.GITHUB)
        link_layout.addWidget(self.github_btn)
        link_layout.addStretch()
        layout.addLayout(link_layout)


class SettingsPanelWidget(QWidget):
    """Settings page with 2-column layout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settings_panel")
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(15)

        header = TitleLabel("设置")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        main_layout.addWidget(header)

        desc = BodyLabel("个性化配置、模版管理与产品信息")
        desc.setStyleSheet("color: #666; margin-bottom: 5px;")
        main_layout.addWidget(desc)

        # 2-Column layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left Column
        left_col = QVBoxLayout()
        left_col.setSpacing(15)
        self.report_settings = ReportSettingsCard(self)
        left_col.addWidget(self.report_settings)
        self.template_guidance = TemplateGuidanceCard(self)
        left_col.addWidget(self.template_guidance)
        left_col.addStretch()
        content_layout.addLayout(left_col, 1)

        # Right Column
        right_col = QVBoxLayout()
        right_col.setSpacing(15)
        self.help_docs = HelpDocsCard(self)
        right_col.addWidget(self.help_docs)
        self.about_card = AboutCard(self)
        right_col.addWidget(self.about_card)
        right_col.addStretch()
        content_layout.addLayout(right_col, 1)

        main_layout.addLayout(content_layout)
