# 项目执行铁律 (Project Iron Laws)

## 1. Git 推送双规 (Dual-Repo Push)
- **要求**: 每次执行 Git 推送（Push）操作时，必须**同时**推送至 GitHub (`origin`) 和私人仓库 (`private`)。
- **示例**: `git push origin main; git push private main`。

## 2. 终端命令兼容性 (Shell Compatibility)
- **环境约束**: 考虑到部分环境使用 PowerShell 5.1，**严禁**在 shell 命令中使用 `&&` 作为语句分隔符（该符号在 PS 5.1 中无效）。
- **替代方案**: 使用分号 `;` 或将命令分为多次调用。
- **示例**: 
  - 错误: `git status && git add .`
  - 正确: `git status; git add .`

# Typst 编写铁律 (Iron Laws for Typst)

在修改或创建 `.typ` 文件时，必须严格遵守以下规则，严禁混淆 LaTeX 语法。

## 1. 严禁使用反斜杠函数
- **LaTeX (禁止)**: `$\bar{x}$`, `$\sigma$`, `$\frac{a}{b}$`
- **Typst (强制)**: `$macron(x)$`, `$sigma$`, `$a/b$`
- **铁律**: 在 `$ ... $` 块内，绝对不允许出现以 `\` 开头的函数名。

## 2. 常用符号对照表
| 含义 | LaTeX (禁止) | Typst (强制) | 备注 |
| :--- | :--- | :--- | :--- |
| 上划线 | `\bar{x}`, `\overline{x}` | `macron(x)`, `overline(x)` | |
| 希腊字母 | `\sigma`, `\mu`, `\alpha` | `sigma`, `mu`, `alpha` | 无需反斜杠 |
| 运算符 | `\sum`, `\int` | `sum`, `int` | |
| 文本 | `\text{...}` | `"..."` | 引号括起来即为文本 |

## 3. 样式与格式
- **加粗**: 使用单星号 `*文本*`。禁止使用双星号 `**`。
- **斜体**: 使用单下划线 `_文本_`。
- **列表**: 使用 `-` 开头。

## 4. 编译校验
- **强制步骤**: 每次修改 `.typ` 文件后，必须执行 `typst compile <file>` 进行语法检查。若编译失败，严禁提交。

## 5. Python 渲染与集成避坑指南
在使用 Python 动态生成或编译 Typst 报告时，必须注意以下致命问题：
- **禁止混用 Markdown 语法**: Typst 引擎不支持 Markdown 的表格语法（如 `| Header |`）。在 Python 后端拼接数据时，必须严格生成原生 Typst 语法（如 `#table(columns: 2, [H1], [H2])`），否则会报 `the character | is not valid in code` 错误。
- **安全沙箱与文件路径 (file not found)**: Typst 有严格的 `root` 沙箱限制。如果将 `.typ` 放在临时目录而图片放在其他盘符，会由于路径跨越导致报错。**正确做法**：创建一个独立的临时隔离区（Workspace），将 `template.typ`、主渲染模板和所有 `#image` 依赖的图表文件**全部复制**进去，使用相对路径并在隔离区内执行编译，完成后清理该目录。
- **变量注入陷阱 (unclosed delimiter)**: 绝对禁止将未配对的格式化字符（尤其是单星号 `*`、双星号 `**` 等）作为普通数据值注入到模板中（比如表格里的“目标值”不能写成 `*`，应该写 `-`）。这会误导 Typst 启动加粗等样式块并在后续找不到闭合符导致直接崩溃。
- **模板语法错误 (expected semicolon)**: 禁止在模板中定义孤立的离散变量（例如尝试 `#let val = [1], [2]`，由 Python 直接替换 `{{VAR}}`）。所有占位符应当符合 Typst 正确的控制流，如果变量不需要，不要写出不完整的语句。
