"""Q-Caliper main window with Fluent Design navigation."""

from __future__ import annotations

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentIcon, FluentWindow, SubtitleLabel


class MainWindow(FluentWindow):
    """Q-Caliper main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Q-Caliper v0.1.0")
        self.resize(960, 680)
        self.setMinimumSize(QSize(800, 550))

        self._init_navigation()
        self._center_window()

    def _init_navigation(self) -> None:
        from q_caliper.ui.cpk_panel import CpkPanelWidget
        from q_caliper.ui.data_center import DataCenterWidget

        self.data_center = DataCenterWidget(self)
        self.cpk_panel = CpkPanelWidget(self)

        self.addSubInterface(self.data_center, FluentIcon.HOME, "数据中心")
        self.addSubInterface(self.cpk_panel, FluentIcon.PIE_SINGLE, "Cpk 分析")

        self.navigationInterface.addSeparator()

        info_widget = SubtitleLabel("Q-Caliper")
        info_widget.setFixedHeight(40)

    def _center_window(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)
