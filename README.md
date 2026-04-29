# Q-Caliper

质量工程桌面分析平台 — Minitab 精华功能的开源替代品

## 定位

Q-Caliper 是一款面向结构与质量工程师的开源桌面分析平台，旨在将 Minitab 最常用的统计分析功能以现代化、数据优先（Data-First）的交互方式重新实现，并通过 Typst 引擎自动生成专业级 PDF 分析报告。

> 让工程师直接拖拽数据文件，系统自动识别列类型并点亮可用分析按钮，最终一键生成可交付的报告文档。

## 核心功能

| 阶段 | 功能模块 | 状态 |
|------|---------|------|
| 第一阶段 MVP | Cpk/Ppk 计算、正态性检验、直方图报告 | ✅ 已完成 |
| 第二阶段 MSA | GRR ANOVA 分析、偏差分析、线性分析 | ✅ 已完成 |
| 第三阶段 SPC | XBar-R / I-MR 控制图、八大判异准则、Cpk 趋势 | ✅ 已完成 |
| 第四阶段 DOE | 全因子/部分因子设计、因子效应图、Pareto 图、Typst 报告 | ✅ 已完成 |

## 界面总览

左侧 Fluent Design 导航栏，共 7 个功能页面：

| 页面 | 功能 |
|------|------|
| **数据中心** | 拖拽/浏览加载 Excel/CSV，自动预览，数据同步到所有分析模块 |
| **Cpk 分析** | 列映射 → 正态性检验 → Cpk/Ppk 计算 → 直方图（正态拟合 + 规格限） |
| **GRR 分析** | ANOVA 法 GRR → 变异分量 → 6 图仪表板（箱线图/均值图/交互图/饼图） |
| **MSA 分析** | 偏差分析（t 检验）+ 线性分析（回归 + P/T 比） |
| **SPC 分析** | XBar-R / I-MR 控制图 + 八大判异准则自动标注 + Cpk 趋势 |
| **DOE 实验设计** | 全因子/部分因子设计矩阵 + 因子效应图 + Pareto 排序 + Excel 导出 |
| **设置** | 报告公司名/编制人配置，系统信息 |

## 技术栈

| 类别 | 组件 | 说明 |
|------|------|------|
| 核心语言 | **Python 3.12+** | 类型注解完善，Nuitka 兼容 |
| UI 框架 | **PyQt5 + PyQt-Fluent-Widgets** | Win11 Fluent Design，深/浅色主题 |
| 打包编译 | **Nuitka** | 编译为 C++ 二进制 EXE（单文件分发） |
| 报告引擎 | **typst (Python 包)** | 原生 PDF 编译，无需 CLI |
| 数据处理 | **Pandas 2.x** | Excel/CSV 读写 |
| 统计推断 | **SciPy.stats** | 正态性检验、t 检验、F 检验 |
| 建模分析 | **Statsmodels** | OLS 回归、ANOVA |
| 实验设计 | **pyDOE2** | 全因子/部分因子设计矩阵 |
| 图形渲染 | **Matplotlib** | 嵌入 Qt 的图表引擎 |

## 快速开始

### 安装运行

```bash
git clone http://hh.yuxtk.com:3030/sheldon/Q-caliper.git
cd Q-Caliper

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
python main.py
```

### 打包为 EXE

```bash
pip install -r requirements-dev.txt
python build.py
# 输出: dist/main.exe（单文件，可直接分发给同事）
```

### 开发命令

```bash
ruff check .                  # 代码检查
mypy q_caliper/               # 类型检查
pytest                        # 运行 30 个单元测试
```

## 项目结构

```
Q-Caliper/
├── main.py                          # 应用入口
├── build.py                         # Nuitka 打包脚本
├── AGENTS.md                        # 开发铁律
├── pyproject.toml                   # 项目元数据
├── requirements.txt                 # 运行依赖
├── requirements-dev.txt             # 开发依赖
├── ruff.toml / mypy.ini / pytest.ini
│
├── q_caliper/
│   ├── core/                        # 核心计算引擎（无 UI 依赖）
│   │   ├── cpk.py                   #   Cpk/Ppk + 正态性检验
│   │   ├── grr.py                   #   GRR ANOVA + 数据验证
│   │   ├── msa.py                   #   偏差分析 + 线性分析
│   │   ├── spc.py                   #   控制图 + 八大判异准则
│   │   └── doe.py                   #   全因子/部分因子设计
│   │
│   ├── ui/                          # PyQt5 + Fluent-Widgets 界面层
│   │   ├── main_window.py           #   主窗口 + 导航
│   │   ├── data_center.py           #   拖拽加载 + 数据预览
│   │   ├── cpk_panel.py             #   Cpk 分析面板 + 直方图
│   │   ├── grr_panel.py             #   GRR 面板 + 6 图仪表板
│   │   ├── msa_panel.py             #   MSA 偏差/线性面板
│   │   ├── spc_panel.py             #   SPC 控制图面板
│   │   ├── doe_panel.py             #   DOE 实验设计面板
│   │   └── settings_panel.py        #   设置面板
│   │
│   ├── reports/                     # Typst 报告引擎
│   │   ├── report_engine.py         #   PDF 生成逻辑
│   │   └── templates/               #   .typ 模板文件
│   │       ├── base_report.typ
│   │       ├── cpk_report.typ
│   │       └── grr_report.typ
│   │
│   └── tests/                       # pytest 测试套件（30 个测试）
│       ├── test_cpk.py
│       ├── test_grr.py
│       ├── test_msa.py
│       ├── test_spc.py
│       └── test_doe.py
│
├── data/examples/                   # 示例数据集
│   ├── cpk_example.xlsx
│   ├── grr_example.xlsx
│   ├── spc_example.xlsx
│   └── generate_samples.py
│
└── docs/                            # 文档
    ├── 使用说明.md
    └── 函数功能清单.md
```

## 示例数据

`data/examples/` 目录提供 3 套标准测试数据：

| 文件 | 分析模块 | 建议参数 |
|------|----------|----------|
| `cpk_example.xlsx` | Cpk 分析 | 测量列: 测量值, USL=60, LSL=40 |
| `grr_example.xlsx` | GRR 分析 | 测量列: 测量值, 操作者列: 操作者, 零件列: 零件 |
| `spc_example.xlsx` | SPC 分析 | 测量列: 测量值, USL=110, LSL=90 |

## 文档

- [使用说明](docs/使用说明.md) — 安装、各模块操作流程、FAQ
- [函数功能清单](docs/函数功能清单.md) — 核心 API、UI 类、报告引擎参考

## 许可证

[MIT License](LICENSE)
