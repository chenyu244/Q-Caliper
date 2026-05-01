# Changelog (2026-05-01)

## 核心算法重构 (Core Algorithm)
- **CPK/PPK 计算引擎**: 
  - 移除了旧版废弃的 `calculate_cpk` 接口，全面采用具有统一逻辑和三类分析模式 ("equipment", "subgrouped", "individual") 的 `calculate_capability` 新接口。
  - 重写了 `q_caliper/core/cpk.py` 中的英文注释为中文，方便国内开发者阅读。
  - **精度优化**: 在 `_d2_constant` 中，对于子组大小 $n > 10$ 的情况，舍弃了固定的保守估计 $3.0$，采用更高精度的数学公式 $d_2(n) \approx \sqrt{\frac{\pi n}{2n - 1}}$。

## 文档与排版 (Documentation & Typography)
- **Typst 技术文档修复**:
  - 修复了由于不兼容的 Markdown 表格和旧版 LaTeX 语法导致的严重编译报错。
  - 修正了由于缺少字体导致的全局文本加粗渲染异常，更换为通用的 Windows 字体组合（Times New Roman, SimSun, Microsoft YaHei, Consolas）。
  - **模板化**: 抽取了所有的 `#set` 与 `#show` 样式配置规则至 `docs/template.typ`，并在 `qcaliper_capability_guide.typ` 中进行了重构引用。

## 构建脚本优化 (Build Script)
- **Nuitka 打包精简**:
  - 修复了通过 Nuitka 编译独立 EXE 文件时图标丢失的问题，补充了 `--windows-icon-from-ico=images/Q-Caliper.ico` 参数。
  - 移除了不再必须额外打包的资源文件夹（`data/examples` 与 `images`），以及显式的 `--include-package`，结合 `--follow-imports` 大幅缩减最终产物的体积。

## 界面与 UI 调整 (User Interface)
- **图表视觉精细化**:
  - 统一遍历并修改了 `q_caliper/ui/` 目录下（CPK, MSA, SPC, GRR, DOE）所有基于 matplotlib 的绘图脚本。将过于粗重的曲线（`linewidth=2` 或 `1.5`）全部调细至 `1.2` 或 `1.0`，提升整体美感。
- **数据中心 (Data Center) 全面重构**:
  - 废弃了原本占据空间巨大的独立 `DropZone`，直接为表格 `DataPreviewWidget` 提供全局拖拽支持。
  - **前缀保护**: 导入数据时如果文件名未带 `[Q]_` 前缀，则自动在同目录下拷贝一份带前缀的工作副本，后续所有修改基于副本进行。
  - **智能清洗**: 自动识别并提取前 20 行中的有效表头行，并剔除全空的冗余数据行和列 (`dropna(how="all")`)。
  - **表头下放**: 将 Excel 的真实表头作为数据呈现于界面的第 0 行，允许直接双击编辑。原本顶部的灰色固定表头被改造为“智能角色推断”栏。