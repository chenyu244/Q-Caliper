#import "template.typ": project

#show: project.with(
  title: "Q-Caliper: 统计过程控制 (SPC) 算法深度指南",
  subtitle: "涵盖控制图计算逻辑、八大判异准则 (Nelson Rules) 与过程能力监测",
)

== 1. SPC 核心理念

Q-Caliper 的 SPC 引擎旨在通过统计方法区分过程中的 *偶然原因 (Common Cause)* 与 *异常原因 (Special Cause)*。

#table(
  columns: (1fr, 1.5fr, 4fr),
  inset: 10pt,
  align: (left, left, left),
  stroke: 0.5pt + gray,
  [*控制图类型*], [*适用场景*], [*算法核心*],
  [Xbar-R 图], [计量型数据，有理子组 ($n=2$ 至 $10$)], [
    利用子组均值监控 *过程中心*，利用子组极差监控 *过程波动*。\
    _应用场景_：大批量自动化生产，定期抽样。
  ],
  [I-MR 图], [计量型数据，单值样本 ($n=1$)], [
    利用单值监控 *过程中心*，利用移动极差监控 *过程波动*。\
    _应用场景_：连续流（如化工）、破坏性试验、昂贵产品。
  ],
)

---

== 2. 控制图计算逻辑

=== 2.1 Xbar-R 控制图

*1. Xbar 图控制限*：
- 中心线 ($"CL"$)：$ macron(macron(x)) = 1/k sum macron(x)_i $
- 控制限：$ "UCL" / "LCL" = macron(macron(x)) plus.minus A_2 macron(R) $

*2. R 图控制限*：
- 中心线 ($"CL"$)：$ macron(R) = 1/k sum R_i $
- 控制限：$ "UCL" = D_4 macron(R) $，$ "LCL" = D_3 macron(R) $

*Q-Caliper 实现*：
```python
xbar_cl = np.mean(means)
r_cl = np.mean(ranges)
xbar_ucl = xbar_cl + a2 * r_cl
r_ucl = d4_const * r_cl
```

=== 2.2 I-MR 控制图 (Individual-Moving Range)

*1. I 图 (单值图)*：
- 控制限：$ "UCL" / "LCL" = macron(x) plus.minus 3 macron("MR") / d_2 $
  _（注：单值移动极差 $n=2$ 时 $d_2 = 1.128$，因此 $3 / 1.128 approx 2.66$，实际应用中常简写为 $macron(x) plus.minus 2.66 times macron("MR")$）_

*2. MR 图 (移动极差图)*：
- 控制限：$ "UCL" = 3.267 times macron("MR") $，$ "LCL" = 0 $

---

== 3. 八大判异准则 (Nelson Rules)

Q-Caliper 实现了完整的 Nelson 八大判异准则 (Nelson Rules)，用于自动识别过程的不稳定性。

#table(
  columns: (0.8fr, 1.5fr, 3fr),
  inset: 10pt,
  fill: (x, y) => if y == 0 { luma(200) } else if calc.rem(y, 2) == 0 { luma(245) } else { white },
  stroke: 0.5pt,
  [*规则*], [*判定条件*], [*初步诊断*],
  
  [Rule 1], [1点超出 3$sigma$ 控制限], [突发性异常原因（如换料、突然停机）。],
  
  [Rule 2], [连续 9 点在中心线同一侧], [过程均值发生了持续性的偏移。],
  
  [Rule 3], [连续 6 点单调递增或递减], [过程存在趋势性漂移（如刀具磨损、气压缓慢下降）。],
  
  [Rule 4], [连续 14 点交替上下波动], [数据受到人为干预或采样方式存在周期性偏差。],
  
  [Rule 5], [3 点中有 2 点落在 2$sigma$ 外], [过程变异正在增大，预警信号。],
  
  [Rule 6], [5 点中有 4 点落在 1$sigma$ 外], [过程均值已发生小幅度漂移。],
  
  [Rule 7], [连续 15 点落在 1$sigma$ 以内], [可能存在分层、分辨率不足、过度筛选或非自然采样。],
  
  [Rule 8], [连续 8 点在 1$sigma$ 外但未出限], [可能存在过程混合 (mixture) 或过度调节 (tampering)。],
)

---

== 4. 区域划分与 $sigma$ 估算

控制图被划分为三个区域（基于 $sigma$ 估算值，而非全样本 $s$）：
- *C 区*：中心线至 1$sigma$。
- *B 区*：1$sigma$ 至 2$sigma$。
- *A 区*：2$sigma$ 至 3$sigma$（控制限）。

*Q-Caliper $sigma$ 估算逻辑*：
对于 Xbar-R 图，基于极差估算：$ sigma_"within" = macron(R) / d_2 $
这确保了判异准则对 *短期波动* 的敏感性。

---

== 5. 控制限 vs 规格限 (核心辨析)

这是整个 SPC 质量体系的灵魂概念，工程师必须严格区分：

#table(
  columns: (1.5fr, 1.5fr, 3fr),
  inset: 10pt,
  fill: (x, y) => if y == 0 { luma(200) } else if calc.rem(y, 2) == 0 { luma(245) } else { white },
  stroke: 0.5pt,
  [*限值类型*], [*来源与决定因素*], [*核心作用*],
  [控制限 (UCL/LCL)], [过程的内在统计特性\ （由均值和变异计算得出）], [判断过程是否*稳定受控*。\ 提示是否存在特殊原因。],
  [规格限 (USL/LSL)], [客户或产品设计要求\ （与实际制造表现无关）], [判断产品是否*合格*。],
)

*核心准则*：
- *SPC 不看规格*：控制图只监控稳定性，点在控制限内不代表产品合格（可能整体偏离目标）。
- *Capability (能力分析) 才看规格*：只有当过程稳定后，结合规格限计算的 Cpk/Ppk 才有预测未来质量的意义。

---

== 6. API 调用示例

=== 6.1 生成 Xbar-R 控制图

```python
from q_caliper.core.spc import xbar_r_chart

# 准备数据并指定子组大小
data = [...] # 连续测量数据
x_chart, r_chart = xbar_r_chart(data, subgroup_size=5)

# 检查 Xbar 图中的违规点
for v in x_chart.violations:
    print(f"索引 {v.index}: 触发 {v.rule} ({v.description})")

# 获取控制限
print(f"UCL: {x_chart.limits.ucl}, CL: {x_chart.limits.cl}")
```

=== 6.2 生成 I-MR 控制图

```python
from q_caliper.core.spc import imr_chart

i_chart, mr_chart = imr_chart(data)
print(f"单值图平均值: {i_chart.limits.cl}")
```

---

== 7. 最佳实践指南

1. *先看波动图，再看均值图*：在分析 Xbar-R 时，若 R 图失控（变异不稳定），则 Xbar 图的控制限也失去了统计意义。应先稳定过程变异。
2. *子组大小的选择*：子组大小 $n$ 常用 4 或 5。$n > 10$ 时推荐使用 Xbar-S 控制图（Q-Caliper 将在后续版本中强化 S 图支持）。
3. *受控与稳态*：控制图受控不代表产品合格。受控仅表示过程 *可预测*。必须结合 Cpk/Ppk 才能判断能力是否达标。
4. *判异后的行动*：每当触发判异规则时，必须调查 *特殊原因*。严禁仅通过重新计算控制限来“消除”异常点。

---

#align(center, text(9pt, gray)[
  Q-Caliper - 统计过程控制模块文档\
  版本: v1.0 | 符合 AIAG SPC 第二版标准\
  源码: https://github.com/chenyu244/Q-Caliper
])
