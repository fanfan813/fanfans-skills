---
name: git-commit-message
description: Generate Git commit messages that follow the team's commit convention from a diff, staged changes, changed file list, or user summary. Use this skill whenever the user asks for a commit message, 提交文案, commit 说明, or wants a change summary converted into a compliant Git commit message. This skill only outputs commit message text and must not run git commit, git push, branch creation, or any other repository write operation unless the user separately asks for that action.
---

# Git Commit Message

根据代码变更生成符合团队规范的 `commit message`。

这个 skill 的目标很单纯：把“改了什么”转换成“怎么提交”，并且只产出提交文案，不替用户执行任何 Git 操作。

## 适用场景

- 用户明确说“帮我写 commit message”
- 用户给出 `git diff`、暂存区变更、文件列表或改动摘要，希望整理为提交信息
- 用户想把一组代码变更压缩成符合规范的提交标题与正文

## 强约束

- 只生成 `commit message` 文本
- 不执行 `git commit`
- 不执行 `git push`
- 不创建、切换或合并分支
- 不附带发布说明、PR 文案、命令清单，除非用户明确要求
- 如果上下文不足以可靠判断改动内容，先读取最小必要上下文；仍不足时，再向用户索取改动摘要，不能硬猜

## 输出格式

默认使用如下格式：

```text
<type>(<scope>): <subject>

<body>

<footer>
```

其中：

- `scope` 可省略
- `body` 可省略
- `footer` 可省略

如果用户只需要简洁结果，优先只输出单行标题。

## 类型选择

按以下语义选择最贴近的一种：

| type | 使用场景 |
| --- | --- |
| `feat` | 新功能、新能力、新入口 |
| `fix` | 缺陷修复、异常修正、兼容问题处理 |
| `docs` | 文档、说明、注释性文案变更 |
| `style` | 纯格式调整，不影响运行逻辑 |
| `refactor` | 重构、拆分、整理实现，行为保持不变 |
| `test` | 新增或调整测试 |
| `chore` | 杂项维护、脚本、辅助配置 |
| `perf` | 明确以性能优化为目的的改动 |
| `ci` | CI/CD 流程相关变更 |
| `build` | 构建系统、依赖、打包流程变更 |
| `revert` | 回滚已有提交 |

## Scope 选择

- 只在范围明确时填写 `scope`
- 优先使用最能代表影响面的模块或领域词
- 常见示例：`api`、`ui`、`auth`、`database`、`config`
- 不要为了凑格式强行填写过大或过泛的 `scope`

## Subject 规则

- 使用祈使句、现在时
- 首字母小写
- 结尾不加句号
- 控制在 50 个字符以内
- 优先使用中文，代码标识符和模块名保留原文
- 直接描述“本次提交要做什么”，不要写过程感很强的流水账

好的例子：

```text
fix(auth): 修复密码校验空值异常
refactor(api): 简化用户查询分页逻辑
docs: 补充风控规则接入说明
```

不好的例子：

```text
fix: fixed bug
feat: update code
refactor(api): 对代码进行一些优化处理。
```

## Body 书写原则

仅在以下情况补充 `body`：

- 单行标题不足以说明影响
- 需要解释改动背景或业务原因
- 需要说明兼容性、边界条件或限制

要求：

- 说明“是什么”和“为什么”，不要展开“怎么做”
- 与 `subject` 之间空一行
- 每行尽量不超过 72 个字符

## Footer 书写原则

仅在以下情况补充 `footer`：

- 需要声明 breaking change
- 需要关闭 issue，例如 `Closes #123`

## 生成流程

### Step 1: 理解改动

优先从以下信息中提炼提交意图：

1. `git diff` 或暂存区 diff
2. 变更文件列表
3. 用户给出的改动摘要

如果同时存在多类不相关改动，优先提醒用户拆分提交；若用户仍要求合并成一条，则选择最主要的改动方向生成。

### Step 2: 归类 type 和 scope

- 先判断这是“新增 / 修复 / 重构 / 文档 / 杂项”中的哪一类
- 再判断是否存在清晰的模块范围
- 如果 `scope` 会让提交更模糊，就省略

### Step 3: 生成 subject

- 用一句话概括核心动作
- 避免空泛词，如“优化”“调整”“处理一下”
- 尽量让不了解上下文的人也能从标题看出主要意图

### Step 4: 判断是否需要 body/footer

- 简单改动：只输出单行标题
- 复杂改动：补充 `body`
- 有 issue / breaking change：补充 `footer`

## 输出要求

默认直接给出最终 `commit message`，不要额外包裹解释。

如果用户没有要求候选项，只输出 1 条最合适的结果。

如果改动存在明显歧义，可以输出最多 3 条候选项，并用一句短说明区分适用场景。

## 示例

**示例 1：修复问题**

输入：

```text
修复登录时 password 为空导致的 NPE，并补充空值判断
```

输出：

```text
fix(auth): 修复密码校验空值异常
```

**示例 2：新增能力**

输入：

```text
新增批量导出订单的接口和导出按钮
```

输出：

```text
feat(order): 新增订单批量导出能力
```

**示例 3：复杂改动**

输入：

```text
重构用户查询接口，拆分 service 逻辑，并修复旧分页参数兼容问题
```

输出：

```text
refactor(user): 重构用户查询接口并兼容旧分页参数

梳理查询链路并下沉 service 逻辑，减少分页参数分支判断。
保留旧参数写法，避免影响现有调用方。
```
