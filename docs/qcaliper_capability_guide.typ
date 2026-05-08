#import "template.typ": project

#show: project.with(
  title: "Q-Caliper: 过程能力分析算法深度指南",
  subtitle: "完整涵盖 Cmk, Cpk, Ppk 的计算逻辑、算法实现与工程决策",
)

== 1. 核心指标定义

在 Q-Caliper 引擎中，我们根据*波动的时间来源与测量序列特征*将过程能力指数划分为三个层次：

#table(
  columns: (1fr, 1.5fr, 4fr),
  inset: 10pt,
  align: (left, left, left),
  stroke: 0.5pt + gray,
  [*指标*], [*标准名称*], [*核心含义与应用*],
  [$C_"mk"$], [设备能力指数], [
    *"设备底子"*。在极短时间内（几分钟内）连续产出的样本，完全不考虑时间漂移因素。反映设备机械精度与重复性。\
    _应用场景_：FAT/SAT 验收、设备调试、硬件精度确认。
  ],
  [$C_"pk"$], [过程能力指数], [
    *"过程潜力"*。利用有理子组（rational subgroups）内的极差估算短期波动，隔离长期漂移。\
    _含义_：假设过程稳定，机器能达到的最好指标。\
    _应用场景_：IATF 16949 标准评估、同一条生产线的能力基准。
  ],
  [$P_"pk"$], [过程性能指数], [
    *"实际表现"*。基于全样本标准差，包含所有真实的波动（温度漂移、刀具磨损、换班变化等）。\
    _含义_：客户实际收到的产品质量体现。\
    _应用场景_：长期质量评估、交付质量承诺。
  ]
)

#v(1em)

=== 1.1 三个指标的数学关系

设有 $n$ 个观测值 $x_1, x_2, ..., x_n$，分组大小为 $m$：

- *Cmk 与 Cpk 的关系*：
  - Cmk 不考虑子组分割，而 Cpk 使用子组内极差的 $d_2$ 变换。
  - 通常 $C_"mk" <= C_"pk"$（因为忽视了部分时间变异）。

- *Cpk 与 Ppk 的关系*：
  $ C_"pk" = min(("USL" - macron(x)) / (3 sigma_"within"), (macron(x) - "LSL") / (3 sigma_"within")) $
  $ P_"pk" = min(("USL" - macron(x)) / (3 sigma_"overall"), (macron(x) - "LSL") / (3 sigma_"overall")) $
  
  其中 $sigma_"within"$ 由子组极差估算，$sigma_"overall"$ 为全样本标准差。
  
  关键观察：如果 $C_"pk" approx P_"pk"$，过程稳定；如果 $C_"pk" > P_"pk"$，存在*过程漂移*。

---

== 2. 算法核心：三种变异分离方法

=== 2.1 方法 A：Xbar-R（有理子组）

*适用条件*：数据可以按时间或逻辑分组（如：每小时采集5件，共12小时）。

*算法步骤*：

1. 将 $n$ 个数据分为 $k$ 个子组，每组大小 $m$。
2. 计算每个子组的极差：$ R_i = max(x_i) - min(x_i) $
3. 平均极差：$ macron(R) = 1/k sum_(i=1)^k R_i $
4. 短期标准差：$ sigma_"within" = macron(R) / d_2(m) $

*用途*：用于 *Cpk* 计算（过程能力，短期）

*d₂ 常数表*（用于极差→标准差转换）：

#align(center)[
  #table(
    columns: (1.5fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    inset: 6pt,
    align: center,
    fill: luma(240),
    [$m$], [2], [3], [4], [5], [6], [7], [8], [9], [10],
    [$d_2$], [1.128], [1.693], [2.059], [2.326], [2.534], [2.704], [2.847], [2.970], [3.078],
  )
]

*Q-Caliper 实现*：
```python
subgroups = data.reshape(-1, subgroup_size)
ranges = np.ptp(subgroups, axis=1)
d2 = _d2_constant(subgroup_size)
sigma_within = np.mean(ranges) / d2
```

---

=== 2.2 方法 B：I-MR（个体移动极差）

*适用条件*：
- 数据无法按逻辑分组（生产过程连续，无明显批次边界）
- 使用 `subgroup_size=1` 或未指定（默认为 1）时自动启用

*算法步骤*：

1. 计算相邻观测值的移动极差：$"MR"_i = |x_(i+1) - x_i|$ （共 $n-1$ 个值）
2. 平均移动极差：$ overline("MR") = 1/(n-1) sum_(i=1)^(n-1) "MR"_i $
3. 短期标准差：$ sigma_"within" = overline("MR") / d_2(2) = overline("MR") / 1.128 $

*用途*：用于 *Cpk* 计算（当 subgroup_size=1 时，基于移动极差估算短期波动）

