// Q-Caliper Cpk Report Template
// Variables: {{COMPANY}}, {{TITLE}}, {{AUTHOR}}, {{DATE}}, {{MODULE}},
//            {{SUMMARY_ROWS}}, {{TABLES}}, {{CHARTS}}

#set document(title: "{{TITLE}}", author: "{{COMPANY}}")
#set page(paper: "a4", margin: (top: 2.5cm, bottom: 2cm, left: 2cm, right: 2cm))
#set text(font: ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"), size: 10pt)
#set heading(numbering: "1.1")

// Cover
#align(center)[
  #v(3cm)
  #text(size: 24pt, weight: "bold")[Cpk 过程能力分析报告]
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
= 分析摘要

#table(
  columns: (auto, auto),
  inset: 8pt,
  stroke: 0.5pt,
  align: (left, left),
  table.header([指标], [值]),
  {{SUMMARY_ROWS}}
)

// Capability Indices
= 过程能力指数

Cpk 是衡量过程满足规格要求能力的核心指标:

- *Cp* >= 1.33: 过程能力良好
- *Cpk* >= 1.33: 过程实际能力良好 (考虑均值偏移)
- *Ppk*: 使用总体标准差的过程性能指数

{{TABLES}}

// Charts
= 直方图与分布

{{CHARTS}}

// Conclusion
= 结论

由以上分析结果可得:

#let cpk_val = {{SUMMARY_ROWS}}

#table(
  columns: (auto, auto),
  inset: 8pt,
  stroke: 0.5pt,
  table.header([Cpk 范围], [判定]),
  [>= 1.67], [优秀 — 过程能力充足],
  [>= 1.33], [良好 — 过程能力满足要求],
  [>= 1.00], [可接受 — 过程能力勉强满足],
  [< 1.00], [不可接受 — 需改进过程],
)

#v(1fr)
#line(length: 100%, stroke: 0.5pt)
#text(size: 8pt, fill: gray)[由 Q-Caliper v1.0 自动生成]
