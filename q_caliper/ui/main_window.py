"""Main application window."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class MainWindow(QWidget):
    """Q-Caliper main window with Fluent Design."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Q-Caliper — 质量工程桌面分析平台")
        self.setMinimumSize(1200, 800)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        label = QLabel("Q-Caliper v0.1.0")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; font-weight: bold; color: #0078D4;")
        layout.addWidget(label)

        subtitle = QLabel("质量工程桌面分析平台 — Minitab 精华功能的开源替代品")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(subtitle)
