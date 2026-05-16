#import "template.typ": project

#show: project.with(
  title: "Q-Caliper: 测量系统分析 (MSA) 算法深度指南",
  subtitle: "涵盖偏差 (Bias)、线性 (Linearity) 与量具 R&R (ANOVA) 的计算逻辑与工程诊断",
)

== 1. 核心概念与指标定义

在 Q-Caliper 测量系统分析引擎中，我们根据 *AIAG MSA 第四版手册* 实现了三类核心分析，用于评估量具的准确度与精确度：

#table(
  columns: (1fr, 1.5fr, 4fr),
  inset: 10pt,
  align: (left, left, left),
  stroke: 0.5pt + gray,
  [*分析类别*], [*核心指标*], [*评估目标与应用*],
  [偏差 (Bias)], [p-value, Bias%], [
    *准确度 (Accuracy)*。评估测量均值与参考真值的差异。\
    _应用场景_：量具校准验证、基准偏移检查。
  ],
  [线性 (Linearity)], [Slope, P/T Ratio], [
    *量程准确度*。评估量具在整个量程范围内的偏差是否一致。\
    _应用场景_：宽量程测量设备的可靠性验证。
  ],
  [量具 R&R (GR&R)], [%GRR, ndc], [
    *精确度 (Precision)*。评估测量系统的重复性（量具）与再现性（操作者）。\
    _应用场景_：新量具验收、生产过程测量系统监控。
  ]
)

#v(1em)

=== 1.1 精确度与准确度的数学关系

总变异 ($sigma^2_"Total"$) 是产品真实变异与测量系统变异的平方和：
$ sigma^2_"Total" = sigma^2_"Part" + sigma^2_"MS" $

其中，测量系统变异 ($sigma^2_"MS"$) 包含：
- *准确度相关*：偏差、线性、稳定性（系统性误差）。
- *精确度相关*：重复性 (EV) 与再现性 (AV)。

---

== 2. 偏差分析 (Bias Analysis) 算法

=== 2.1 统计学原理

偏差分析采用 *单样本 t 检验*。

*算法步骤*：
1. 选取一个已知参考值 $X_"ref"$ 的基准件。
2. 进行 $n$ 次重复测量，得到均值 $macron(x)$ 和标准差 $s$。
3. 计算偏差：$ "Bias" = macron(x) - X_"ref" $
4. 计算 t 统计量：$ t = "Bias" / (s / sqrt(n)) $
5. 获取 p-value：基于自由度 $ "df" = n - 1 $ 的双尾 t 分布。

*Q-Caliper 实现*：
```python
bias = mean - reference_value
t_stat = bias / (std / np.sqrt(n))
p_val = 2 * (1 - stats.t.cdf(abs(t_stat), df=n-1))
is_significant = p_val < 0.05
```

=== 2.2 诊断标准
- *p-value >= 0.05*：无显著偏差，量具准确。
- *p-value < 0.05*：存在显著偏差。
- *95% 置信区间*：若区间包含 0，说明偏差在统计误差范围内可接受。

---

== 3. 线性分析 (Linearity Analysis) 算法

=== 3.1 回归模型

线性分析评估偏差 ($y$) 随参考值 ($x$) 的变化关系。

*回归方程*：$ y = a + b x + epsilon $
- $b$ (Slope)：斜率，反映量程内的比例偏差。
- $a$ (Intercept)：截距。

*关键指标 - 线性度 (Linearity) 与 %Linearity*：
$ "Linearity" = |b| times "Process Variation" $
$ %"Linearity" = "Linearity" / "Process Variation" times 100% = |b| times 100% $
（Q-Caliper 默认使用 $6 sigma$ 或规格限作为过程变异）

*Q-Caliper 实现*：
```python
slope, intercept, r_value, p_value, _ = stats.linregress(refs, biases)
linearity = abs(slope) * process_variation
pct_linearity = abs(slope) * 100.0
```

=== 3.2 诊断标准
- *%Linearity <= 5%*：线性优良。
- *5% < %Linearity <= 10%*：有条件接受。
- *R-squared 接近 1*：说明偏差具有极强的线性趋势，必须通过修正系数或重新校准来补偿。

---

== 4. 量具 R&R (GR&R) - 方差分析法 (ANOVA)

Q-Caliper 采用 *双因素交叉模型 (Two-Way Random Effects Model)*，相比极差法，它能更精确地分离出 *交互作用*。

=== 4.1 方差分解公式

