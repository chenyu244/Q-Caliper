"""Q-Caliper main window with Fluent Design navigation."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentIcon, FluentWindow, NavigationItemPosition


def _resolve_icon() -> str | None:
    """Find the logo icon for both dev and Nuitka standalone modes."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "images" / "Q-caliper_logo_small.png",
    ]
    if hasattr(sys, "_MEIPASS"):
        candidates.insert(0, Path(sys._MEIPASS) / "images" / "Q-caliper_logo_small.png")
    for p in candidates:
        if p.exists():
            return str(p)
    return None


class MainWindow(FluentWindow):
    """Q-Caliper main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Q-Caliper v1.0")
        self.resize(960, 680)
        self.setMinimumSize(QSize(800, 550))

        icon_path = _resolve_icon()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        self._init_navigation()
        self._center_window()

    def _init_navigation(self) -> None:
        from q_caliper.ui.cpk_panel import CpkPanelWidget
        from q_caliper.ui.data_center import DataCenterWidget
        from q_caliper.ui.doe_panel import DoePanelWidget
        from q_caliper.ui.grr_panel import GrrPanelWidget
        from q_caliper.ui.msa_panel import MsaPanelWidget
        from q_caliper.ui.settings_panel import SettingsPanelWidget
        from q_caliper.ui.spc_panel import SpcPanelWidget

        self.data_center = DataCenterWidget(self)
        self.cpk_panel = CpkPanelWidget(self)
        self.grr_panel = GrrPanelWidget(self)
        self.msa_panel = MsaPanelWidget(self)
        self.spc_panel = SpcPanelWidget(self)
        self.doe_panel = DoePanelWidget(self)
        self.settings_panel = SettingsPanelWidget(self)

        self.addSubInterface(self.data_center, FluentIcon.HOME, "数据中心")
        self.addSubInterface(self.cpk_panel, FluentIcon.PIE_SINGLE, "正态分析")
        self.addSubInterface(self.grr_panel, FluentIcon.PEOPLE, "量具分析")
        self.addSubInterface(self.msa_panel, FluentIcon.SPEED_HIGH, "MSA 分析")
        self.addSubInterface(self.spc_panel, FluentIcon.SPEED_MEDIUM, "SPC 分析")
        self.addSubInterface(self.doe_panel, FluentIcon.LAYOUT, "实验设计 (DOE)")

        self.navigationInterface.addSeparator()

        self.addSubInterface(
            self.settings_panel, FluentIcon.SETTING, "设置",
            position=NavigationItemPosition.BOTTOM,
        )

    def switchTo(self, interface: QWidget) -> None:
        """Switch to a specific interface programmatically."""
        self.stackedWidget.setCurrentWidget(interface)
        self.navigationInterface.setCurrentItem(interface.objectName())

    def _center_window(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)
