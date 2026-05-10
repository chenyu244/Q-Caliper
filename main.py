"""Q-Caliper — 质量工程桌面分析平台."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def main() -> None:
    """Application entry point."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Q-Caliper")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("Q-Caliper")

    from q_caliper.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
