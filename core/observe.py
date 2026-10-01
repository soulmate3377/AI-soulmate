# observe.py
#
# Observations: a local, append-only record of how she behaved.
# 观测层：把她的行为记成一份本地的、只追加的记录。
#
# ==================================================
# Why this exists
# --------------------------------------------------
# Two things were invisible, and invisible meant unfixable:
#
#   1. Understanding silently falls back to keyword rules. When the
#      understanding call fails, brain gets None and quietly swaps in the
#      rule analyzers. The chat keeps working, so nobody notices -- but
#      "she reads him badly" is then caused by a bug, not by a weak model.
#
#   2. Willingness only exists as a current value. You can see the number
#      today and nothing about which way it has been drifting.
#
# Both can only be answered with history. Hence this file.
# ==================================================
# 为什么要有这个文件
# --------------------------------------------------
# 有两件事以前完全不可见，而不可见就没法修：
#
#   1. 理解端会静默回退到关键词规则。理解调用失败时 brain 拿到 None，
#      悄悄换成规则分析。聊天照常，所以没人发现——于是"她读不懂他"
#      可能是 bug 造成的，而不是模型不够聪明。
#
#   2. 意愿值只有一个"现在是多少"，看不出这几天在往哪边走。
#
# 这两个问题只能靠历史回答，所以有了这个文件。
#
# ==================================================
# Rules this file obeys
# --------------------------------------------------
# - note() never raises. Observability must not be able to break a chat.
# - Append-only JSONL: one json object per line. A crash loses at most the
#   last line, and no read-modify-write of a whole file is ever needed.
# - One file per local day, in memory/metrics/. Old files are left alone.
# - Set ECHO_METRICS_OFF=1 to turn it off entirely.
# ==================================================
# 这个文件遵守的规矩
# --------------------------------------------------
# - note() 永不抛异常。观测绝不该把聊天搞挂。
# - 只追加的 JSONL：一行一个 json 对象。崩溃最多丢最后一行，
#   也不需要"读整个文件再写回去"。
# - 按本地日期一天一个文件，放在 memory/metrics/。旧文件不清理。
# - 设 ECHO_METRICS_OFF=1 可整体关掉。
#
# ==================================================
# DO NOT DELETE THIS MODULE
# --------------------------------------------------
# It is the measurement rig. The only way to know whether a change to her
# behaviour actually worked is to compare the numbers before and after.
# Without it, every tweak is a guess.
# ==================================================
# 不要删掉这个模块
# --------------------------------------------------
# 它是测量装置。想判断一次改动有没有真的生效，唯一办法就是对比改前改后的
# 数字。没有它，每次调整都只是凭感觉。

import json
import os

from datetime import datetime, timedelta
from pathlib import Path

from core.paths import data_dir


# =========================
# 开关与路径
# =========================

_DIR_NAME = "memory/metrics"

# 环境变量设成 1 / true / yes 就整个关掉。
# Any truthy value turns observation off.
_OFF_VALUES = {"1", "true", "yes", "on"}


def enabled():
    """
    Whether observation is switched on.

    观测是否开启。
    """

    return _enabled_raw()


def _dir():
    """
    The metrics directory, created on demand.

    指标目录，按需创建。
    """

    d = Path(data_dir()) / _DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _file_for(day):
    """
    Path of one day's file, e.g. memory/metrics/2026-09-30.jsonl

    某一天的文件路径。
    """

    return _dir() / f"{day}.jsonl"


# =========================
# 写入
# =========================

