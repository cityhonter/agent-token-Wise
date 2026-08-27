#!/usr/bin/env python3
"""Token-Wise 离线成本估算脚本。

用法:
  python estimate_cost.py stats.json [--prices prices.json]

stats.json 格式（由 evaluation 模块生成，每行一个任务 JSON 或 JSON 数组）:
  {"task": "auth 重构", "model": "sonnet", "input_tokens": 32000,
   "output_tokens": 4000, "cache_hit_pct": 72,
   "retry_count": 0, "correction_count": 1, "task_success": true}

prices.json（可选，默认: 输入 $3 / 输出 $15 / 缓存命中按输入价 10%）:
  {"input_per_m": 3.0, "output_per_m": 15.0, "cache_ratio": 0.1}
"""
import json
import sys
from pathlib import Path

DEFAULT_PRICES = {"input_per_m": 3.0, "output_per_m": 15.0, "cache_ratio": 0.1}


def load_prices(path: str | None) -> dict:
    if not path:
        return DEFAULT_PRICES
    with open(path, encoding="utf-8") as f:
        return {**DEFAULT_PRICES, **json.load(f)}


def load_stats(path: str) -> list[dict]:
    raw = Path(path).read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


def cost_of(task: dict, prices: dict) -> tuple[float, float]:
    """返回 (实际估算成本, 无优化默认估算成本)。"""
    pin = prices["input_per_m"] / 1_000_000
    pout = prices["output_per_m"] / 1_000_000
    pcache = pin * prices["cache_ratio"]

    inp = float(task.get("input_tokens", 0))
    out = float(task.get("output_tokens", 0))
    hit = float(task.get("cache_hit_pct", 0) or 0) / 100

    actual = inp * pin * (1 - hit) + inp * pcache * hit + out * pout
    # 默认策略估算：按无缓存 + 探索量放大 1.5 倍（未优化时常见多读文件）
    default = inp * 1.5 * pin + out * pout
    return actual, default


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    prices = load_prices(sys.argv[2] if len(sys.argv) > 2 else None)
    tasks = load_stats(sys.argv[1])
    if not tasks:
        print("无任务记录。")
        return

    total_actual = total_default = 0.0
    successes = 0
    for t in tasks:
        a, d = cost_of(t, prices)
        total_actual += a
        total_default += d
        if t.get("task_success"):
            successes += 1
        saved = (1 - a / d) * 100 if d else 0
        print(f"- {t.get('task', '?')} [{t.get('model', '?')}]: "
              f"${a:.2f} (默认 ${d:.2f}, 省 {saved:.0f}%)")

    n = len(tasks)
    print(f"\n共 {n} 个任务 | 成功 {successes}/{n} "
          f"({successes / n * 100:.0f}%) | "
          f"总成本 ${total_actual:.2f} vs 默认 ${total_default:.2f} "
          f"| 总节省 {(1 - total_actual / total_default) * 100:.0f}%")


if __name__ == "__main__":
    main()
