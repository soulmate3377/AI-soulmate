"""
Read back the observations and print them.

把观测记录读回来打印成人看得懂的报告。

Usage / 用法
    python _tools/report.py            # last 7 days / 最近 7 天
    python _tools/report.py 30         # last 30 days / 最近 30 天

Why this exists / 为什么要有它
----------------------------
"She reads him badly" has two very different causes:

    understanding actually failed and fell back to keyword rules, or
    understanding worked and was simply not smart enough.

They need opposite fixes. This report tells you which one you have.
"她读不懂他"有两种完全不同的病因：

    理解调用失败了、回退到关键词规则，或者
    理解调用成功了、只是不够聪明。

两者要的药完全相反。这份报告告诉你属于哪一种。
"""

import sys
from pathlib import Path

# Make the repo importable when run as a plain script.
# 以普通脚本方式运行时，让仓库能被 import。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import observe  # noqa: E402


def bar(fraction, width=28):
    """
    A cheap text bar, so a rate is readable at a glance.

    一个廉价的文本条，让比例一眼能看出来。
    """

    if fraction is None:
        return ""

    filled = int(round(max(0.0, min(1.0, fraction)) * width))

    return "#" * filled + "." * (width - filled)


def main():
    days = 7

    if len(sys.argv) > 1:
        try:
            days = max(1, int(sys.argv[1]))
        except ValueError:
            print(f"用法: python _tools/report.py [天数]   (给的是 {sys.argv[1]!r})")
            return 2

    s = observe.summary(days=days)

    print("=" * 62)
    print(f"Observations report / 观测报告   最近 {days} 天")
    print("=" * 62)

    if not s["events"]:
        print()
        print("No observations yet. / 还没有任何记录。")
        print()
        print("说明：")
        print("  - 观测文件在数据目录的 memory/metrics/ 下，一天一个 .jsonl")
        print("  - 跑几轮对话（GUI 或 companion.py）之后再看这里")
        print("  - 如果设了 ECHO_METRICS_OFF=1，观测是关掉的")
        return 0

    print(f"总记录条数: {s['events']}")
    print()

    # ---- 理解端 ----
    print("-" * 62)
    print("理解端 / Understanding")
    print("-" * 62)
    print(f"  对话轮数        : {s['turns']}")
    print(f"  正常            : {s['understand_ok']}")
    print(f"  回退到规则分析  : {s['understand_fallback']}")

    rate = s["fallback_rate"]

    if rate is None:
        print("  回退率          : (没有轮数数据)")
    else:
        print(f"  回退率          : {rate * 100:.1f}%  [{bar(rate)}]")
        print()
        if rate == 0:
            print("  -> 理解端没失败过。'读不懂' 不是故障导致的，")
            print("     要往提示词 / 模型 / 上下文方向找原因。")
        elif rate < 0.05:
            print("  -> 偶尔回退，属于容错正常范围。")
        else:
            print("  -> 回退偏多。先修理解端的预算和输出约束，")
            print("     再谈提示词优化 —— 否则你是在调一个没在跑的东西。")

    if s["error_reasons"]:
        print()
        print("  失败病因 / why it failed:")
        for reason, n in sorted(
            s["error_reasons"].items(), key=lambda kv: -kv[1]
        ):
            hint = {
                "empty_content": "思考吃光了 max_tokens，json 没吐出来",
                "bad_json": "返回了不是合法 json 的内容",
                "schema": "json 合法但字段结构不对",
            }.get(reason, "")
            print(f"    {reason:<18} {n:<4} {hint}")

    if s["fallback_reasons"]:
        print()
        print("  回退记录 / fallback entries:")
        for reason, n in sorted(
            s["fallback_reasons"].items(), key=lambda kv: -kv[1]
        ):
            print(f"    {reason:<18} {n}")

    # ---- 意愿值 ----
    print()
    print("-" * 62)
    print("意愿值 / Willingness")
    print("-" * 62)

    samples = s["willingness_samples"]

    if not samples:
        print("  (没有记录到变化)")
        print("  只在数字真的动了时才会记一条，所以'没有'通常表示一直没变。")
    else:
        values = [v for _, v, _ in samples]

        print(f"  变化次数: {len(samples)}")
        print(f"  区间    : {min(values):.2f} ~ {max(values):.2f}")
        print(f"  最新    : {values[-1]:.2f}")
        print()
        print("  最近的变化（旧 -> 新）:")

        for t, v, level in samples[-12:]:
            print(f"    {t}  {v:.2f}  ({level or '-'})")

        first, last = values[0], values[-1]
        drift = last - first

        print()
        if abs(drift) < 0.02:
            print(f"  -> 整体基本没动（{drift:+.2f}）。")
        elif drift > 0:
            print(f"  -> 整体在往上走（{drift:+.2f}）。")
        else:
            print(f"  -> 整体在往下掉（{drift:+.2f}）。")
            print("     注意：目前的下限是 DROP_CAP（每天最多比开盘低 0.15），")
            print("     而且第二天会重新掷骰子 —— 也就是坏状态不会累积。")

    # ---- 主动开口 ----
    print()
    print("-" * 62)
    print("主动开口 / Proactive attempts")
    print("-" * 62)

    attempts = s["proactive_attempts"]

    if not attempts:
        print("  (这段时间没有主动开口的决策记录)")
    else:
        blocked = s["proactive_blocked"]
        block_rate = blocked / attempts if attempts else 0.0

        print(f"  决策次数: {attempts}")
        print(f"  真的开口: {attempts - blocked}")
        print(f"  被拦下  : {blocked}")
        print(f"  拦下比例: {block_rate * 100:.1f}%  [{bar(block_rate)}]")
        print()
        print("  关心这个数字，是因为它把'她的意愿'和'实际行为'连了起来：")
        print("  如果拦下比例近乎 100%，说明守门人把她的主动性全吃掉了；")
        print("  如果接近 0%，说明门槛对她不构成约束。")

    print()
    print("=" * 62)
    print("文件位置 / where the raw data lives:")
    print(f"  <数据目录>/{observe._DIR_NAME}/")
    print("=" * 62)

    return 0


if __name__ == "__main__":
    sys.exit(main())
