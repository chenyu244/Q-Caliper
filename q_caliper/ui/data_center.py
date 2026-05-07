"""Data Center — drag-drop Excel loading and data preview."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
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
    MessageBox,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    TitleLabel,
)


class DataPreviewWidget(QWidget):
    """Table preview of loaded data with drag-and-drop support."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._full_df: pd.DataFrame | None = None
        self._loading = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header_row = QHBoxLayout()
        self.file_label = TitleLabel("未加载数据 (可将 Excel 拖拽至此)")
        self.file_label.setStyleSheet("font-size: 15px;")
        header_row.addWidget(self.file_label)
        
        self.browse_btn = PushButton("浏览文件")
        self.browse_btn.setIcon(FluentIcon.FOLDER)
        self.browse_btn.clicked.connect(self._browse_file)
        header_row.addWidget(self.browse_btn)

        self.sync_btn = PushButton("同步修改")
        self.sync_btn.setIcon(FluentIcon.SYNC)
        self.sync_btn.clicked.connect(self._sync_file)
        self.sync_btn.hide() # Hidden until data is loaded
        header_row.addWidget(self.sync_btn)

        self.smart_btn = PrimaryPushButton("分析推荐")
        self.smart_btn.setIcon(FluentIcon.INFO)
        self.smart_btn.clicked.connect(self._goto_analysis)
        self.smart_btn.hide() # Hidden until data is loaded
        header_row.addWidget(self.smart_btn)

        header_row.addStretch()

        self.time_label = BodyLabel("")
        self.time_label.setStyleSheet("color: #0078D4; margin-right: 15px;")
        header_row.addWidget(self.time_label)

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
                border: 2px dashed #ccc;
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
        
        # 信号连接
        self.table.horizontalHeader().sectionDoubleClicked.connect(self._edit_header)
        self.table.itemChanged.connect(self._on_item_changed)
        
        layout.addWidget(self.table)

    def set_sync_time(self, time_dt: datetime | None = None) -> None:
        if time_dt:
            self.time_label.setText(f"同步时间: {time_dt.strftime('%H:%M:%S')}")
        else:
            self.time_label.setText("")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.table.setStyleSheet(self.table.styleSheet().replace("border: 2px dashed #ccc;", "border: 2px dashed #0078D4; background: #f0f8ff;"))

    def dragLeaveEvent(self, event) -> None:
        self.table.setStyleSheet(self.table.styleSheet().replace("border: 2px dashed #0078D4; background: #f0f8ff;", "border: 2px dashed #ccc;"))

    def dropEvent(self, event: QDropEvent) -> None:
        self.table.setStyleSheet(self.table.styleSheet().replace("border: 2px dashed #0078D4; background: #f0f8ff;", "border: 2px dashed #ccc;"))
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
        while parent and not hasattr(parent, "load_file"):
            parent = parent.parent()
        if hasattr(parent, "load_file"):
            parent.load_file(path)

    def _edit_header(self, logical_index: int) -> None:
        if self.table.columnCount() == 0:
            return
        
        item = self.table.horizontalHeaderItem(logical_index)
        current_role = item.text() if item else "未分类"
        
        roles = ["测量值", "操作者", "零件", "时间", "因子", "未分类"]
        new_role, ok = QInputDialog.getItem(
            self, "修改数据角色", "请选择该列的数据角色:", roles, 
            current=roles.index(current_role) if current_role in roles else 5,
            editable=False
        )
        
        if ok and new_role:
            if item:
                item.setText(new_role)
            else:
                self.table.setHorizontalHeaderItem(logical_index, QTableWidgetItem(new_role))
            
            # 修改角色只同步状态，静默处理
            self._sync_file(silent=True)
            self._update_smart_btn()
            InfoBar.success("角色已更新", f"列 {logical_index} 的角色已更新为 '{new_role}'", parent=self, duration=2000)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading or self._full_df is None:
            return
            
        row = item.row()
        col = item.column()
        val = item.text()
        
        # 暂时关闭信号避免递归
        self.table.blockSignals(True)
        
        try:
            if row == 0:
                # 修改列名
                new_cols = list(self._full_df.columns)
                new_cols[col] = val
                self._full_df.columns = new_cols
                
                # 加粗显示列名
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            else:
                # 修改数据 (行索引在表格中 offset 了 1)
                # 尝试类型转换
                try:
                    if not val:
                        converted_val = None
                    elif "." in val:
                        converted_val = float(val)
                    else:
                        converted_val = int(val)
                except ValueError:
                    converted_val = val
                
                self._full_df.iloc[row - 1, col] = converted_val
                
            # 自动保存应该静默进行，避免频繁弹窗干扰用户
            self._sync_file(silent=True)
        except Exception as e:
            InfoBar.error("数据更新失败", str(e), parent=self)
        finally:
            self.table.blockSignals(False)

    def _sync_file(self, silent: bool = False) -> None:
        if self._full_df is None:
            return
            
        parent = self.parent()
        while parent and not hasattr(parent, "sync_file"):
            parent = parent.parent()
        if hasattr(parent, "sync_file"):
            parent.sync_file(self._full_df, silent=silent)

    def _get_current_dataframe(self) -> pd.DataFrame:
        """Constructs a DataFrame from the current QTableWidget contents. Row 0 contains column names.
        DEPRECATED: Now uses self._full_df directly to avoid truncation.
        """
        return self._full_df if self._full_df is not None else pd.DataFrame()

    def _goto_analysis(self) -> None:
        mapping = self.get_role_mapping()
        main_win = self.window()
        
        target_panel = None
        if all(r in mapping for r in ["测量值", "操作者", "零件"]):
            target_panel = getattr(main_win, "grr_panel", None)
        elif "测量值" in mapping:
            target_panel = getattr(main_win, "cpk_panel", None)
        
        if target_panel and hasattr(main_win, "switchTo"):
            if hasattr(target_panel, "set_selected_columns"):
                target_panel.set_selected_columns(mapping)
            main_win.switchTo(target_panel)
        else:
            InfoBar.warning("分析推荐", "请先通过双击表头为列分配角色（如：测量值、零件、操作者）", parent=self)

    def get_role_mapping(self) -> dict[str, list[str]]:
        """Extract mapping of roles to column names from the table."""
        mapping = {}
        for j in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(j)
            if not header_item:
                continue
            role = header_item.text()
            # The actual column name is in the 0-th row of the table
            col_item = self.table.item(0, j)
            if not col_item:
                continue
            col_name = col_item.text()
            if role not in mapping:
                mapping[role] = []
            mapping[role].append(col_name)
        return mapping

    def _update_smart_btn(self) -> None:
        """Update smart analysis button text based on current roles."""
        mapping = self.get_role_mapping()
        if all(r in mapping for r in ["测量值", "操作者", "零件"]):
            self.smart_btn.setText("智能推荐: GRR")
            self.smart_btn.setIcon(FluentIcon.MARKET)
        elif "测量值" in mapping:
            self.smart_btn.setText("智能推荐: 正态分析")
            self.smart_btn.setIcon(FluentIcon.CARE_RIGHT_SOLID)
        else:
            self.smart_btn.setText("分析推荐")
            self.smart_btn.setIcon(FluentIcon.INFO)

    def load_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        self._loading = True
        self.table.blockSignals(True)
        self._full_df = df.copy() # 保存全量数据副本
        
        self.file_label.setText(filename)
        n_rows, n_cols = df.shape
        self.row_label.setText(f"{n_rows} 行 x {n_cols} 列")

        self.table.clear()
        
        # 智能推断数据角色
        roles = []
        for col in df.columns:
            col_str = str(col).lower()
            if any(k in col_str for k in ("人", "操作", "检验员", "operator", "appraiser")):
                roles.append("操作者")
            elif any(k in col_str for k in ("零件", "产品", "part", "item", "产品号")):
                roles.append("零件")
            elif any(k in col_str for k in ("测量", "值", "value", "data", "数据", "结果")):
                roles.append("测量值")
            elif any(k in col_str for k in ("日期", "时间", "date", "time")):
                roles.append("时间")
            elif any(k in col_str for k in ("因子", "factor", "条件")):
                roles.append("因子")
            else:
                roles.append("未分类")
                
        max_preview_rows = min(n_rows, 100)
        self.table.setRowCount(max_preview_rows + 1)
        self.table.setColumnCount(n_cols)
        self.table.setHorizontalHeaderLabels(roles)

        # 第 0 行放置真实表头
        for j in range(n_cols):
            item = QTableWidgetItem(str(df.columns[j]))
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setBackground(Qt.GlobalColor.lightGray)
            self.table.setItem(0, j, item)

        # 第 1 行起放置真实数据
        for i in range(max_preview_rows):
            for j in range(n_cols):
                val = df.iloc[i, j]
                item = QTableWidgetItem(str(val) if pd.notna(val) else "")
                self.table.setItem(i + 1, j, item)

        self.table.resizeColumnsToContents()
        self.table.blockSignals(False)
        self._loading = False
        self.sync_btn.show()
        self.smart_btn.show()
        self._update_smart_btn()



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

        self.preview = DataPreviewWidget(self)
        layout.addWidget(self.preview, 1)

    def load_file(self, path: str) -> None:
        try:
            p = Path(path)
            suffix = p.suffix.lower()

            if suffix not in (".xlsx", ".xlsm", ".csv"):
                InfoBar.error("不支持的格式", f"不支持 {suffix} 格式, 请使用 .xlsx / .xlsm / .csv", parent=self)
                return

            target_path = p
            if not p.name.startswith("[Q]_"):
                target_name = f"[Q]_{p.name}"
                target_path = p.with_name(target_name)
                
                if target_path.exists():
                    title = "发现已存在的分析副本"
                    content = f"文件夹中已存在分析副本 '{target_path.name}'。\n是否用当前选中的源文件覆盖它？(注意：覆盖后将丢失之前在副本中的所有修改)"
                    w = MessageBox(title, content, self)
                    w.yesButton.setText("覆盖")
                    w.cancelButton.setText("取消")
                    if not w.exec():
                        return # 用户取消
                
                # 无论是新生成还是确认覆盖，都进行拷贝
                shutil.copy2(path, target_path)

            df = self._smart_read_and_clean(target_path)
            if df is None:
                return

            self.df = df
            self.filepath = str(target_path)
            self.preview.load_dataframe(df, target_path.name)
            self.preview.set_sync_time(datetime.now())

            # Record timestamp for future sync
            self._last_modified_time = os.path.getmtime(self.filepath)

            InfoBar.success("加载成功", f"已加载 {target_path.name} ({len(df)} 行 x {len(df.columns)} 列)", parent=self, duration=2000)

            main_win = self.window()
            if hasattr(main_win, "cpk_panel"):
                main_win.cpk_panel.set_dataframe(df, target_path.name)
            if hasattr(main_win, "grr_panel"):
                main_win.grr_panel.set_dataframe(df, target_path.name)
            if hasattr(main_win, "msa_panel"):
                main_win.msa_panel.set_dataframe(df, target_path.name)
            if hasattr(main_win, "spc_panel"):
                main_win.spc_panel.set_dataframe(df, target_path.name)
            if hasattr(main_win, "doe_panel"):
                main_win.doe_panel.set_dataframe(df, target_path.name)

        except Exception as e:
            InfoBar.error("加载失败", str(e), parent=self)

    def sync_file(self, current_df: pd.DataFrame, silent: bool = False) -> None:
        if not self.filepath:
            return

        try:
            current_mtime = os.path.getmtime(self.filepath)
            
            # Check for external modification (with 1 second tolerance)
            if hasattr(self, "_last_modified_time") and current_mtime > self._last_modified_time + 1:
                title = "检测到外部修改"
                content = "文件在外部被修改，是否重新加载外部内容？（选择否将用当前界面内容覆盖外部文件）"
                w = MessageBox(title, content, self)
                w.yesButton.setText("重新加载")
                w.cancelButton.setText("覆盖")
                if w.exec():
                    self.load_file(self.filepath)
                    return

            # Overwrite external file with current UI data
            suffix = Path(self.filepath).suffix.lower()
            if suffix == ".csv":
                current_df.to_csv(self.filepath, index=False)
            else:
                current_df.to_excel(self.filepath, engine="openpyxl", index=False)
            
            self.df = current_df
            self._last_modified_time = os.path.getmtime(self.filepath)
            
            # Update other panels
            main_win = self.window()
            if hasattr(main_win, "cpk_panel"):
                main_win.cpk_panel.set_dataframe(current_df, Path(self.filepath).name)
            if hasattr(main_win, "grr_panel"):
                main_win.grr_panel.set_dataframe(current_df, Path(self.filepath).name)
            if hasattr(main_win, "msa_panel"):
                main_win.msa_panel.set_dataframe(current_df, Path(self.filepath).name)
            if hasattr(main_win, "spc_panel"):
                main_win.spc_panel.set_dataframe(current_df, Path(self.filepath).name)
            if hasattr(main_win, "doe_panel"):
                main_win.doe_panel.set_dataframe(current_df, Path(self.filepath).name)

            self.preview.set_sync_time(datetime.now())

            if not silent:
                InfoBar.success("同步成功", "界面修改已保存至文件并更新所有分析模块", parent=self, duration=2000)
            
        except Exception as e:
            InfoBar.error("同步失败", str(e), parent=self)

    def _smart_read_and_clean(self, file_path: Path) -> pd.DataFrame | None:
        """Smartly detects header within first 20 rows and drops all-NaN rows/cols."""
        try:
            suffix = file_path.suffix.lower()
            if suffix == ".csv":
                raw_df = pd.read_csv(file_path, header=None, nrows=20)
            else:
                raw_df = pd.read_excel(file_path, engine="openpyxl", header=None, nrows=20)

            # Find the row with the maximum number of non-null values to be the header
            best_header_idx = 0
            max_non_nulls = 0
            for i in range(len(raw_df)):
                non_null_count = raw_df.iloc[i].count()
                if non_null_count > max_non_nulls:
                    max_non_nulls = non_null_count
                    best_header_idx = i

            if max_non_nulls == 0:
                InfoBar.warning("未能识别有效数据", "在前 20 行中没有找到任何有效的表头或数据。", parent=self)
                return None

            # Read full dataframe with the detected header
            if suffix == ".csv":
                df = pd.read_csv(file_path, header=best_header_idx)
            else:
                df = pd.read_excel(file_path, engine="openpyxl", header=best_header_idx)

            # Clean empty rows and columns
            df = df.dropna(how="all", axis=0)
            df = df.dropna(how="all", axis=1)
            
            # Save the cleaned dataframe back to the [Q]_ file
            if suffix == ".csv":
                df.to_csv(file_path, index=False)
            else:
                df.to_excel(file_path, engine="openpyxl", index=False)

            return df
        except Exception as e:
            InfoBar.error("数据清洗失败", f"无法自动识别表头或清洗数据: {str(e)}", parent=self)
            return None

