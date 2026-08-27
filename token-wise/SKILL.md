---
name: token-wise
description: "Save AI model tokens and cost without degrading quality. Use when the user wants to cut token usage in long agent sessions: zombie sessions, bloated context, verbose output, repeated re-explaining, large file reads. Provides lossless-first savings with a layered lossy-measures gate (L0/L1/L2), plus red-line rules with optional reminders."
agent_created: true
---

# Token-Wise（Agent Cost Optimization Framework）

> 目标：**在质量约束下**减少不必要的 token 与推理成本。
> 核心理念：**Context Hygiene（有效上下文管理）**，不是"别开新会话"。
> 一句话：先减少无效上下文和重复工作，再减少输出废话，最后才动模型能力。

## 核心概念（先分清四层，别混为一谈）

| 层 | 是什么 | 生命周期 |
|---|---|---|
| Conversation History | 对话记录，存在会话里 | 会话一直保留 |
| Context | 当前喂给模型的上下文窗口内容 | 随会话增长，可被整理/清空 |
| Prompt Cache | 服务端前缀缓存（命中打折） | 短（5min~1h 级，按厂商），**过期只影响计费，不影响上下文** |
| Token Billing | 计费 | 每轮按输入+输出算 |

**关键结论**：缓存过期 ≠ 上下文丢失 ≠ 必须开新会话。四层独立，不要把它们当成一个东西。

## 核心原则

1. **省钱指标 = 每件完成的事的成本（Cost per successful task）**，不是每 token 成本。
   ```
   Total Cost = Input + Output + Cache + Retry + Correction + Human Review
   ```
   多花 20% token 一次做对，远好于省 30% token 却返工 2 次。
2. **优化优先级**（从高到低）：
   减少无效上下文 → 减少重复工作 → 减少输出废话 → 合理利用缓存 → 模型路由 → compact/降 reasoning。
3. **有损手段分级授权**：默认只开 L0（Context 优化）；L1/L2 按配置与任务类型放行。

## 七问自检（每轮执行前快速过一遍）

1. 我是不是把不需要的信息给 AI 了？（无效上下文）
2. AI 是不是重复读取了已经知道的信息？（重复工作）
3. 当前历史是不是已经变成噪音？（上下文污染）
4. AI 是不是在输出大量无价值内容？（输出废话）
5. 当前任务是否真的需要旗舰模型？（模型路由）
6. 当前任务是否真的需要完整 reasoning？（思考等级）
7. 这次优化到底有没有真的省钱？（效果验证 → 见"效果评估"）

①~④ 属于无损优化，⑤~⑥ 属于有风险优化（需分级闸门），⑦ 属于效果验证。

## 计费模式（Billing Mode）——缓存值多少钱，由你的付费方式决定

用户分成两类，省钱杠杆完全不同，**不要一刀切**：

| 模式 | 典型用户 | 缓存命中值钱吗 | skill 行为差异 |
|---|---|---|---|
| `api`（按量计费，默认）| API Key 直连、BYOK | **值钱**——命中部分按 10%~25% 计价 | R2 缓存提醒开启；prompt 强调静态前缀稳定、少切模型/会话 |
| `subscription`（套餐）| Claude Pro/Max、ChatGPT Plus、企业座席 | **不值钱**——已含在套餐里 | R2 降级为纯上下文管理（不提示缓存）；评估报告不报美元，只报 token 与成功率 |
| `auto` | 无法确定 | 未知 | 按 `api` 保守假设执行 |

- 判断依据：用户按 token 付钱 → api；按月付固定费用 → subscription。
- 配置位置：`config/token-wise.config.md` 的 `billing_mode`（懒加载会一并读取）。
- 注意：subscription 模式仍有**上下文窗口与限流**约束，Context Hygiene（L0）照常生效，只是不把缓存当省钱工具。

## 宿主能力检测（不要假装知道不知道的东西）

Agent **不一定能拿到**精确的 context token 数、cache hit/miss、TTL 剩余时间。

