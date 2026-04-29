"""Data Center — drag-drop Excel loading and data preview."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    InfoBar,
    PrimaryPushButton,
    SubtitleLabel,
    TitleLabel,
)


class DropZone(CardWidget):
    """Drag-and-drop zone for Excel/CSV files."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self.setMaximumHeight(200)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(FluentIcon.FOLDER_ADD.icon().pixmap(48, 48))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        self.title_label = SubtitleLabel("拖拽 Excel/CSV 文件到此处")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.subtitle_label = BodyLabel("支持 .xlsx / .xlsm / .csv 格式")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("color: #888;")
        layout.addWidget(self.subtitle_label)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.browse_btn = PrimaryPushButton("浏览文件")
        self.browse_btn.setIcon(FluentIcon.FOLDER)
        self.browse_btn.clicked.connect(self._browse_file)
        btn_row.addWidget(self.browse_btn)
        layout.addLayout(btn_row)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("CardWidget { border: 2px dashed #0078D4; }")

    def dragLeaveEvent(self, event) -> None:
        self.setStyleSheet("")

    def dropEvent(self, event: QDropEvent) -> None:
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self._load_file(path)

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "",
            "Excel 文件 (*.xlsx *.xlsm);;CSV 文件 (*.csv);;所有文件 (*)",
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str) -> None:
        parent = self.parent()
        while parent and not isinstance(parent, DataCenterWidget):
            parent = parent.parent()
        if isinstance(parent, DataCenterWidget):
            parent.load_file(path)


class DataPreviewWidget(QWidget):
    """Table preview of loaded data."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header_row = QHBoxLayout()
        self.file_label = TitleLabel("未加载数据")
        self.file_label.setStyleSheet("font-size: 15px;")
        header_row.addWidget(self.file_label)
        header_row.addStretch()

        self.row_label = BodyLabel("")
        self.row_label.setStyleSheet("color: #666;")
        header_row.addWidget(self.row_label)
        layout.addLayout(header_row)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #eee;
                font-size: 12px;
            }
            QTableWidget::item:selected {
                background: #cce4ff;
                color: black;
            }
            QHeaderView::section {
                background: #f0f2f5;
                border: none;
                border-bottom: 2px solid #0078D4;
                padding: 6px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.table)

    def load_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self.file_label.setText(filename)
        n_rows, n_cols = df.shape
        self.row_label.setText(f"{n_rows} 行 x {n_cols} 列")

        self.table.clear()
        self.table.setRowCount(min(n_rows, 100))
        self.table.setColumnCount(n_cols)
        self.table.setHorizontalHeaderLabels([str(c) for c in df.columns])

        for i in range(min(n_rows, 100)):
            for j in range(n_cols):
                val = df.iloc[i, j]
                item = QTableWidgetItem(str(val) if pd.notna(val) else "")
                self.table.setItem(i, j, item)

        self.table.resizeColumnsToContents()


class DataCenterWidget(QWidget):
    """Data Center page — file loading and preview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("data_center")
        self.df: pd.DataFrame | None = None
        self.filepath: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 20)

        header = TitleLabel("数据中心")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)

        desc = BodyLabel("拖拽或选择数据文件, 自动预览并启用可用分析功能")
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        layout.addWidget(desc)

        self.drop_zone = DropZone(self)
        layout.addWidget(self.drop_zone)

        self.preview = DataPreviewWidget(self)
        layout.addWidget(self.preview, 1)

    def load_file(self, path: str) -> None:
        try:
            p = Path(path)
            suffix = p.suffix.lower()

            if suffix in (".xlsx", ".xlsm"):
                df = pd.read_excel(path, engine="openpyxl")
            elif suffix == ".csv":
                df = pd.read_csv(path)
            else:
                InfoBar.error("不支持的格式", f"不支持 {suffix} 格式, 请使用 .xlsx / .xlsm / .csv", parent=self)
                return

            self.df = df
            self.filepath = path
            self.preview.load_dataframe(df, p.name)

            InfoBar.success("加载成功", f"已加载 {p.name} ({len(df)} 行 x {len(df.columns)} 列)", parent=self, duration=2000)

            main_win = self.window()
            if hasattr(main_win, "cpk_panel"):
                main_win.cpk_panel.set_dataframe(df, p.name)
            if hasattr(main_win, "grr_panel"):
                main_win.grr_panel.set_dataframe(df, p.name)
            if hasattr(main_win, "msa_panel"):
                main_win.msa_panel.set_dataframe(df, p.name)
            if hasattr(main_win, "spc_panel"):
                main_win.spc_panel.set_dataframe(df, p.name)

        except Exception as e:
            InfoBar.error("加载失败", str(e), parent=self)
