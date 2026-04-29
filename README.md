# Q-Caliper

质量工程桌面分析平台 — Minitab 精华功能的开源替代品

## 定位

Q-Caliper 是一款面向结构与质量工程师的开源桌面分析平台，旨在将 Minitab 最常用的统计分析功能以现代化、数据优先（Data-First）的交互方式重新实现，并通过 Typst 引擎自动生成专业级 PDF 分析报告。

## 核心功能（路线图）

| 阶段 | 功能模块 | 状态 |
|------|---------|------|
| 第一阶段 MVP | Cpk/Ppk 计算、正态性检验、直方图报告 | 🚧 进行中 |
| 第二阶段 MSA | GRR ANOVA 分析、线性分析、偏差分析 | 📋 计划中 |
| 第三阶段 SPC | XBar-R / I-MR 控制图、八大判异准则 | 📋 计划中 |
| 第四阶段 DOE | 全因子设计、因子效应图、Pareto 图 | 📋 计划中 |

## 技术栈

- **Python 3.12+** — 核心语言
- **PySide6 (Qt 6.x)** — UI 框架
- **PyQt-Fluent-Widgets** — Win11 Fluent Design 皮肤
- **Nuitka** — 编译为 C++ 二进制 EXE
- **Typst CLI** — PDF 报告引擎
- **Pandas / SciPy / Statsmodels** — 数据处理与统计分析
- **Matplotlib** — 图表渲染

## 快速开始

### 安装

```bash
# 克隆仓库
git clone http://hh.yuxtk.com:3030/sheldon/Q-caliper.git
cd Q-caliper

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 代码检查
ruff check .

# 类型检查
mypy q_caliper/

# 运行测试
pytest
```

## 项目结构

```
q_caliper/
├── core/           # 核心计算引擎（无 UI 依赖）
│   ├── cpk.py      # Cpk/Ppk 计算
│   ├── grr.py      # GRR ANOVA 法
│   ├── spc.py      # 控制图与判异规则
│   └── doe.py      # DOE 设计矩阵生成
├── ui/             # PySide6 界面层
│   ├── main_window.py
│   ├── cpk_panel.py
│   ├── grr_panel.py
│   └── spc_panel.py
├── charts/         # 图表渲染层
├── reports/        # Typst 模板与 PDF 生成
│   └── templates/  # .typ 模板文件
├── tests/          # pytest 测试套件
├── build/          # Nuitka 打包脚本
└── main.py         # 应用入口点
```

## 许可证

[MIT License](LICENSE)
