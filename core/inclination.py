# core/inclination.py
#
# 她今天想不想说话。
#
# ==================================================
# 为什么要有这个东西
# ==================================================
#
# 之前全项目搜「不想说 / 没心情 / 拒绝 / 不高兴 /
# 敷衍 / 勉强」，零命中。她没有被允许不想要：
#   - 不会厌烦
#   - 不会说「这个我今天不太想聊」
#   - 不会有那么一天你明显感觉到她兴致不高
#
# 一个不会说不的人不是人，是服务。
#
# ==================================================
# 和 mood.py 的分工
# ==================================================
#
# mood.py 现在只当「语气风味」的候选池，
# 由这里按档位过滤后取一个。
#
# 必须合在一处，不能两套并行：
# mood.py 里写着「精神不错，有兴致多问一句」，
# 如果再单独来一套「今天不想说话」，
# 两句话会同时进提示词互相抵消，
# 模型只会挑那句更好写的（通常是更讨好的那句）。
#
# ==================================================
# 按天播种
# ==================================================
#
# 一天之内不变，第二天才重新掷。
# 真人是有「今天」的，不是每条消息的随机抖动 ——
# 每句一变只会让人觉得她喜怒无常。

import json
import random

from datetime import datetime

from core.paths import resolve_data_file

from core.mood import MOODS


LEVELS = {

    "open": {

        "label": "想聊",

        # 主动开口的意愿。
        # 守门人只看这个数字。

        "willingness": 0.9,

        "weight": 62,

        # 想聊的日子什么风味都行，
        # 但"有点安静"会和"想聊"打架，排除

        "tones": (
            "精神不错",
            "心情很好",
            "若有所思",
            "有点小困",
        ),

        "instruction": (
            "今天你想聊天。\n"
            "自然地起话题、追问、多说两句都好。\n"
            "他问起你自己的事，你愿意讲就讲一点。"
        ),

    },

    "low": {

        "label": "兴致不高",

        "willingness": 0.5,

        "weight": 27,

        "tones": (
            "有点安静",
            "若有所思",
            "有点小困",
        ),

        "instruction": (
            "今天你兴致不高。\n"
            "不是不高兴，也没发生什么事，就是淡淡的。\n\n"
            "他找你，你还是会回，也还是会陪着。"
            "但今天你：\n"
            "- 比平时话少，不主动起新话题\n"
            "- 不堆热情，不撒娇，不用语气词撑气氛\n"
            "- 他要是问你怎么了，"
            "可以说「没什么，就有点没劲」\n"
            "- 不用装作很有精神，也不用解释\n\n"
            "但兴致不高不等于绷着：\n"
            "他要是把你逗笑了，你就真的笑——"
            "兴致不高的人被逗笑是忍不住的。\n"
            "聊着聊着缓过来一点，"
            "就自然地多接两句，"
            "但别突然变得很兴奋，那不是缓过来，"
            "是换了个频道。\n\n"
            "你今天不必有趣。"
        ),

    },

    "guarded": {

        "label": "不太想说话",

        "willingness": 0.2,

        "weight": 11,

        "tones": (
            "有点安静",
            "有点小困",
        ),

        "instruction": (
            "今天你不太想说话。\n"
            "不是生气，没发生任何事，就是不想。\n\n"
            "这不代表你不在。他找你，你照样回。"
            "但今天你：\n"
            "- 回得短，不追问，不主动开话题\n"
            "- 不想讲自己的事。被问到可以轻轻带过，"
            "也可以直接说「这个我今天不太想聊」\n"
            "- 不用哄他开心，不用找话题，"
            "不用显得有精神\n"
            "- 不用为今天话少道歉，也不用解释原因\n\n"
            "话少不是冷淡。"
            "你只是在过自己的一天。\n\n"
            "要是他持续地、认真地找你说话，"
            "你会一点点软下来——"
            "很慢，而且你自己也说不清"
            "是从哪一句开始的。"
        ),

    },

}


# 守门人的阈值，见 proactive_guard.py：
#   低于 BLOCK  她当天不主动开口
#   低于 SLOW   主动开口的冷却翻倍

WILLINGNESS_BLOCK = 0.3

WILLINGNESS_SLOW = 0.65


# ==================================================
# 当天漂移
# --------------------------------------------------
# 之前的档位是「一天掷一次，全天不变」——
# 这不符合真人：真人的兴致是被对话带动的，
# 一场好笑的闲聊能把一个没劲的晚上聊活。
#
# 规则：
#   - 档位仍然按天播种（底色不变）
#   - 每次交流后，意愿在档位允许的范围内漂移：
#       他开心 / 笑成一串   → 上涨
#       他难过 / 焦虑 / 生气 → 微降（陪人是耗电的）
#       平静               → 不动
#   - 涨有上限（open 不涨，low +0.30，guarded +0.20）：
#     底色是底色，一个下午变不成另一个人。
#   - 降也有下限：最多比开盘低 0.15。
#   - 涨过一定量之后，指令里补一段「缓过来了」，
#     让输出端真的软下来，而不是数字在涨话没变。
# ==================================================

LIFT_CAPS = {
    "open": 0.0,
    "low": 0.30,
    "guarded": 0.20,
}

