# perception.py
# Understanding layer: every user message passes through here first, and one
# call yields all structured judgements — emotion, scene, reply length, memory
# ops, relationship events, follow-ups.
# No persona here: it only emits JSON, and the output must pass
# understanding_schema.validate so dirty data never reaches downstream.
# On failure it raises; brain falls back to rule analysis, chat never breaks.
# 理解端（感知层）：每条用户消息先过这里，一次调用产出全部结构化判断——
# 情绪、场景、回复长短、记忆操作、关系事件、话茬。
# 它在这里不带人格、只输出 JSON，且必须先过 understanding_schema.validate，
# 脏数据到不了下游；失败就抛异常，由 brain 回退规则分析，聊天永不中断。

import json
from datetime import datetime
from core.understanding_schema import (
    validate,
)
_SYSTEM = (
    "你是陪伴机器人的感知分析层。"
    "你只输出合法的 json 对象，"
    "不输出任何解释、"
    "不使用 markdown 代码块。"
)
_PROMPT = """分析用户刚发来的消息，结合最近对话，输出一个 json 对象。

现在的时间：{now}

最近对话（旧到新）：
{dialogue}

用户画像摘要：
{profile}

新消息：
{message}

严格按这个 json 格式输出，字段缺一不可，没有内容就填 null 或空数组：
{{
  "emotion": "happy/sad/tired/anxious/angry/neutral 之一",
  "intensity": 0到1之间的小数,
  "need": "comfort/listen/share/advice/normal 之一",
  "scene": "闲聊/分享/倾诉/求助/玩笑 之一",
  "reply_length": "短/正常/多陪几句 之一",
  "memory_ops": [
    {{"action": "add_profile_item", "category": "preferences", "key": "hobbies", "value": "读诗"}}
  ],
  "relationship_event": "脆弱分享/好消息/冲突/和解/第一次/感谢 之一，没有填 null",
  "follow_up": "对方提到的近期安排或悬念（如明天面试），没有填 null",
  "follow_up_due": "那件事的发生时间，格式 YYYY-MM-DD HH:MM 或 YYYY-MM-DD，没有或推不出填 null",
  "reacts_to": "见下方规则，不适用填 null"
}}

follow_up_due 规则：
- 对照"现在的时间"推算：
  "明天下午面试" -> 明天日期的 15:00；
  "下周一面试" -> 下周一的日期，推不出几点就只给日期
- 只有他明确说了时间才填；
  "改天一起吃饭"这种没着落的时间填 null
- 拿不准就填 null，不要硬编

reacts_to 规则（这一条很重要）：
- 如果新消息只是笑声、应声、短促附和
  （哈哈哈、哈哈、嗯嗯、可以可以、好、行、真的吗、
  这样啊、确实、笑死、绝了、好好好），
  它自己没有内容，全靠挂在上一句上才有意思。
  这时必须写出它在回应你刚才说的哪一句、
  以及它是什么意思。
  例：你刚说「写到一半开始走神了」，对方回「哈哈哈哈」
      -> "他在笑我走神这件事"
  例：你刚说「我请你喝菊花茶」，对方回「可以可以」
      -> "他在答应我请喝菊花茶那件事"
- 如果新消息本身是有内容的（新的事、新的问题），填 null
- 拿不准就填 null，不要硬编

memory_ops 规则：
- 只记录值得长期记住的事实：喜好、目标、重要事件、个人信息
- action 三选一：update_profile（basic 单值字段，key 限 name/birthday/career）
  / add_profile_item（preferences、goals 的列表）
  / add_experience（events 经历，不需要 key）
- category 只能是 basic/preferences/goals/events
- 闲聊、客套、情绪发泄不记，memory_ops 给空数组
- value 要提炼成短词，不要整句照抄
"""


class Perception:

    def __init__(self, llm):
        self.llm = llm

    # Understand one message; raises so the caller can fall back
    # 理解一条消息，失败抛异常，由调用方回退。
    def understand(
        self,
        message,
        recent_dialogue=None,
        profile_summary=""
    ):
        dialogue = self._render_dialogue(
            recent_dialogue
        )
        prompt = _PROMPT.format(
            now=datetime.now().strftime(
                "%Y-%m-%d %H:%M"
            ),
            dialogue=dialogue or "（无）",
            profile=(
                profile_summary or "（空）"
            ),
            message=message,
        )

        # One retry, then raise for brain to fall back
        # 失败重试一次，再失败抛给 brain 回退
        #
        # The reason matters: empty content means the thinking budget ran out
        # before any json came out, a decode error means malformed json, and a
        # schema error means the shape was wrong. Those need different fixes,
        # so record which one it was instead of just "it failed".
        # 失败原因是关键：内容为空 = 思考把额度吃光了、json 没吐出来；
        # 解析失败 = json 本身坏了；schema 失败 = 字段结构不对。
        # 三种病要三种药，所以记下是哪一种，而不是只记"失败了"。
        last_error = None
        reason = "unknown"
        for _ in range(2):
            try:
                raw = self.llm.generate_json(
                    prompt,
                    system=_SYSTEM,
                )
                if not (raw or "").strip():
                    reason = "empty_content"
                    raise ValueError(
                        "理解端返回空内容"
                    )
                try:
                    parsed = json.loads(raw)
                except ValueError as e:
                    reason = "bad_json"
                    raise ValueError(
                        f"理解端 json 解析失败: {e}"
                    )
                try:
                    return validate(parsed)
                except Exception as e:
                    reason = "schema"
                    raise ValueError(
                        f"理解端 schema 校验失败: {e}"
                    )
            except Exception as e:
                last_error = e
        try:
            from core import observe
            observe.note(
                "understand_error",
                reason=reason,
                error=str(last_error)[:200],
            )
        except Exception:
            pass
        raise RuntimeError(
            f"理解端调用失败: {last_error}"
        )

    @staticmethod
    def _render_dialogue(recent_dialogue):
        if not recent_dialogue:
            return ""
        lines = []
        for item in recent_dialogue[-6:]:
            content = (
                item.get("content")
                or ""
            ).replace("\n", " ").strip()
            if not content:
                continue
            who = (
                "对方"
                if item.get("role") == "user"
                else "Soulmate"
            )
            lines.append(
                f"{who}：{content}"
            )
        return "\n".join(lines)
