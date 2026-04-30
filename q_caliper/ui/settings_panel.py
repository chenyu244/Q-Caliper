"""Settings Panel — application preferences."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    InfoBar,
    LineEdit,
    PrimaryPushButton,
    StrongBodyLabel,
    TitleLabel,
)

from q_caliper.reports.report_engine import ReportConfig, check_typst_available


class ReportSettingsCard(CardWidget):
    """Report generation settings."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("报告设置")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(8)

        self.company_edit = LineEdit()
        self.company_edit.setPlaceholderText("Q-Caliper")
        self.company_edit.setText("Q-Caliper")
        form.addRow("公司名称:", self.company_edit)

        self.author_edit = LineEdit()
        self.author_edit.setPlaceholderText("报告编制人")
        form.addRow("编制人:", self.author_edit)

        layout.addLayout(form)

        self.save_btn = PrimaryPushButton("保存设置")
        self.save_btn.setIcon(FluentIcon.SAVE)
        self.save_btn.setFixedHeight(36)
        self.save_btn.clicked.connect(self._on_save)
        layout.addWidget(self.save_btn)

    def get_config(self) -> ReportConfig:
        return ReportConfig(
            company_name=self.company_edit.text() or "Q-Caliper",
            author=self.author_edit.text(),
        )

    def _on_save(self) -> None:
        InfoBar.success("保存成功", "报告设置已更新", parent=self, duration=1500)


class SystemInfoCard(CardWidget):
    """System information and dependency status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header = StrongBodyLabel("系统信息")
        header.setStyleSheet("font-size: 14px; margin-bottom: 6px;")
        layout.addWidget(header)

        import sys

        import PySide6.QtCore

        info_lines = [
            f"Python: {sys.version.split()[0]}",
            f"Qt: {PySide6.QtCore.__version__}",
            f"Typst (Python): {'可用' if check_typst_available() else '未安装'}",
        ]

        for line in info_lines:
            label = BodyLabel(line)
            label.setStyleSheet("font-size: 12px; padding: 2px 0;")
            layout.addWidget(label)


class SettingsPanelWidget(QWidget):
    """Settings page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settings_panel")
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)

        header = TitleLabel("设置")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        main_layout.addWidget(header)

        desc = BodyLabel("报告配置与系统信息")
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        main_layout.addWidget(desc)

        self.report_settings = ReportSettingsCard(self)
        main_layout.addWidget(self.report_settings)

        self.system_info = SystemInfoCard(self)
        main_layout.addWidget(self.system_info)

        main_layout.addStretch()