*行业标准*：该方法（基于 $overline("MR")$ 估算 $sigma$）是 Minitab、AIAG SPC 手册以及 IATF 16949 在处理单值数据时的默认标准算法，具有极高的行业认可度。

*Q-Caliper 实现*：
```python
moving_ranges = np.abs(np.diff(data))
d2_mr = 1.128
sigma_within = np.mean(moving_ranges) / d2_mr
```

---

=== 2.3 方法 C：全样本标准差（用于 Cmk 和 Ppk）

*适用条件*：
- *计算 Cmk*：推荐采集 50-100 个连续样品（单机调试，不分组）
- *计算 Ppk*：全量长期数据（包含所有时间漂移，不考虑s子组分割）
- Q-Caliper 默认自动计算并在结果中返回 `cmk` 和 `ppk`

*算法步骤*：

1. 采集数据，*不进行任何子组分割*
2. 计算全样本标准差：$ sigma = s = sqrt(sum(x_i - macron(x))^2 / (n-1)) $
3. 计算公式：
   $ C_"mk" / P_"pk" = min(("USL" - macron(x)) / (3s), (macron(x) - "LSL") / (3s)) $

*关键差异*：
- *Cmk* 侧重于评估设备在极短时间内的硬件重复精度
- *Ppk* 侧重于评估过程在长期（含多种环境变异）下的实际表现
- 两者均使用全样本标准差，但*数据采集的时间跨度与背景逻辑*完全不同

*Q-Caliper 实现*：
```python
# Cmk 总是伴随计算并返回，无需专门指定模式
sigma_overall = np.std(data, ddof=1)
cmk = min((usl - mean) / (3*sigma_overall), (mean - lsl) / (3*sigma_overall))
```

*汽车标准对应*：
- 博世标准 (Booklet No. 9)：n=50（更好 n=100）
- QS-9000：Cmk = (USL-LSL)/(6*s)，s=50个数据标准差
- IATF 16949：参考 Cmk ≥ 1.67（设备能力要求）
- AIAG & VDA 2026：逐步用 Pm/Pmk 替代 Cm/Cmk

---

== 3. 数据采样与参数策略

=== 3.1 关键决策矩阵

针对不同数据量与应用场景，Q-Caliper 推荐以下配置以获得最佳诊断效果：

#align(center)[
  #table(
    columns: (1.8fr, 1.5fr, 1.2fr, 3fr),
    inset: 10pt,
    fill: (x, y) => if y == 0 { luma(200) } else if calc.rem(y, 2) == 0 { luma(245) } else { white },
    stroke: 0.5pt,
    [*应用场景*], [*推荐样本数*], [*子组大小*], [*目的与诊断*],
    
    [设备 FAT/SAT\
    （单机验收）], [50-100], [/], 
    [硬件精度验证。无足够样本来检测漂移，不做子组分析。],
    
    [常规生产验证\
    （质检抽样）], [30-50], [5], 
    [对比 Cpk ≈ Ppk 判断过程稳定性。6 个子组足以捕捉小时级漂移。],
    
    [正式 IATF 评估\
    （过程能力）], [60-100], [4-5], 
    [符合汽车工业标准。稳定的子组内外变异分离，Cpk ≥ 1.33 为合格。],
    
    [长期质量监控\
    （SPC）], [>200], [5], 
    [建立控制图。分批计算 Cpk（每批 n=5），观察 Cpk 趋势诊断过程漂移。],
  )
]


---

=== 3.2 采样策略原则

*原则 1：合理子组的时间含义*
- 子组内的样本应在短时间内（同一工艺条件下）产生。
- 子组间应包含足够的时间差（可能发生漂移的机会）。
- 例：加工中心每 10 分钟采 5 件为一个子组，共 12 组 → 2 小时内评估过程。

*原则 2：当一次性取 30 件时，仍然推荐子组n=5*

即便 30 个数据是*连续产出、物理上不分组*的，也应该"人为分组"为 6 个子组（每组 5 件）：
- 这样可以用极差法估算 $sigma_"within"$，而不是直接用全样本标准差。
- 极差法更*稳健*（对异常值敏感度低）。
- 最重要的是：可以对比 Cpk 与 Ppk，*诊断 30 件内是否有渐进式漂移*。

例：
- Cpk = 1.80, Ppk = 1.45 → 数据内部存在漂移（前 15 件可能偏高，后 15 件偏低）
- Cpk ≈ Ppk = 1.50 → 分布均匀，短期能力就是长期表现

*原则 3：当使用单值数据 ($n=1$) 时*
- 适用于*无法逻辑分组*（如连续流、化工参数、自动化单件生产）或*样本量极少*的场景。
- I-MR 方法通过移动极差估算 $sigma_"within"$。虽然 $C_"pk"$ 仍可用于对比 $P_"pk"$ 诊断漂移，但对微小漂移的敏感度低于有理子组法。
- 此时应优先结合 *I-MR 控制图* 来观察点与点之间的稳定性。

