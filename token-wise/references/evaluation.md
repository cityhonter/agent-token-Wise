# 效果评估（Evaluation）

> 目标：把"我觉得省了"变成"测出来省了"。
> 原则：**有数据才有结论**——任何"省了 X%"的宣称必须有统计支撑。

## 记录指标（每个任务一条）

```json
{
  "task": "auth 模块重构",
  "model": "claude-sonnet-4-5",
  "input_tokens": 32000,
  "output_tokens": 4000,
  "cache_hit_pct": 72,
  "retry_count": 0,
  "correction_count": 1,
  "task_success": true,
  "notes": "用了模式二，规划 1 轮"
}
```

- `cache_hit_pct`：仅当宿主暴露缓存统计时记录；否则省略，成本估算按无缓存计（保守）。
- `task_success`：任务是否一次通过验收（核心质量指标）。

## 成本估算

```
estimated_cost = input×P_in×0.001 + output×P_out×0.001     # P 为每百万 token 价格
  （有 cache_hit 时：input 的命中部分按缓存价计，未命中部分按全价）

with_default   = 同一任务按"不优化"策略的估算（输入按实际发生的探索量粗估）

savings = 1 - estimated_cost / with_default
```

价格默认取：P_in=3, P_out=15（美元/百万，示意）；实际用宿主或用户配置的价格。

## 报告模板（`/token-wise report`）

```
任务：auth 模块重构
模型：Sonnet 4.5
输入：32K ｜ 输出：4K ｜ 缓存命中：72% ｜ 重试：0 ｜ 修正：1
估算成本：$0.18
默认策略估算：$0.31
节省：42% ｜ 任务成功：是
```

- 单任务报告：当前任务结束后输出。
- 汇总报告：`/token-wise report all`——输出近期 N 个任务的平均节省、成功率、返工率。

## 数据落地

1. 会话内：直接输出即可，不落盘。
2. 落盘（`evaluation.save_stats: true` 时）：追加到 `.token-wise/stats.json`。
3. 离线算账：`python scripts/estimate_cost.py .token-wise/stats.json`——输出按任务/按模型的汇总。

## 何时启用

- 想验证 skill 效果 / 写 README 数据时：开启 `save_stats`，跑 10~20 个真实任务后出报告。
- 日常使用：只输出单任务报告（开销极小，一次计算）。

## 与基准对比（A/B）

- 对照组：关闭 token-wise（或 preset: conservative）跑同类任务。
- 对比指标：token reduction / cost reduction / task success rate / retry rate / quality regression。
- 样本量 ≥ 10 个任务再下结论，避免小样本噪声。