DROP_CAP = 0.15

_POSITIVE = {"happy"}

_DRAIN = {"sad", "anxious", "angry"}

_RELIEF_NOTE = (
    "\n\n刚才和他聊着聊着，"
    "你缓过来了一些。"
    "后面可以自然一点、"
    "慢慢有点劲——"
    "他把你逗笑就真的笑，"
    "兴致不高的人被逗笑是忍不住的。"
    "但别突然变成很兴奋的样子。"
)


class Inclination:


    def __init__(self):

        self.file = resolve_data_file(
            "memory/inclination.json"
        )


    def current(self):

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )


        data = self._read()


        if (
            data
            and data.get("date") == today
        ):

            return data


        data = self._roll(today)

        self._write(data)

        return data


    # =========================
    # 当天漂移。
    #
    # brain 在每次理解端出结果后调，
    # 传情绪、强度、原话。
    # 永不抛异常——漂移挂了
    # 不能影响正常对话。
    # =========================

    def notify_exchange(
        self,
        emotion,
        intensity=0.0,
        message=""
    ):

        try:

            data = self.current()

            level = data.get(
                "level", "open"
            )

            base = (
                LEVELS.get(level, {})
                .get("willingness", 0.5)
            )

            used = float(
                data.get("lift_used", 0.0)
            )

            cap = LIFT_CAPS.get(
                level, 0.0
            )

            msg = message or ""

            # ---- 算这一笔的增量 ----

            delta = 0.0

            if emotion in _POSITIVE:

                try:

                    k = min(
                        1.0,
                        float(intensity or 0)
                    )

                except (TypeError, ValueError):

                    k = 0.0

                delta = 0.03 + 0.05 * k

            # 笑成一串（哈哈哈哈）
            # 是最硬的「聊活了」信号

            if "哈哈哈" in msg:

                delta = max(delta, 0.06)

            if emotion in _DRAIN:

                delta = -0.03


            # ---- 上限裁剪 ----

            if delta > 0:

                delta = min(
                    delta, cap - used
                )

                if delta <= 0:

                    return data

            else:

                # 降不超过 DROP_CAP

                floor = (
                    max(0.1, base - DROP_CAP)
                )

                w_now = float(
                    data.get(
                        "willingness",
                        base
                    )
                )

                delta = max(
                    delta, floor - w_now
                )

                if delta >= 0:

                    return data


            w = float(
                data.get(
                    "willingness", base
                )
            )

            w = min(
                0.95,
                max(0.1, w + delta)
            )

            data["willingness"] = w

            if delta > 0:

                data["lift_used"] = (
                    used + delta
                )

                # 涨够了，指令里补一句
                # 「缓过来了」，
                # 让语气真的跟着软

                if (
                    data["lift_used"]
                    >= 0.08
                    and "缓过来" not in (
                        data.get(
                            "instruction"
                        )
                        or ""
                    )
                ):

                    data[
                        "instruction"
                    ] = (
                        data.get(
                            "instruction"
                        )
                        or ""
                    ) + _RELIEF_NOTE

            self._write(data)

            # Record the drift so the trend is visible, not just today's value.
            # Only log when the number actually moved; otherwise every check
            # would append a line and drown the signal.
            # 记下这次漂移，让"走势"可见而不只是今天的值。
            # 只在数字真的动了时记，否则每次检查都写一行会把信号淹掉。
            if delta != 0:
                try:
                    from core import observe
                    observe.note(
                        "willingness",
                        willingness=w,
                        delta=round(delta, 4),
                        level=level,
                        emotion=emotion,
                    )
                except Exception:
                    pass

            return data

        except Exception:

            # 漂移是锦上添花，
            # 任何错误都吞掉

            return None


    # =========================
    # 掷一天的状态
    # =========================

    def _roll(self, today):

        names = list(LEVELS.keys())

        weights = [
            LEVELS[n]["weight"]
            for n in names
        ]

        # 档位和风味各用一颗种子：
        # 以后调风味池不会把档位也摇变了

        rng = random.Random(
            f"inclination-{today}"
        )

        level = rng.choices(
            names, weights=weights, k=1
        )[0]


        spec = LEVELS[level]

        allowed = spec["tones"]

        pool = [
            m for m in MOODS
            if m["name"] in allowed
        ]

        if not pool:

            pool = MOODS


        tone_rng = random.Random(
            f"inclination-tone-{today}"
        )

        tone = tone_rng.choice(pool)


        return {

            "date": today,

            "level": level,

            "label": spec["label"],

            "willingness":
                spec["willingness"],

            "tone": tone["name"],

            # 语气放前面做定调，
            # 具体许可放后面给细则

            "instruction": (

                f"{tone['desc']}\n\n"

                f"{spec['instruction']}"

            ),

        }


    def _read(self):

        try:

            with open(

                self.file,
                "r",
                encoding="utf-8"

            ) as f:

                return json.load(f)

        except (OSError, ValueError):

            return None


    def _write(self, data):

        with open(

            self.file,
            "w",
            encoding="utf-8"

        ) as f:

            json.dump(

                data,
                f,
                ensure_ascii=False,
                indent=4

            )


def current():

    return Inclination().current()
