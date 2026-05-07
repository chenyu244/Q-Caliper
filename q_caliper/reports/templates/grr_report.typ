// Q-Caliper GRR Report Template

#import "template.typ": project

#show: project.with(
  title: "{{TITLE}}",
  subtitle: "由 Q-Caliper 自动生成 | 模块: {{MODULE}}"
)

// Summary
= GRR 分析摘要

#table(
  columns: (auto, auto),
  inset: 8pt,
  stroke: 0.5pt,
  align: (left, left),
  table.header([指标], [值]),
  {{SUMMARY_ROWS}}
)

// ANOVA Table
= ANOVA 方差分析

{{TABLES}}

// Acceptance Criteria
= 判定标准

#table(
  columns: (auto, auto, auto),
  inset: 8pt,
  stroke: 0.5pt,
  table.header([指标], [可接受], [不可接受]),
  [%GRR], [< 10% (或 < 30% 可有条件接受)], [> 30%],
  [ndc (分级数)], [>= 5], [< 5],
)

// Charts
= 图表分析

{{CHARTS}}

// Conclusion
= 结论

由 GRR 分析结果:

- *重复性 (EV)*: 反映量具本身的变异
- *再现性 (AV)*: 反映不同操作者之间的变异
- *ndc*: 可区分的分级数, 反映量具分辨真实变异的能力