---

== 4. 诊断决策树

=== 4.1 通过 Cpk vs Ppk 对比诊断

*前提*：已计算获得 $sigma_"within"$（无论是通过子组极差还是移动极差）。

#table(
  columns: (1.8fr, 1.8fr, 3fr),
  inset: 10pt,
  fill: luma(250),
  stroke: 0.5pt,
  [*结果模式*], [*对比关系*], [*诊断与对策*],
  
  [过程稳定], 
  [$C_"pk" approx P_"pk"$\
  （差值 < 0.1）],
  [✓ 过程无明显漂移。机器稳定，短期能力 = 长期表现。\
  *对策*：维持现状，例行监控。],
  
  [过程漂移], 
  [$C_"pk" >> P_"pk"$\
  （差值 ≥ 0.2）],
  [⚠ 机器精度足够（Cpk 好），但*过程不稳定*（Ppk 差）。\
  *原因*：热变形、刀具磨损、气压波动、夹持松动。\
  *对策*：不调整机器精度，改善工艺参数稳定性（温度控制、定时刀具更换、环境隔离）。],
  
  [能力不足], 
  [Cpk < 1.33 且\
  Ppk < 1.33],
  [✗ 机器或工艺底子不够。\
  *对策*：升级设备、改进工艺方法、或提高工人技能。],
  
  [均匀不良], 
  [Cpk ≈ Ppk\
  均低（$<1.0$）],
  [✗ 机器精度与工艺方法都有问题，且无特殊漂移。\
  *对策*：全面诊断，设备检修 + 工艺优化。],
)

---

=== 4.2 个体数据（subgroup_size=1）的诊断

当使用 I-MR 方法时，虽然 $C_"pk"$ 与 $P_"pk"$ 在无波动场景下较为接近，但若数据存在缓慢趋势，两者差值依然具有诊断意义。此时应结合以下手段：

1. *直方图 + 正态性检验* -> 数据分布是否符合规格
2. *I-MR 控制图* -> 是否有超出控制限的点（表示特异波动）
3. *Ppk 绝对值* -> 判断能力等级

#table(
  columns: (1fr, 1.2fr, 3fr),
  inset: 10pt,
  fill: (x, y) => if y == 0 { luma(230) } else { white },
  stroke: 0.5pt,
  [*Ppk 范围*], [*能力等级*], [*备注*],
  [≥ 1.67], [优], [较少不良品（DPMO < 50）],
  [1.33 - 1.67], [良好], [符合 IATF 标准],
  [1.00 - 1.33], [合格], [允许但需改进],
  [< 1.00], [不合格], [需要立即改善],
)

---

== 5. API 调用指南与代码示例

=== 5.1 核心调用逻辑：智能自动化

Q-Caliper 推荐使用默认的智能模式。无论何种场景，引擎都会一次性计算并返回所有指标，差异仅在于你如何解读它们。

*推荐调用方式 (全能模式)*

```python
from qcaliper_cpk import calculate_capability

# 只需提供数据和规格限，引擎会自动处理一切
result = calculate_capability(
    data=data,
    usl=100.5,
    lsl=99.5,
    subgroup_size=5  # 指定子组大小以启用变异分离诊断
)

# 一次性获取所有指标进行对比
print(f"Cpk (短期潜力): {result.cpk:.3f}")
print(f"Ppk (长期性能): {result.ppk:.3f}")
print(f"Cmk (设备能力): {result.cmk:.3f}")
print(f"分析模式: {result.analysis_mode}")  # cpk_grouped 或 cpk_individual
```

---

*解读指南*

1. *验收设备*：关注 `result.cmk`。推荐连续 50 个样品的 Cmk ≥ 1.67。
2. *评估过程*：对比 `result.cpk` 与 `result.ppk`。如果差值大，则过程不稳定。
3. *单值数据*：不设置 `subgroup_size`，此时 `result.cpk` 基于移动极差 (I-MR) 计算。

---

=== 5.2 完整工程示例

