# Token-Wise（省 token 不降智）

在**质量约束下**减少 AI 编码/对话中不必要的 token 与推理成本。面向 Claude Code / CodeBuddy / Cursor 等支持 SKILL.md 的 agent。

> 一句话：**先减少无效上下文和重复工作，再减少输出废话，最后才动模型能力。**
> 核心理念是 **Context Hygiene（有效上下文管理）**，不是"别开新会话"。

## 解决的问题

| 痛点 | 本 skill 的解法 |
|---|---|
| 僵尸会话：历史全是噪音，每轮白烧 token 还降智 | Context Hygiene：上下文占比分级 + 整理/收尾建议 |
| 输出废话多：寒暄、过程叙述 | L1 输出纪律：禁寒暄、diff 优先、默认简版 |
| 模糊提问导致全仓扫描 | precise_ref auto：先最小范围搜索，范围巨大才问用户 |
| 全量代码塞上下文，又贵又降智 | 索引按需：宿主原生索引优先，复杂项目才补 AI_INDEX |
| 为了省钱压缩上下文/降档，结果变笨 | 分级闸门 L0/L1/L2：有损手段默认关，按任务类型放行 |
| 复杂任务一路狂奔写错方向，返工烧更多钱 | R4：先规划后执行（模式二） |
| 不知道到底省没省钱 | **效果评估**：记录指标 → 估算成本 → `/token-wise report` |

## 核心设计：Context / Output / Reasoning 三层分级

- **L0 Context 优化（永远开）**：删冗余、精确搜索、按需读取、避免重复解释、subagent 隔离（减少上下文污染）、缓存友好排序
- **L1 Output 优化（按档位）**：输出压缩、摘要历史、减少过程描述
- **L2 Reasoning/Model 优化（默认关）**：/compact 全量压缩、模型降档、降低思考

边界诚实说明：**diff-only 是输出压缩（L1）不是无损**（复杂修改自动补影响范围/风险/测试）；**subagent 隔离是减少污染，不保证省 token**。

保护名单（`protected_tasks`）14 类：架构设计、大规模重构、疑难 bug、教学、安全审查、**支付、登录鉴权、权限控制、数据库迁移、生产故障、数据迁移、性能优化、API 契约变更、依赖升级**——永不进 L2。

## 概念澄清（别把四层混为一谈）

```
Conversation History（对话记录）→ Context（上下文）→ Prompt Cache（前缀缓存）→ Token Billing（计费）
```

**缓存过期 ≠ 上下文丢失 ≠ 必须开新会话**。TTL 失效只影响计费折扣；长会话噪音大才需要整理/新开。本 skill 用**上下文占比分级**（context_ratio：<30% 正常 / 50% 提醒 / 70% 强提醒 / >85% 建议结束）替代写死的 token 阈值，且不假装能感知缓存 TTL——宿主暴露数据才用实际值，否则保守估算。

## 效果评估（核心能力）

```
/token-wise report
任务：auth 模块重构
模型：Sonnet 4.5
输入：32K ｜ 输出：4K ｜ 缓存命中：72% ｜ 重试：0 ｜ 修正：1
估算成本：$0.18 ｜ 默认策略估算：$0.31 ｜ 节省：42% ｜ 任务成功：是
```

- 每任务记录：input/output tokens、cache hit（宿主提供才记）、retry/correction、task_success
- 落盘后可离线算账：`python scripts/estimate_cost.py .token-wise/stats.json`
- 累计 10~20 个任务后出汇总，README 的可信度来自实测，不是"理论上省"

## 安装

将 `token-wise/` 目录放到 agent 的 skills 目录：

- **Claude Code**：`~/.claude/skills/token-wise/`
- **WorkBuddy / CodeBuddy**：`~/.workbuddy/skills/token-wise/`
- 其他支持 SKILL.md 的 agent：按各自约定放置

## 配置

只改一个文件：`token-wise/config/token-wise.config.md`（**保留即可，不用删**）