- **宿主暴露了 usage/context/cache/model 信息**（如 API 返回 usage、工具提供统计）→ 用实际数据判断。
- **宿主不提供** → 用保守估算：按对话轮数与内容量级粗估上下文占比，标注"估算值"，不下绝对结论。
- 禁止写死"Agent 能感知 TTL"这类假设；所有 TTL/缓存判断前先声明数据来源。

## 配置加载（懒加载协议，config 保留不删）

1. 开局只查 `preset:`、`redlines.reminders:`、`billing_mode:` 三行（约 30 token），不要整文件读入。
2. 命中默认值（balanced + reminders: true + api）→ 其余走 SKILL.md 内联默认。
3. 当前任务需要具体参数（context_ratio 档位、protected_tasks、router）时，才读对应小节。
4. 不回显全文。配置缺失/冲突 → 默认值并说明。冲突裁决：`protected_tasks` > 模块开关 > preset。
5. 懒加载只影响上下文占用（约 1K → 约 20 token），不影响功能。

## 红线守则（条件策略，非绝对规则）

> 红线是**行为级约束**，不可通过配置关闭；配置只控制是否主动提醒（`redlines.reminders`）。
> 提醒关闭 ≠ 红线失效。强烈建议用户自己遵守，效果最好。

| # | 红线（条件策略） | Agent 行为 |
|---|---|---|
| R1 | 管理上下文生命周期，不机械坚持同一会话 | 检测到"当前会话历史已变成噪音/超长"时，权衡继续 vs 整理 vs 新开：历史噪音大 + 上下文占比高 → 建议整理或新开（带小结）；否则继续。新开/切换前先输出进度小结 |
| R2 | 关注 Prompt Cache 命中，不机械追赶 TTL | 长时间中断后重新评估：上下文很大 + 中断久 + 缓存可能失效 + 历史噪音 → 建议整理/新开；否则直接继续。**不因"超 TTL"就催用户结束会话**。`billing_mode: subscription` 时此条降级为纯上下文管理（不提示缓存） |
| R3 | 索引按需使用 | 宿主有原生 repo map / 语义搜索 → 优先用；没有且项目复杂（>500 文件或跨模块修改）→ 才建议 `AI_INDEX.md`；小项目不强制 |
| R4 | 复杂任务先规划后执行 | 命中 `protected_tasks` 或复杂度高 → 先输出方案清单，用户确认后才动手 |

### 温馨提醒

- **R1 关于切模型**：缓存按模型/厂商隔离——同家切回（TTL 内且前缀未变）可能恢复命中，跨家完全失效。简单任务换便宜模型合理（见 router），但复杂任务中途别来回切。
- **R2 关于 TTL 数值**：Claude 系约 5 分钟（可扩展）、OpenAI 系约 5 分钟~1 小时，其余以官方为准。TTL 只影响计费折扣，不影响上下文可用性。
- **R3 关于索引**：Codex / Claude Code / Aider 已内置 repo map，优先用工具自带能力。

## 分级闸门（L0 Context / L1 Output / L2 Reasoning-Model）

| 级别 | 定位 | 手段 | 默认 |
|---|---|---|---|
| L0 Context 优化 | 减少垃圾 | 删冗余、精确搜索、按需读取、避免重复解释、上下文隔离（subagent）、缓存友好排序 | 永远开 |
| L1 Output 优化 | 减少表达 | 输出压缩（禁寒暄/diff-only/默认简版）、摘要历史、减少过程描述 | 按 preset |
| L2 Reasoning/Model 优化 | 动模型能力 | /compact 全量压缩、模型降档、降低 reasoning | 默认关，显式开启 |

**边界修正（不是"无损"的，要明说）**：
- **diff-only 是输出压缩（L1），不是 L0 无损**。默认"diff + 一行结果"；复杂修改（多文件/高风险）给"diff + 影响范围 + 风险 + 测试结果"；用户要求解释时恢复详细输出。
- **subagent 隔离是"减少上下文污染"（L0），不保证省 token**——subagent 自身也消耗 token（parent 指令 + subagent 输入/输出 + 回传摘要）。它的价值是防止探索结果污染主上下文。
- **force_precise_ref 用 auto，不强制**：用户给了精确位置直接用；没给 → agent 先做最小范围搜索；搜索范围明确不追问；范围巨大才询问用户。
- **router 是策略层，不是切换执行器**：agent 只做任务分类并**推荐** light/heavy；实际切换由宿主决定；宿主不支持动态切换时，改为提示用户手动切。

