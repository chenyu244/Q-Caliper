#import "template.typ": project

#show: project.with(
  title: "Q-Caliper: 实验设计 (DOE) 算法深度指南",
  subtitle: "涵盖全因子与分数因子设计、效应分析、Pareto 排序与模型诊断",
)

== 1. DOE 核心概念

Q-Caliper 的 DOE 模块通过系统地改变因子水平，帮助工程师识别影响过程响应的关键因子及其相互作用。

#table(
  columns: (1fr, 1.5fr, 4fr),
  inset: 10pt,
  align: (left, left, left),
  stroke: 0.5pt + gray,
  [*设计类型*], [*特点*], [*应用场景*],
  [2^k 全因子设计], [测试所有可能的因子组合。], [
    当因子数较少 ($k < 5$) 时，旨在准确评估主效应与所有交互作用。\
    _特点_：分辨率极高，但实验次数随 $k$ 指数级增长。
  ],
  [2^(k-p) 分数因子设计], [测试部分组合，节省实验成本。], [
    用于因子筛选 (Screening)，从大量潜在因子中找出关键的少数。\
    _特点_：牺牲部分高阶交互作用以换取实验效率。
  ],
)

---

== 2. 设计矩阵生成逻辑

Q-Caliper 使用编码水平（$-1$ 表示低水平，$+1$ 表示高水平）生成标准正交设计矩阵。

=== 2.1 全因子设计 (Full Factorial)

*算法步骤*：
1. 计算实验运行次数：$ n = 2^k $。
2. 生成所有因子水平的全排列组合。
3. 可选操作：随机化运行顺序 (Run Order) 以消除时间环境漂移的影响。

*Q-Caliper 实现*：
```python
levels = [-1, 1]
combinations = list(product(levels, repeat=n_factors))
design_matrix = np.array(combinations, dtype=float)
```

=== 2.2 分数因子设计 (Fractional Factorial)

Q-Caliper 目前支持标准的半分数设计 (Half-fraction, $2^(k-1)$)。
- *生成元 (Generator)*：最后一个因子的水平由前 $k-1$ 个因子的乘积决定（即 $I = "ABC"...K$）。

---

== 3. 效应分析与回归模型

DOE 的核心是建立响应变量 $y$ 与因子 $x_i$ 之间的线性模型。

=== 3.1 因子效应 (Factor Effect)

效应值衡量的是因子从低水平到高水平时，响应均值的变化量：
$ "Effect"_i = macron(y)_(x_i = +1) - macron(y)_(x_i = -1) $

=== 3.2 回归系数 (Coefficients)

在编码模型 $y = b_0 + sum b_i x_i + epsilon$ 中：
- 系数 $b_i$ 为效应值的一半：$ b_i = "Effect"_i / 2 $。
- 截距 $b_0$ 为所有实验运行响应的平均值。

---

== 4. 结果诊断与可视化

=== 4.1 Pareto 效应图 (Pareto Chart)

Q-Caliper 自动生成 Pareto 图，并计算显著性阈值（通常基于 $alpha = 0.05$）。
- *标准化效应*：$ t = b_i / "SE"(b_i) $。
- *阈值线*：基于 t 分布的临界值，标识出在统计上显著影响过程的因子。

=== 4.2 模型拟合度

- *R-squared ($R^2$)*：模型解释的变异比例。
- *调整后 R-squared*：考虑了因子数量对自由度的消耗，防止过拟合。

---

== 5. API 调用示例

=== 5.1 生成设计矩阵

```python
from q_caliper.core.doe import full_factorial

# 生成 3 因子全因子设计
design = full_factorial(n_factors=3, factor_names=["温度", "压力", "时间"])

# 查看设计矩阵 (2^3 = 8 次实验)
print(design.design_matrix)
print(f"设计类型: {design.design_type}")
```

=== 5.2 分数因子筛选设计

```python
from q_caliper.core.doe import fractional_factorial

# 生成 5 因子的半分数设计 (仅需 16 次实验，而非 32 次)
screening_design = fractional_factorial(n_factors=5)
print(f"运行次数: {screening_design.n_runs}")
```

---

== 6. 工程实践建议

1. *随机化 (Randomization)*：严禁按设计矩阵的顺序直接实验。必须使用 Q-Caliper 提供的 `run_order` 进行实验，以平衡外部环境噪声。
2. *中心点 (Center Points)*：推荐在实验中加入 3-5 个中心点（因子水平均为 0），用于评估过程的曲率 (Curvature) 和实验误差的稳定性。
3. *分辨率 (Resolution)*：在使用分数因子设计时，注意效应混淆 (Aliasing)。三分辨率设计 (Resolution III) 会使主效应与二阶交互作用混淆。
4. *逐步实验*：先用分数因子设计筛选出关键因子，再用全因子设计或响应面法 (RSM) 进行深度优化。

---

#align(center, text(9pt, gray)[
  Q-Caliper - 实验设计模块文档\
  版本: v1.0 | 工业标准实验统计引擎\
  源码: https://github.com/chenyu244/Q-Caliper
])
