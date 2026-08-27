---
name: token-wise
description: "Save AI model tokens and cost without degrading quality. Use when the user wants to cut token usage in long agent sessions: zombie sessions, bloated context, verbose output, repeated re-explaining, large file reads. Provides lossless-first savings with a layered lossy-measures gate (L0/L1/L2), plus red-line rules with optional reminders."
agent_created: true
---

# Token-Wise（省 token 不降智）

> 目标：在不降低模型输出质量的前提下，系统性地减少 token 用量与成本。

## 核心原则（三条铁律）

1. **无损优先**：省 token 的正确姿势是"少带无关的东西"，不是"把该带的东西压缩"。
2. **省钱指标 = 每件完成的事的成本**，不是每个 token 的成本。返工、重试、瞎改三件事烧掉的钱，永远大于 token 差价。
3. **有损手段必须分级授权**：默认只开无损层（L0），有损层（L1/L2）按配置与任务类型放行。

## 配置加载

1. 定位配置文件 `config/token-wise.config.md`（随 skill 分发，或用户自定义位置）。
2. 读取其中 `preset`（conservative / balanced / aggressive）与本次任务相关的开关；只提取所需字段，不要将整个配置文件复述进回复。
3. 若配置缺失或字段冲突：按默认值（balanced + 全部默认开启项）执行，并在回复中说明"使用了默认配置"。
4. 冲突裁决规则：`protected_tasks` 优先级 > 模块开关 > preset。

## 红线守则（不可违反，行为级约束）

> 红线本身**不可通过配置关闭**；配置只控制 agent 是否**主动提醒**（见 `redlines.reminders`）。
> 提醒关闭 ≠ 红线失效——行为依然遵守，只是不打扰用户。
> 文档（README）中已强调：**红线建议用户自己遵守，效果最好**。

| # | 红线 | agent 行为 |
|---|---|---|
| R1 | 不轻易切窗口（新会话）| 检测到用户要"新开会话/重来"且当前任务未完成时，提示续同一会话更省（缓存+上下文连续）；若必须切换，先自动输出一段进度小结 |
| R2 | 不过缓存时间（TTL）对话 | 感知会话上下文大小与持续时间，超过 `context_hygiene.compact_hint_threshold` 时建议 /compact 或收尾；收尾前**强制**产出"进度小结+待办+下一步"（受 `context_hygiene.overnight_summary` 控制）。**任务中断后恢复**：确认在同一会话内继续即可，缓存未失效（TTL 内），不要重开会话重来 |
| R3 | 做好索引地图 | 进入代码任务时检查 `AI_INDEX.md` 是否存在；缺失则建议生成；修改文件后提醒更新索引（受 `input_slim.index_map` 控制）|

### 温馨提醒

- **R2 关于缓存时间（TTL）**：不同厂商/模型的缓存时长不同——Claude 系约 5 分钟（可扩展），OpenAI 系约 5 分钟~1 小时，其余以厂商官方文档为准。不要盲信统一数值，选型时查厂商定价页。本 skill 不写死 TTL，只按 `compact_hint_threshold` 给压缩/收尾建议。
- **R3 关于索引地图**：Codex、Claude Code、Aider 等主流工具已内置仓库索引（repo map），优先使用工具自带能力；手写 `AI_INDEX.md` 作为补充（尤其用于工具索引覆盖不到的语言或场景）。
| R4 | 模式二：先规划后执行 | 任务复杂度高（或命中 `protected_tasks`，判定见 `references/decision-tree.md`）时，先输出方案清单，用户确认后才动手 |

### 提醒开关语义

- `redlines.reminders: true`（默认）：在上述触发点主动提醒用户，并给出原因。
- `redlines.reminders: false`：**静默遵守**——不主动啰嗦；仅在用户明确做出违反红线的操作时，给一句简短提示，其余情况不打扰。

## 工作流

### 会话开局
1. 读取配置（见"配置加载"）。
2. 若为代码任务且配置要求：检查索引地图是否存在（R3）。
3. 输出纪律与输入瘦身规则生效（见下）。

### 会话执行中（每轮）
1. **输出纪律**：按 `output_discipline.strictness` 执行（禁寒暄、diff-only、默认简版）。
2. **输入瘦身**：优先精确引用（文件+符号+行号）；宽检索丢给 subagent；静态内容前置、动态内容后置。
3. **上下文卫生**：上下文超过 `clear_hint_threshold` / `compact_hint_threshold` 时，按配置提示（受 `redlines.reminders` 控制）。
4. **分级闸门**：按 `references/decision-tree.md` 判定当前任务适用的 L 级别，有损手段只在放行时使用。
5. **返工检测**：同一问题被修正 ≥2 次 → 提示"上下文可能被失败尝试污染，建议重开并重新组织 prompt"。

### 会话收尾
1. 若配置 `context_hygiene.overnight_summary: true`：输出"进度小结 + 待办 + 下一步"。
2. 若用户要切换新会话：先给小结（R1），再允许切换。

## Token 预算（本 skill 自身的成本）

- 常驻加载：SKILL.md（约 1.5K token）+ config（约 1K token）。
- 按需加载：`references/*`（决策树/模板，每次几百 token，仅判定或取模板时读）。
- 总常驻成本约 2~3K token/会话——这是"纪律型 skill"的固定开销，已控制在最小。
- 极简模式：只需要红线 + 输出纪律时，删除 `config/` 与 `references/`，单文件 SKILL.md 即可运行（所有行为用内联默认值）。

## 分级闸门（L0 / L1 / L2）

| 级别 | 手段 | 默认 |
|---|---|---|
| L0 无损 | 删冗余、缓存友好排序、精确引用、索引地图、subagent 隔离、输出格式约束 | 永远开启 |
| L1 轻度有损 | 输出压缩（Caveman 式）、summary 型历史管理、/clear 建议 | 按 `preset` |
| L2 重度有损 | /compact 全量压缩、模型降档、关闭/降低思考 | 默认关闭，需显式开启 |

- 判定规则见 `references/decision-tree.md`。
- `protected_tasks` 中的任务类型**禁止**使用 L2，且 L1 仅限输出压缩。
- 路由与思考控制：按 `router` 与 `thinking` 配置执行；`thinking.mode: auto` 时按任务复杂度给档位，禁止全局关闭思考。

## 提示词模板

可直接复用的模板见 `references/prompt-templates.md`（模式二两阶段、确认开工、长会话收尾、新会话开局、索引地图生成）。

## 资源说明

- `config/token-wise.config.md` — 用户唯一需要编辑的配置文件（三档预设 + 模块开关 + 红线提醒开关 + 豁免表）。
- `references/decision-tree.md` — 分级闸门判定决策树（agent 查表用）。
- `references/prompt-templates.md` — 各场景提示词模板与好坏示例对比。