**Protected Tasks（禁压名单，命中则 L2 全禁、L1 仅输出压缩）**：
architecture_design, large_refactor, tricky_bug, teaching, security_review,
**payment, authentication, authorization, database_migration, production_incident,
data_migration, performance_optimization, api_contract_change, dependency_upgrade**

自动进名单信号：同一问题修正 ≥2 次；用户要求解释；任务涉支付/鉴权/权限/密钥；用户说"质量优先"。

## 上下文占比分级（替代写死的 token 阈值）

```
context_ratio = 当前上下文估算 / 模型 context window（宿主不提供则粗估）
  < 30%    正常，不干预
  30~50%   观察，留意历史增长
  50~70%   提醒整理：优先 /compact 或精简历史
  70~85%   强烈建议整理：或结束当前上下文、带小结新开
  > 85%    建议结束当前上下文（此时继续 = 高成本 + 注意力分散）
```

判断不只看 token 数，综合：context size + utilization + task state + cache status + correction count。

## 工作流

### 会话开局
1. 宿主能力检测（能否拿到 usage/cache/model 信息）。
2. 懒加载配置（preset / reminders 两行）。
3. 代码任务按 R3 判断索引策略。

### 会话执行中（每轮）
1. 七问自检（快速过，重点 ①③⑦）。
2. 按 L 级别执行：L0 手段常态生效；L1/L2 按闸门放行。
3. 上下文占比超 50% 时按分级提示（受 reminders 控制）。
4. 记录评估指标（见"效果评估"）。

### 会话收尾
1. 输出"进度小结 + 待办 + 下一步"（`context_hygiene.overnight_summary`）。
2. 输出/记录本次任务评估（见下）。

## 效果评估（核心模块：把"我觉得省了"变成"测出来省了"）

### 记录指标（每任务）
```
task: 任务名
model: 使用的模型
input_tokens / output_tokens / cache_hit(宿主提供则记)
retry_count / correction_count
task_success: true|false
```

### 估算成本
```
estimated_cost = input×P_in + output×P_out
  （有 cache 数据时：命中部分按缓存价计）
with_default = 按默认策略（不优化）估算
savings = 1 - estimated_cost / with_default
```

### 报告（用户输入 `/token-wise report` 时输出）
```
任务：auth 模块重构
模型：Sonnet 4.5
输入：32K ｜ 输出：4K ｜ 缓存命中：72% ｜ 重试：0 ｜ 修正：1
估算成本：$0.18        ← api 模式
默认策略估算：$0.31
节省：42% ｜ 任务成功：是
```
- `billing_mode: subscription` 时：报告改为只报 token 与成功率，美元成本显示为"等效 API 值（仅参考）"。

### 数据落地
- 记录到会话内即可；宿主支持时写入 `.token-wise/stats.json`（可用 `scripts/estimate_cost.py` 离线算账）。
- 有统计数据后，README 的可信度来自实测，而不是"理论上省"。

## Token 预算（本 skill 自身的成本）

- 常驻：SKILL.md（约 2K token）+ config 懒加载（三行，约 30 token）。
- 按需：references/*（几百 token）、config 小节（用到才读）。
- 总常驻约 2K token/会话。极简模式：只留红线 + 输出纪律时，删 config/ 与 references/ 单文件可跑。

## 资源说明

- `config/token-wise.config.md` — 用户唯一需要编辑的配置（预设 + 模块开关 + 红线提醒 + 豁免表）。
- `references/decision-tree.md` — 分级闸门 + 上下文占比判定（agent 查表）。
- `references/evaluation.md` — 效果评估指标与报告模板。
- `scripts/estimate_cost.py` — 离线成本估算脚本（可选）。