```python
import numpy as np
from scipy import stats
from qcaliper_cpk import calculate_capability, normality_test

# 模拟加工数据（正态分布，均值 100.1，标准差 0.3）
np.random.seed(42)
data = np.random.normal(100.1, 0.3, 50)

# 第 1 步：正态性检验
norm_result = normality_test(data)
print(f"正态性测试: {norm_result.test_name}")
print(f"p-value: {norm_result.p_value:.4f}")
print(f"通过检验: {'是' if norm_result.is_normal else '否'}\n")

# 第 2 步：计算能力指数
result = calculate_capability(
    data=data,
    usl=100.8,
    lsl=99.2,
    subgroup_size=5
)

# 第 3 步：输出报告
print("=" * 50)
print("Q-Caliper 过程能力评估报告")
print("=" * 50)
print(f"样本数量: {result.sample_size}")
print(f"分析模式: {result.analysis_mode}")  # 输出: cpk_grouped
print(f"子组数: {result.num_subgroups}\n")

print("基本统计:")
print(f"  均值: {result.mean:.4f}")
print(f"  短期 σ: {result.std_within:.4f}")
print(f"  长期 σ: {result.std_overall:.4f}\n")

print("规格限:")
print(f"  USL: {result.usl}")
print(f"  LSL: {result.lsl}\n")

print("能力指数:")
print(f"  Cpk (短期): {result.cpk:.3f}")
print(f"  Ppk (长期): {result.ppk:.3f}")
print(f"  Cmk (设备): {result.cmk:.3f}\n")

print("品质指标:")
print(f"  超 USL: {result.pct_above_usl:.4%}")
print(f"  低于 LSL: {result.pct_below_lsl:.4%}")
print(f"  总不合格率: {result.pct_total_out:.4%}\n")

# 第 4 步：诊断
if norm_result.is_normal and result.cpk >= 1.33:
    print("✓ 符合 IATF 16949 标准（Cpk ≥ 1.33）")
else:
    print("✗ 需要改进")

if result.cpk > result.ppk + 0.15:
    print("⚠️  过程存在时间漂移，需检查环境控制")
```

---

== 6. 实现细节与数值精度

=== 6.1 d₂ 常数与精度

Q-Caliper 内置了标准 $d_2$ 常数表，支持子组大小 $n$ 从 2 到 25 的精确计算。

- 对于 $n <= 25$：直接使用高精度查表值（源自 ASTM E158 标准）。
- 对于 $n > 25$：引擎将抛出异常，因为当子组过大时，极差法的统计效率会显著下降，此时推荐使用 $s$ 估算法（即通过平均标准差 $macron(s)/c_4$ 来估算 $sigma$，该方法能利用子组内所有数据，在大样本下更稳健）。

---

=== 6.2 正态性检验策略

- *n < 5000*：使用 Shapiro-Wilk 检验（功效高，样本敏感）
- *n ≥ 5000*：使用 Anderson-Darling 检验（计算效率高）
- *显著性水平*：α = 0.05（工程应用标准）

如数据不正态，Cpk/Ppk 计算值可能失效。此时考虑：
1. 数据变换（Box-Cox）
2. 非参数方法（百分位法）
3. 检查是否混合了两个不同过程

---

=== 6.3 数值稳定性

- 当 σ 接近 0 时（所有数据相同），函数返回 0.0（避免除以 0）
- 移动极差为空时，自动降级为全样本标准差
- NaN 值自动过滤

---

== 7. 最佳实践与常见陷阱

=== 7.1 何时用 Cmk，何时用 Cpk，何时用 Ppk

#table(
  columns: (1.5fr, 1.5fr, 2.5fr),
  inset: 8pt,
  fill: (x, y) => if y == 0 { luma(240) } else { white },
  stroke: 0.5pt,
  [*情景*], [*推荐指标*], [*理由*],
  [设备刚装机，做 FAT], [Cmk], [聚焦硬件精度，忽视工艺因素],
  [新产线首批生产，评估能力], [Cpk], [过程基本稳定，反映短期潜力],
  [月度质量总结报告], [Ppk], [包含全部真实变异，代表客户体验],
  [供应商继续验收], [Cpk（1.33+）], [IATF 16949 要求],
  [过程改进前后对比], [同一指标], [保持方法一致],
)

---

=== 7.2 常见错误

*错误 1*：同时报告 Cpk 和 Ppk，但不解释差异
→ 工程师困惑，无法诊断问题

*错误 2*：数据分组不合理（如随意分组）
→ 子组极差失去意义，σ_within 估计失效

*错误 3*：使用 Cpk 评估长期过程
→ 低估了实际风险（Cpk > Ppk 时的误导）

*错误 4*：不检查正态性就直接计算
→ 百分位法失准，PPM 估计错误

---

== 8. 版本与更新日志

*Q-Caliper Capability Engine v1.0*
- ✓ 完整 Cmk/Cpk/Ppk 实现
- ✓ Xbar-R 与 I-MR 双引擎
- ✓ Shapiro-Wilk / Anderson-Darling 正态性检验
---

#align(center, text(9pt, gray)[
  Q-Caliper - 由工程师为工程师设计的开源质量分析工具\
  文档版本: v1.0 | 发布日期: 2025年5月\
  源码: https://github.com/chenyu244/Q-Caliper
]))