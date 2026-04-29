# Q-Caliper

质量工程桌面分析平台

项目执行情况 v1.0

|  |  |
| --- | --- |
| **项目代号** | Q-Caliper |
| **目标用户** | 结构 / 质量工程师 |
| **核心定位** | Minitab 精华功能的开源替代品 |
| **技术栈** | Python 3.12+ · PyQt5 · PyQt-Fluent-Widgets |
| **打包方式** | Nuitka → EXE (Windows) |
| **报告引擎** | Typst (Python typst 包) |
| **当前版本** | v1.0.0 |

让结构工程师从繁琐的统计计算中解脱——一拖一拽，报告自出。

---

# 1 四阶段执行总览

| 阶段 | 目标 | 状态 | 交付物 |
|------|------|------|--------|
| 第一阶段 MVP | Cpk/Ppk 分析 + 直方图 + Excel 拖拽 | ✅ 已完成 | Cpk 引擎、正态检验、直方图、数据中心、Fluent Design 主框架 |
| 第二阶段 MSA | GRR ANOVA + 偏差/线性分析 | ✅ 已完成 | GRR 引擎 + 6 图仪表板、MSA 偏差/线性分析、数据验证层 |
| 第三阶段 SPC | 控制图 + 判异 + Cpk 趋势 | ✅ 已完成 | XBar-R/I-MR 控制图、八大判异准则、过程能力趋势 |
| 第四阶段 DOE | 实验设计 + 报告引擎 + 发布 | ✅ 已完成 | DOE 设计矩阵、因子效应/Pareto 图、Typst PDF 报告、设置面板 |

---

# 2 各阶段完成明细

## 2.1 第一阶段 MVP · Cpk

| 功能模块 | 优先级 | 状态 | 实际交付 |
|----------|--------|------|----------|
| Excel 读取器 (.xlsx/.csv 拖拽) | P0 | ✅ | `data_center.py` — 拖拽/浏览加载，自动预览 100 行 |
| 列映射面板 (测量列/USL/LSL) | P0 | ✅ | `cpk_panel.py` — 下拉框选择 + 双精度规格限输入 |
| 正态性检验 | P0 | ✅ | `core/cpk.py` — Shapiro-Wilk / Anderson-Darling |
| Cpk/Ppk 引擎 | P0 | ✅ | `core/cpk.py` — Cp/Cpk/Pp/Ppk + 组内/组间标准差 |
| 直方图输出 | P0 | ✅ | `cpk_panel.py` — 正态拟合 + USL/LSL 红线 + Cpk 标注 |
| 主界面框架 | P0 | ✅ | `main_window.py` — FluentWindow + 侧边栏导航 |
| Nuitka 打包脚本 | P0 | ✅ | `build.py` — pyqt5 插件 + include-data-dir |
| 单元测试 | P1 | ✅ | `tests/test_cpk.py` — 6 个测试 |

## 2.2 第二阶段 MSA · GRR

| 功能模块 | 优先级 | 状态 | 实际交付 |
|----------|--------|------|----------|
| GRR ANOVA 法 | P0 | ✅ | `core/grr.py` — 完整 ANOVA 表 + 方差分量 + ndc |
| GRR 仪表板 (6 图) | P0 | ✅ | `grr_panel.py` — 箱线图/均值图/交互图/饼图 |
| MSA 偏差分析 | P1 | ✅ | `core/msa.py` — 单样本 t 检验 + 置信区间 |
| MSA 线性分析 | P1 | ✅ | `core/msa.py` — 线性回归 + R² + P/T 比 |
| 数据验证层 | P0 | ✅ | `core/grr.py` — validate_grr_data() |
| MSA 基础报告 | P1 | ✅ | Typst GRR 模板 (`grr_report.typ`) |

## 2.3 第三阶段 SPC

| 功能模块 | 优先级 | 状态 | 实际交付 |
|----------|--------|------|----------|
| XBar-R 控制图 | P0 | ✅ | `core/spc.py` + `spc_panel.py` — UCL/CL/LCL + 区域着色 |
| I-MR 控制图 | P0 | ✅ | `core/spc.py` + `spc_panel.py` — 个体值 + 移动极差 |
| 八大判异准则 | P0 | ✅ | `core/spc.py` — 8 条 Western Electric 规则自动检测 |
| 过程能力趋势 | P1 | ✅ | `spc_panel.py` — 5 段 Cpk 柱状图 |
| SPC 报告模板 | P1 | ⬜ | 未创建独立 SPC Typst 模板（低优先级） |

