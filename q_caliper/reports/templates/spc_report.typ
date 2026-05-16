// Q-Caliper SPC 统计过程控制报告模板

#import "template.typ": project

#show: project.with(
  title: "统计过程控制 (SPC) 分析报告",
  subtitle: "由 Q-Caliper 自动生成 | 模块: {{MODULE}} | 日期: {{DATE}}"
)

= 1. 数据总结

本章节汇总了本次 SPC 分析的输入参数与数据概况。

{{TABLE_DATA_SUMMARY}}

= 2. 控制图

{{CHARTS}}

= 3. 控制限参数

{{TABLE_LIMITS}}

= 4. 判异规则检测结果

采用 Nelson 八大判异准则 (Nelson Rules) 对控制图进行自动检测。

{{TABLE_VIOLATIONS}}

= 5. 过程能力趋势 (Cpk)

{{TABLE_CPK}}

= 6. 判异准则说明

== 6.1 八大判异准则 (Nelson Rules)
+ *Rule 1*: 任何点超出控制限 (UCL 或 LCL)。表明过程出现特殊原因变异。
+ *Rule 2*: 连续 9 点在中心线同一侧。表明过程均值发生漂移。
+ *Rule 3*: 连续 6 点递增或递降。表明过程存在趋势 (如刀具磨损)。
+ *Rule 4*: 连续 14 点交替上下。表明过程存在系统性振荡。
+ *Rule 5*: 连续 3 点中 2 点在 A 区外 (2#sym.sigma 以外)。表明过程变异增大。
+ *Rule 6*: 连续 5 点中 4 点在 B 区外 (1#sym.sigma 以外)。表明过程均值发生小幅度偏移。
+ *Rule 7*: 连续 15 点在 C 区内 (1#sym.sigma 以内)。可能存在分层、分辨率不足、过度筛选或非自然采样。
+ *Rule 8*: 连续 8 点在 C 区外 (均在控制限内)。可能存在过程混合 (mixture) 或过度调节 (tampering)。

== 6.2 过程能力趋势说明
过程能力趋势图将数据分为 5 段, 逐段计算 Cpk 值:
- *Cpk >= 1.33*: 过程能力充足 (绿色)
- *1.0 <= Cpk < 1.33*: 过程能力边际 (橙色)
- *Cpk < 1.0*: 过程能力不足 (红色)

趋势图可帮助识别过程能力是否随时间恶化 (如设备磨损、环境变化等)。
