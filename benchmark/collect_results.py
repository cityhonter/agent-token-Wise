#!/usr/bin/env python3
"""Token-Wise benchmark 汇总脚本。

用法:
  python benchmark/collect_results.py <stats1.json> [<stats2.json> ...]

每个 stats 文件 = 一组配置的全部任务记录（数组）。输出 markdown 对比表。

指标: 任务数 / 成功率 / token 总量 / 估算成本 / 节省% / 平均重试 / 平均修正
价格默认 $3/$15 每百万；缓存命中按输入价 10%（仅 api 计费，见 token-wise.config.md）。
"""
import json
import sys
from pathlib import Path

PIN = 3.0 / 1_000_000
POUT = 15.0 / 1_000_000
CACHE_RATIO = 0.1


def load(path: str) -> list[dict]:
    raw = Path(path).read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


def cost_of(t: dict) -> float:
    inp = float(t.get("input_tokens", 0))
    out = float(t.get("output_tokens", 0))
    hit = float(t.get("cache_hit_pct", 0) or 0) / 100
    return inp * PIN * (1 - hit) + inp * PIN * CACHE_RATIO * hit + out * POUT


def summarize(name: str, tasks: list[dict]) -> dict:
    n = len(tasks)
    if n == 0:
        return {"name": name, "n": 0}
    success = sum(1 for t in tasks if t.get("task_success"))
    tokens_in = sum(int(t.get("input_tokens", 0)) for t in tasks)
    tokens_out = sum(int(t.get("output_tokens", 0)) for t in tasks)
    cost = sum(cost_of(t) for t in tasks)
    retry = sum(int(t.get("retry_count", 0)) for t in tasks)
    corr = sum(int(t.get("correction_count", 0)) for t in tasks)
    return {
        "name": name, "n": n,
        "success_rate": success / n * 100,
        "tokens": tokens_in + tokens_out,
        "cost": cost,
        "retry_avg": retry / n,
        "corr_avg": corr / n,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    groups = [(Path(p).stem, load(p)) for p in sys.argv[1:]]
    rows = [summarize(n, t) for n, t in groups]
    rows = [r for r in rows if r["n"] > 0]
    if not rows:
        print("没有有效任务记录。")
        return

    base = rows[0]
    print(f"| 组 | 任务数 | 成功率 | 总 token | 估算成本 | 省 vs 对照 | 平均重试 | 平均修正 |")
    print(f"|---|------:|------:|-------:|-------:|-------:|------:|------:|")
    for r in rows:
        vs = f"-" if r is base else f"{(1 - r['cost'] / base['cost']) * 100:.0f}%"
        print(f"| {r['name']} | {r['n']} | {r['success_rate']:.0f}% "
              f"| {r['tokens']:,} | ${r['cost']:.2f} | {vs} "
              f"| {r['retry_avg']:.1f} | {r['corr_avg']:.1f} |")

    print("\n说明：'省 vs 对照' 以第一个文件（对照组）为基线；成功率下降与重试上升 = 质量回归信号。")


if __name__ == "__main__":
    main()