## 2.4 第四阶段 DOE + 报告

| 功能模块 | 优先级 | 状态 | 实际交付 |
|----------|--------|------|----------|
| DOE 设计生成器 | P0 | ✅ | `core/doe.py` + `doe_panel.py` — 全因子/部分因子 |
| 因子效应图 | P1 | ✅ | `doe_panel.py` — OLS 回归主效应图 |
| Pareto 效应排序 | P1 | ✅ | `doe_panel.py` — |效应| 降序 + alpha=0.05 显著线 |
| Typst 报告引擎 | P0 | ✅ | `reports/report_engine.py` — Python typst 包原生编译 |
| 设置面板 | P1 | ✅ | `settings_panel.py` — 公司名/编制人/系统信息 |
| 帮助文档与示例数据 | P1 | ✅ | `docs/` 使用说明 + 函数清单；`data/examples/` 3 套数据 |
| v1.0 发布准备 | P0 | ⬜ | CHANGELOG 未创建；Git Tag 未打 |

---

# 3 技术栈实际选型（与原始计划差异）

| 项目 | 原计划 | 实际选型 | 原因 |
|------|--------|----------|------|
| UI 框架 | PySide6 | **PyQt5** | PyQt-Fluent-Widgets 依赖 PyQt5 |
| Python 版本 | 3.14+ | **3.12+** | 3.14 尚未正式发布 |
| Typst 集成 | CLI subprocess | **Python typst 包** | 原生 API 更简洁，无需外部二进制 |
| GRR 实现 | PyGRR 库 | **自研 ANOVA** | 更可控，无额外依赖 |
| 报告模板 | 待设计 | **3 个 .typ 模板** | base/cpk/grr |

---

# 4 测试覆盖

| 测试文件 | 测试数 | 覆盖模块 |
|----------|--------|----------|
| test_cpk.py | 6 | normality_test, calculate_cpk |
| test_grr.py | 8 | validate_grr_data, calculate_grr (含 ANOVA 表/图表数据) |
| test_msa.py | 6 | analyze_bias, analyze_linearity |
| test_spc.py | 4 | xbar_r_chart, imr_chart, detect_violations |
| test_doe.py | 6 | full_factorial, fractional_factorial |
| **合计** | **30** | |

---

# 5 剩余待办事项

## 5.1 发布相关（建议优先处理）

| 事项 | 优先级 | 说明 |
|------|--------|------|
| 创建 CHANGELOG.md | 中 | 记录四个阶段的功能变更 |
| 打 Git Tag v1.0.0 | 中 | `git tag v1.0.0 && git push --tags` |
| Nuitka 实际编译测试 | 中 | 运行 `python build.py` 验证 EXE 可用 |
| GitHub Actions CI 更新 | 低 | ci.yml 中 pyqt5 插件配置需同步 |

## 5.2 功能增强（后续迭代）

| 事项 | 优先级 | 说明 |
|------|--------|------|
| SPC 报告模板 | 低 | 创建 spc_report.typ |
| DOE 报告模板 | 低 | 创建 doe_report.typ |
| 深色主题适配 | 低 | 当前仅浅色主题 |
| 中/英文语言切换 | 低 | 设置面板中预留 |
| 多 Sheet 支持 | 低 | Excel 多 Sheet 选择 |
| 图表 PNG 导出按钮 | 低 | 各面板图表独立导出 |
| pytest-qt UI 测试 | 低 | 关键路径自动化测试 |

---

# 6 风险回顾

| 原始风险 | 实际情况 |
|----------|----------|
| PyGRR 文档不完整 | ✅ 已规避 — 改用自研 ANOVA 实现 |
| Nuitka 与 PySide6 冲突 | ✅ 已规避 — 切换为 PyQt5 |
| Fluent-Widgets 版本变更 | ✅ 已锁定版本 1.11.2 |
| Typst CLI 嵌入增大体积 | ✅ 已规避 — 使用 Python typst 包 |
| 单人维护瓶颈 | ⚠️ 持续风险 — 严格控制范围 |
