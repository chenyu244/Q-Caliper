#import "@preview/cuti:0.3.0": show-cn-fakebold

#let project(title: "", subtitle: "", body) = {
  show: show-cn-fakebold
  
  set page(
    paper: "a4",
    margin: (x: 2.5cm, y: 2.5cm),
    header: align(right, text(8pt, gray)[Q-Caliper 开源项目 - 技术文档]),
    footer: context align(center, counter(page).display()),
  )

  set text(
    font: ("Times New Roman", "SimSun", "Microsoft YaHei"),
    size: 11pt,
    lang: "zh",
  )

  set par(leading: 1em, justify: true)

  show heading: set block(above: 1.5em, below: 1em)
  show heading: set text(fill: navy)
  show link: set text(fill: blue)
  
  // 统一表格样式：斑马纹与边框
  show table: set table(
    inset: 8pt,
    stroke: 0.5pt + gray,
    fill: (x, y) => if y == 0 { luma(230) } else if calc.even(y) { white } else { luma(250) }
  )

  show raw.where(block: true): set text(font: ("Consolas", "Microsoft YaHei"), size: 10pt)
  show raw.where(block: false): set text(font: ("Consolas", "Microsoft YaHei"), size: 9pt)

  if title != "" {
    align(center)[
      #text(24pt, weight: "bold")[#title] \
      #if subtitle != "" {
        v(0.5em)
        text(12pt, style: "italic")[#subtitle]
      }
    ]
    v(1em)
  }

  body
}
