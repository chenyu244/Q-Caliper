// Q-Caliper Base Report Template
// Variables: {{COMPANY}}, {{TITLE}}, {{AUTHOR}}, {{DATE}}, {{MODULE}},
//            {{SUMMARY_ROWS}}, {{TABLES}}, {{CHARTS}}

#set document(title: "{{TITLE}}", author: "{{COMPANY}}")
#set page(paper: "a4", margin: (top: 2.5cm, bottom: 2cm, left: 2cm, right: 2cm))
#set text(font: ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"), size: 10pt)
#set heading(numbering: "1.1")

// Cover
#align(center)[
  #v(3cm)
  #text(size: 24pt, weight: "bold")[{{TITLE}}]
  #v(1cm)
  #text(size: 14pt, fill: gray)[{{COMPANY}}]
  #v(0.5cm)
  #text(size: 11pt)[模块: {{MODULE}}]
  #v(0.5cm)
  #text(size: 10pt)[{{DATE}}]
  #v(0.5cm)
  #text(size: 10pt)[{{AUTHOR}}]
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

// Data Tables
= 数据分析

{{TABLES}}

// Charts
= 图表

{{CHARTS}}

// Footer
#v(1fr)
#line(length: 100%, stroke: 0.5pt)
#text(size: 8pt, fill: gray)[由 Q-Caliper 自动生成]
