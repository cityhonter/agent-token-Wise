# Benchmark 运行协议（A/B 对比）

> 目标：用同一批真实编码任务，量化 Token-Wise 的实际收益与质量影响。
> 产出：README 可引用的实测数据（token reduction / cost reduction / success rate / retry rate / quality regression）。

## 三组配置

| 组 | 配置 | 用途 |
|---|---|---|
| Control（对照组）| 不加载 token-wise（或 preset: conservative）| 基线 |
| Balanced | preset: balanced + billing_mode: api | 推荐组 |
| Aggressive | preset: aggressive | 上限测试（预期可能有质量回归）|

## 前置条件

1. 同一宿主 Agent（Claude Code / CodeBuddy 等，固定模型档位，例如 Sonnet）。
2. 同一份任务代码基线（git 分支分别建：`bench-control` / `bench-balanced` / `bench-aggressive`）。
3. 至少 10 个任务（12 个全跑更好），避免小样本噪声。
4. 每任务独立会话开始（避免跨任务污染），但**同一任务的三组都从同一基线开始**。

## 执行步骤

1. 读 `tasks.md`，按 T01→T12 顺序执行。
2. 每组跑全部任务，每任务结束后用 `/token-wise report`（或 stats 记录）收集数据。
3. 每任务记录一条 JSON 到 `.token-wise/bench-<组名>.json`（数组形式）。
4. 全部跑完后运行汇总脚本：
   ```
   python benchmark/collect_results.py .token-wise/bench-control.json .token-wise/bench-balanced.json .token-wise/bench-aggressive.json
   ```

## 控制变量（必须遵守）

- **模型固定**：三组同一模型；模型切换测试另算，不混入本 benchmark。
- **提示词一致**：任务描述原样粘贴，不因组别改写。
- **用户介入最小化**：correction 计数口径统一（用户指出问题才算一次）。
- **环境一致**：同仓库、同依赖版本、同 Node/Python 版本。

## 结果判定

| 指标 | 期望 |
|---|---|
| token reduction（balanced vs control）| 明显下降（目标 ≥30%）|
| cost reduction | 随 token + 缓存命中下降 |
| task success rate | 不下降（或下降 <10% 视为可接受）|
| retry / correction | 不上升 |
| quality regression | aggressive 组允许部分任务质量打折，需逐条记录 |

**结论模板（写入 README）**：
```
在 12 个真实编码任务上（Vue3/JS 项目），Token-Wise balanced 相比默认 Agent：
平均减少输入 token XX%，成本降低 XX%，任务成功率 XX%（对照 XX%），
重试率 XX%（对照 XX%），无质量回归；aggressive 组在 TXX 出现质量打折。
```

## 报告生成

`collect_results.py` 输出 markdown 对比表，直接贴进 README 的「Benchmark 结果」章节。