def note(kind, **fields):
    """
    Append one observation. Never raises, never returns anything useful.

    追加一条观测记录。永不抛异常，也不返回有意义的东西。

    kind    short event name, e.g. "understand_ok" / "understand_fallback"
    fields  any json-serialisable context. Keep the field names stable --
            the report groups by them.

    kind    事件短名，例如 understand_ok / understand_fallback
    fields  任何可 json 序列化的上下文。字段名要保持稳定，报告按它聚合。
    """

    try:

        if not _enabled_raw():
            return

        # Objects / exceptions are not json-serialisable; keep the record
        # cheap and never let a bad field kill the write.
        # 对象和异常不能直接 json 序列化，转成字符串，别让一个坏字段毁掉写入。
        safe = {}

        for k, v in fields.items():

            if v is None or isinstance(v, (str, int, float, bool)):

                safe[k] = v

            else:

                safe[k] = str(v)[:200]

        record = {
            "t": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "kind": str(kind),
        }

        record.update(safe)

        line = json.dumps(record, ensure_ascii=False)

        day = datetime.now().strftime("%Y-%m-%d")

        with open(_file_for(day), "a", encoding="utf-8") as f:

            f.write(line + "\n")

    except Exception:

        # Swallow everything. A metrics failure must never surface to the user.
        # 全部吞掉。指标写入失败绝不能冒到用户面前。
        return


def _enabled_raw():
    """
    The actual on/off check, kept separate so note() stays readable.

    真正的开关判断，单独放一个函数，让 note() 保持好读。
    """

    raw = os.environ.get("ECHO_METRICS_OFF", "").strip().lower()

    if raw == "":

        return True

    return raw not in _OFF_VALUES


# =========================
# 读取
# =========================

def read_events(days=7):
    """
    Read back the last `days` days of observations, oldest first.

    读回最近 days 天的观测记录，旧的在前面。

    A corrupt line is skipped rather than raising: a half-written last line
    is expected after a hard kill, and it should not hide the good data.
    坏行直接跳过而不是抛异常：硬杀进程后留下半行是正常的，不该因此看不到好数据。
    """

    out = []

    try:

        today = datetime.now().date()

        for i in range(days - 1, -1, -1):

            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")

            path = _file_for(day)

            if not path.exists():

                continue

            with open(path, "r", encoding="utf-8") as f:

                for line in f:

                    line = line.strip()

                    if not line:

                        continue

                    try:

                        out.append(json.loads(line))

                    except ValueError:

                        continue

    except Exception:

        return out

    return out


def summary(days=7):
    """
    Aggregate the last `days` days into the handful of numbers that matter.

    把最近 days 天聚合成本文件顶部说的那几个真正重要的数字。

    Returns a plain dict so the caller can print it or render it.
    返回普通 dict，调用方可以打印它或渲染它。
    """

    events = read_events(days=days)

    result = {
        "days": days,
        "events": len(events),
        "turns": 0,
        "understand_ok": 0,
        "understand_fallback": 0,
        "fallback_reasons": {},
        "error_reasons": {},
        "willingness_samples": [],
        "proactive_attempts": 0,
        "proactive_blocked": 0,
    }

    for e in events:

        kind = e.get("kind")

        if kind == "understand_ok":

            result["turns"] += 1

            result["understand_ok"] += 1

        elif kind == "understand_fallback":

            result["turns"] += 1

            result["understand_fallback"] += 1

            reason = str(e.get("reason") or "unknown")

            result["fallback_reasons"][reason] = (
                result["fallback_reasons"].get(reason, 0) + 1
            )

        elif kind == "understand_error":

            # The precise cause: empty_content / bad_json / schema.
            # perception.py knows this, brain.py only knows "it failed".
            # 精确病因：empty_content / bad_json / schema。
            # perception.py 知道，brain.py 只知道"失败了"。
            reason = str(e.get("reason") or "unknown")

            result["error_reasons"][reason] = (
                result["error_reasons"].get(reason, 0) + 1
            )

        elif kind == "willingness":

            w = e.get("willingness")

            if isinstance(w, (int, float)):

                result["willingness_samples"].append(
                    (e.get("t"), float(w), e.get("level"))
                )

        elif kind == "proactive":

            result["proactive_attempts"] += 1

            if e.get("allowed") is False:

                result["proactive_blocked"] += 1

    turns = result["turns"]

    result["fallback_rate"] = (
        round(result["understand_fallback"] / turns, 4) if turns else None
    )

    return result
