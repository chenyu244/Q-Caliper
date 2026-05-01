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

  show heading: set text(fill: navy)
  show link: set text(fill: blue)
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
