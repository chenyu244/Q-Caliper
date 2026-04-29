// Q-Caliper GRR Report Template
// Variables: {{COMPANY}}, {{TITLE}}, {{AUTHOR}}, {{DATE}}, {{MODULE}},
//            {{SUMMARY_ROWS}}, {{TABLES}}, {{CHARTS}}

#set document(title: "{{TITLE}}", author: "{{COMPANY}}")
#set page(paper: "a4", margin: (top: 2.5cm, bottom: 2cm, left: 2cm, right: 2cm))
#set text(font: ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"), size: 10pt)
#set heading(numbering: "1.1")

// Cover
#align(center)[
  #v(3cm)
  #text(size: 24pt, weight: "bold")[GRR 量具重复性与再现性分析报告]
  #v(1cm)
  #text(size: 14pt, fill: gray)[{{COMPANY}}]
  #v(0.5cm)
  #text(size: 10pt)[{{DATE}}]
  #if "{{AUTHOR}}" != "" [
    #text(size: 10pt)[编制: {{AUTHOR}}]
  ]
]

#pagebreak()

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

#v(1fr)
#line(length: 100%, stroke: 0.5pt)
#text(size: 8pt, fill: gray)[由 Q-Caliper v1.0 自动生成 — 符合 IATF 16949 MSA 要求]
