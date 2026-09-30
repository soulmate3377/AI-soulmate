# core/self_reflection.py
#
# 回看端：输出之后，回头看一眼自己说了什么。
#
# ==================================================
# 这是三个 API 里的第三个
# ==================================================
#
#   1. 理解  core/perception.py
#      情绪、场景、长短、话茬、他在回应什么
#   2. 输出  llm + prompt/builder.py
#   3. 回看  这里
#
# 前两个是单向的：理解完就输出，输出完就结束了。
# 第三个把环闭起来 ——
# 输出的结果回过头去，
# 影响下一轮的理解和输出。
#
# ==================================================
# 为什么放在输出之后
# ==================================================
#
# 放在输出之前能拦住错话，代价是：
# 得先把整段回复缓冲下来再审，
# 流式输出就没了，
# 用户多等半秒到一秒才看到第一个字。
#
# 放在输出之后是免费的：
# 那次调用本来就在回复之后跑。
# 代价是错话已经说出去了。
#
# 所以这里的定位不是"拦截"，
# 是"她自己发现说错了，下一句自然找补一句"。
# 人也是这么聊天的。

import json


_SYSTEM = (
    "你是 Soulmate 的回看层。"
    "你只输出合法的 json 对象，"
    "不输出任何解释，"
    "不使用 markdown 代码块。"
)


_PROMPT = """Soulmate 刚回了一句话。你只判断一件事：这句回复有没有"凭空编造"。

刚才的对话（旧到新）：
{dialogue}

他刚说的：
{user_message}

Soulmate 回的：
{response}

只有以下三种情况判为不合格，其余一律判合格：

1. 她说了他没说过的话、没表达过的意思
   例：他只是问"为啥走神"，
       她回"被你看穿了"
       —— 没有人看穿什么，这是她编的
   例：他说"茉莉花茶"，
       她回"你上次说最爱喝这个"
       —— 他没说过"最爱"

2. 她把他的意思理解反了
   例：他在自嘲，她当成求助去安慰

3. 她复述了自己上一句刚说过的话

另外，如果他刚说的只是笑声或应声
（哈哈哈、嗯嗯、可以可以、好、行），
而她回的是"笑啥""怎么了""什么意思"，
也判不合格 ——
那等于承认自己没听懂。

严格输出这个 json：
{{"passed": true}}
或
{{"passed": false, "note": "用一句话说清她错在哪，二三十字以内，用'你'称呼 Soulmate"}}
"""


_PROMPT_PROACTIVE = """Soulmate 刚主动给他发了一条消息（不是回复，是她自己开的口）。你只判断一件事：这条消息有没有"凭空编造"。

最近的对话（旧到新）：
{dialogue}

他之前提过的事（话茬，带时间）：
{follow_ups}

Soulmate 主动发的：
{message}

只有以下三种情况判为不合格，其余一律判合格：

1. 她提了他没提过的事、安排或约定
   —— 上面的话茬和最近对话里都找不到的事，
      就是她编的
   例：话茬里没有面试，
       她问"你面试怎么样了"

2. 她把那件事的时间说错了
   例：话茬标着事已经过了三天，
       她却问得像明天才发生

3. 她说的和最近聊的对不上，
   像群发，或复述了她自己刚说过的话

严格输出这个 json：
{{"passed": true}}
或
{{"passed": false, "note": "用一句话说清她错在哪，二三十字以内，用'你'称呼 Soulmate"}}
"""


class SelfReflection:


    def __init__(self, llm=None):

        self.llm = llm


    def analyze(
        self,
        user_message,
        response,
        recent_dialogue=None
    ):

        """
        返回 {"adjustments": [...], "note": ...}

        note 是给她下一句看的：
        她上一句哪里说错了，
        下一句要自然地找补一下。

        调用失败一律返回合格 ——
        宁可她胡说一句，
        也不能让她因为回看挂了
        而说不出话。
        """

        result = {
            "adjustments": [],
            "note": None,
        }

        if self.llm is None:

            return result

        dialogue = self._render(
            recent_dialogue
        )

        prompt = _PROMPT.format(

            dialogue=dialogue or "（无）",

            user_message=(
                user_message or "（空）"
            ),

            response=(
                response or "（空）"
            ),

        )

        try:

            # 回看端：走 Pro（MODEL_REFLECT）。
            # 这一步在她把话说完之后才跑，
            # 慢一点他感觉不到，
            # 所以这里是全系统唯一
            # 值得用强模型的地方 ——
            # 她要靠这一步发现自己说错了。

            raw = self.llm.generate_json(
                prompt,
                system=_SYSTEM,
                reflect=True,
            )

            data = json.loads(raw)

            passed = bool(
                data.get("passed", True)
            )

            if passed:

                return result

            note = (
                data.get("note") or ""
            ).strip()

            if note:

                result["note"] = note[:120]

        except Exception:

            return result


        return result


    def analyze_proactive(
        self,
        message,
        recent_dialogue=None,
        follow_ups=None,
    ):

        """
        主动消息的回看。

        主动开口没有人递话，
        是全系统最容易凭空编造的
        通道 —— 普通回复有的回看，
        这里一样要有。

        出的问题照样留成便签：
        他回这条主动消息的时候，
        就是她的"下一句"。

        调用失败一律返回合格，
        理由同 analyze。
        """

        result = {
            "adjustments": [],
            "note": None,
        }

        if self.llm is None:

            return result

        dialogue = self._render(
            recent_dialogue
        )

        followup_lines = []

        for item in (follow_ups or []):

            text = (
                item.get("text") or ""
            ).strip()

            if not text:

                continue

            due = item.get("due") or ""

            if due:

                followup_lines.append(
                    f"- {text}"
                    f"（事约在 {due}）"
                )

            else:

                followup_lines.append(
                    f"- {text}"
                )

        prompt = _PROMPT_PROACTIVE.format(

            dialogue=dialogue or "（无）",

            follow_ups=(
                "\n".join(followup_lines)
                or "（无）"
            ),

            message=(message or "（空）"),

        )

        try:

            raw = self.llm.generate_json(

                prompt,
                system=_SYSTEM,
                reflect=True,

            )

            data = json.loads(raw)

            passed = bool(
                data.get("passed", True)
            )

            if passed:

                return result

            note = (
                data.get("note") or ""
            ).strip()

            if note:

                result["note"] = note[:120]

        except Exception:

            return result


        return result


    @staticmethod
    def _render(recent_dialogue):

        if not recent_dialogue:

            return ""

        lines = []

        for item in recent_dialogue[-6:]:

            content = (
                item.get("content") or ""
            ).replace("\n", " ").strip()

            if not content:

                continue

            who = (
                "他"
                if item.get("role") == "user"
                else "Soulmate"
            )

            lines.append(
                f"{who}：{content}"
            )

        return "\n".join(lines)