总平方和 ($"SS"_"Total"$) 被分解为：
$ "SS"_"Total" = "SS"_"Parts" + "SS"_"Operators" + "SS"_"Interaction" + "SS"_"Error" $

*关键变异来源 (Variance Components)*：
1. *重复性 (EV)*：$ sigma^2_"Repeatability" = "MS"_"Error" $
2. *再现性 (AV)*：$ sigma^2_"Reproducibility" = max(0, ("MS"_"Operators" - "MS"_"Interaction") / (n_"Parts" times n_"Trials")) $
3. *交互作用 (INT)*：$ sigma^2_"Interaction" = max(0, ("MS"_"Interaction" - "MS"_"Error") / n_"Trials") $
4. *量具 R&R (GR&R)*：$ sigma^2_"GRR" = sigma^2_"EV" + sigma^2_"AV" + sigma^2_"INT" $

=== 4.2 核心评估指标

*1. %GRR (研究变异百分比)*：
$ %"GRR" = sigma_"GRR" / sigma_"Total" times 100% $

*2. ndc (可区分类别数)*：
$ "ndc" = 1.41 times (sigma_"Part" / sigma_"GRR") $
反映了测量系统分辨零件间微小差异的能力。

---

== 5. 工程决策矩阵

根据分析结果，Q-Caliper 建议采取以下行动：

#align(center)[
  #table(
    columns: (1.2fr, 1.2fr, 3fr),
    inset: 10pt,
    fill: (x, y) => if y == 0 { luma(200) } else if calc.rem(y, 2) == 0 { luma(245) } else { white },
    stroke: 0.5pt,
    [*指标结果*], [*评价等级*], [*工程建议与诊断*],
    
    [%GRR < 10%], [优], [测量系统完全可接受。无需进一步改进。],
    
    [10% < %GRR < 30%], [合格], [有条件接受。根据应用的重要性、量具成本或维修难度决定。],
    
    [%GRR > 30%], [不合格], [必须改进。调查变异来源：\
    - *EV >> AV*：检查量具磨损、夹具松动或量具分辨率。\
    - *AV >> EV*：加强操作者培训，统一测量手法。],
    
    [ndc < 5], [分辨力不足], [量具无法区分零件间的微小波动。可能产生误判。建议更换更高精度的传感器。],
    
    [Interaction (p < 0.05)], [显著交互], [说明特定操作者对特定零件有特殊的测量偏好。需检查测量步骤的一致性。],
  )
]

---

== 6. API 调用示例

=== 6.1 偏差与线性分析

```python
from q_caliper.core.msa import analyze_bias, analyze_linearity

# 偏差分析
bias_res = analyze_bias(data=[10.1, 10.2, 10.1, 10.1], reference_value=10.0)
print(f"显著性: {bias_res.is_significant}, 均值偏差: {bias_res.mean_bias}")

# 线性分析
linear_res = analyze_linearity(
    reference_values=[10, 20, 30, 40, 50],
    observed_means=[10.1, 20.2, 30.3, 40.4, 50.5],
    process_variation=10.0 # 通常为 6*sigma 或公差
)
print(f"Slope: {linear_res.slope}, %Linearity: {linear_res.pct_linearity:.2f}%")
```

=== 6.2 量具 R&R (ANOVA)

```python
from q_caliper.core.grr import calculate_grr

# 准备数据: parts x operators x trials
# 数据需展平为一维数组
result = calculate_grr(
    data=measurement_data,
    n_parts=10,
    n_operators=3,
    n_trials=2
)

print(f"%GRR: {result.pct_grr:.2f}%")
print(f"ndc: {result.ndc}")
print(f"重复性贡献: {result.var_repeatability / result.var_total:.1%}")
```

---

== 7. 最佳实践指南

1. *零件选择*：样本必须覆盖过程的预期变异。如果零件过于相似，ndc 会被人为降低，导致 %GRR 偏高。
2. *操作者选择*：必须选择实际使用该量具的人员。
3. *盲测原则*：在 GR&R 研究中，操作者不应知道零件的编号或之前的测量结果，以消除主观期望偏差。
4. *数据分布*：如果发现 %PV 极低，首先检查零件抽样是否具有代表性，而不是急于更换量具。

---

#align(center, text(9pt, gray)[
  Q-Caliper - 测量系统分析模块文档\
  版本: v1.0 | 符合 AIAG MSA 第四版标准\
  源码: https://github.com/chenyu244/Q-Caliper
])