1. **三档预设**：`preset: conservative / balanced / aggressive`
2. **模块开关**：输出纪律、输入瘦身、上下文卫生、思考控制、路由、评估——独立开/关/调参
3. **红线提醒开关**：见下节
4. **懒加载协议**：默认只查 `preset` 与 `redlines.reminders` 两行（约 20 token），其余字段按需读——不影响功能

## 红线守则（条件策略，请务必阅读）

4 条红线是**行为级约束**，不可通过配置关闭，但表述为**条件策略**而非绝对规则：

| # | 红线 | 条件/触发 |
|---|---|---|
| R1 | 管理上下文生命周期（不机械坚持同一会话）| 历史噪音大 + 上下文占比高 → 建议整理/新开（带小结）；否则继续 |
| R2 | 关注 Prompt Cache 命中（不机械追赶 TTL）| 长时间中断 + 上下文大 + 缓存可能失效 → 重新评估；**不因"超 TTL"催用户结束** |
| R3 | 索引按需使用 | 宿主有原生 repo map → 优先用；没有且项目复杂（>500 文件）→ 才建议 AI_INDEX.md |
| R4 | 复杂任务先规划后执行 | 命中保护名单或复杂度高 → 先出方案，确认后动手 |

> **温馨提醒**
> - 切模型：缓存按模型/厂商隔离——同家切回（TTL 内且前缀未变）可能恢复命中，跨家完全失效；简单任务换便宜模型合理，复杂任务中途别来回切。
> - TTL：Claude 系约 5 分钟（可扩展）、OpenAI 系约 5 分钟~1 小时，其余以官方文档为准。
> - 任务中断后：同一会话内直接继续即可；是否整理看上下文占比与噪音，不看中断时长。

> **强烈建议：红线请你自己遵守，效果远好于依赖 agent 提醒。**
> `redlines.reminders: false` 会让 agent 静默遵守、不打扰你（适用于已明白道理的用户）。
> **关闭提醒不代表红线失效**，agent 的行为约束依然执行，只是不再主动啰嗦。

## 会不会降智？

- L0（Context 优化）：永不降智，越用越省还更聪明。
- L1（Output 优化）：有信息密度取舍——复杂修改自动补影响范围/风险/测试，用户要解释就恢复详细。
- L2（Reasoning/Model 优化）：默认关闭或分级放行；保护名单内任务永不降智。
- 最大的"降智"来源其实是**僵尸会话**（上下文噪音）——本 skill 的主战场正是治理它。

## 本 skill 自身的 token 成本

- 常驻：SKILL.md（约 2K token）+ config 懒加载（约 20 token）。
- 按需：references/、config 小节（用到才读）。
- 总常驻约 **2K token/会话**。极简模式：只需红线 + 输出纪律时，删 config/ 和 references/，单文件 SKILL.md 可跑。

## 常见问题

**Q: aggressive 档会降智吗？**
A: 会，在某些任务上有风险。它允许 L2（compact/降档）。发现质量下降就退回 balanced 或 conservative。

**Q: 同一个对话切换模型会影响缓存吗？**
A: 会。缓存按模型/厂商隔离——同家切回（TTL 内且前缀未变）可能恢复命中；不同家完全失效。复杂任务中途不要来回切。

**Q: router 会自己切模型吗？**
A: 不会。router 是策略层——agent 只做任务分类并推荐档位，实际切换由宿主执行；宿主不支持时提示你手动切。

**Q: 配置写坏了怎么办？**
A: 删掉配置文件或用默认 preset，agent 会按默认值执行并提示。

**Q: 支持非 Claude 模型吗？**
A: 支持。router 留空即不干预模型选择，机制本身与厂商无关。

## Roadmap

- [x] v1：无损优先 + L0/L1/L2 分级 + 红线
- [x] v2：概念澄清（History/Context/Cache/Billing）、Context Hygiene、上下文占比分级
- [x] v3：效果评估 + 离线成本脚本
- [ ] benchmark：同一批真实 coding tasks 对比默认 / balanced / aggressive，输出 token reduction、cost reduction、task success rate、retry rate、quality regression

## License

MIT
