// Q-Caliper Base Report Template

#import "template.typ": project

#show: project.with(
  title: "{{TITLE}}",
  subtitle: "由 Q-Caliper 自动生成 | 模块: {{MODULE}}"
)

// Summary
= 分析摘要

#table(
  columns: (auto, auto),
  inset: 8pt,
  stroke: 0.5pt,
  align: (left, left),
  table.header([指标], [值]),
  {{SUMMARY_ROWS}}
)

// Data Tables
= 数据分析

{{TABLES}}

// Charts
= 图表

{{CHARTS}}
