# memory_pipeline.py
#
# 记忆入库。
#
# 以前的做法是先让模型判断"这句话值不值得记"，
# 不值得就丢掉。实际跑下来几乎什么都记不住——
# 用户的消息大多是七八个字的闲聊，
# 全被判成不重要，
# 结果约定的日子、学校、住处这些
# 真正有价值的内容一条都没留下。
#
# 现在改成宽进：
#   1. 先做轻噪过滤（嗯嗯、哦哦、复读）
#   2. 剩下的原文全量进向量库，另存一份摘要
#   3. 相关性交给检索时排序，不在这里猜
#
# 另外她自己（Soulmate）的回复也要过一遍：
# 她说过的关于自己的事实（我在哪读书、我住哪）
# 必须落库，否则下次又换一套说法。

import re

from memory.long_memory import LongMemory

from memory.vector_memory import VectorMemory


# 纯语气词和敷衍回应。
# 这些进库只会污染检索。

NOISE = frozenset({

    "哦", "哦哦", "嗯", "嗯嗯", "啊", "啊啊",
    "哈", "哈哈", "哈哈哈", "hhhh", "233",
    "好", "好的", "好吧", "行", "行的", "可以",
    "是", "是的", "对", "对的", "对对", "没错",
    "不是", "没有", "没事", "没", "不用",
    "知道", "知道了", "明白", "了解", "收到",
    "真的吗", "是吗", "为啥", "为什么", "然后呢",
    "嗯呢", "哦豁", "啊这", "呃", "额", "emm",
    "？", "?", "。。。", "...", "…",
    "哈哈哈哈", "笑死", "6", "666",

})


# 一句话里全是同一个字 → 复读，不记

_REPEAT_RE = re.compile(
    r"^(.)\1{2,}$"
)


# 只保留中文、数字、字母，
# 用来判断"这句话有没有实质内容"

_SUBSTANCE_RE = re.compile(
    r"[^"
    r"\u4e00-\u9fff"
    r"a-zA-Z0-9"
    r"]"
)


# Soulmate 关于自己的事实陈述。
# 匹配到就把整句存下来，
# 她下次得接着这个说法。

ECHO_FACT_PATTERNS = (

    r"我在[^，。！？!?~]{2,12}",
    r"我住[^，。！？!?~]{2,12}",
    r"我家在[^，。！？!?~]{2,12}",
    r"我来自[^，。！？!?~]{2,12}",
    r"我是[^，。！？!?~]{2,12}",
    r"我学[^，。！？!?~]{2,12}",
    r"我在读[^，。！？!?~]{2,12}",

)


# ==================================================
# 入库重要度（2026-08-31 加，配遗忘曲线用）
#
# 宽进模式不问模型（多一次 LLM 调用
# 就是多一次延迟），用关键词规则定档：
#
#   0.85 大事：健康、家人、手术、
#        生死、重要决定、约好的事
#   0.75 强情绪事件：第一次、生日、
#        面试、考试、离职
#   0.6  稳定事实：喜欢/讨厌/习惯/
#        我爸我妈这类自述
#   0.4  有内容的日常
#   0.3  默认（闲聊）
#
# 档位对应保质期 240/60/21/7 天，
# 见 vector_memory.py 的文件头。
# 错了没关系——被想起一次就续期，
# 遗忘曲线自己会纠偏。
# ==================================================

_BIG_RE = re.compile(
    r"手术|住院|生病|发烧|体检|化疗|"
    r"去世|走了|离世|生死|"
    r"决定了|已经决定|跟你说个事|"
    r"约好|说好的|答应你|等你"
)

_EVENT_RE = re.compile(
    r"第一次|生日|面试|考试|考研|"
    r"复试|成绩|入职|离职|辞职|"
    r"发工资|搬家|表白|分手|"
    r"下周|下个月|明天.{0,6}(要|得)"
)

_PREF_RE = re.compile(
    r"喜欢|讨厌|受不了|最爱|"
    r"不吃|不吃辣|忌口|习惯|"
    r"我妈|我爸|我哥|我姐|我弟|我妹|"
    r"我老家|我们家"
)


def _guess_importance(text):

    t = text or ""

    if _BIG_RE.search(t):

        return 0.85

    if _EVENT_RE.search(t):

        return 0.75

    if _PREF_RE.search(t):

        return 0.6

    # 有实质内容才有 0.4

    substance = _SUBSTANCE_RE.sub(
        "", t
    )

    if len(substance) >= 10:

        return 0.4

    return 0.3


# 约定的信号：
# 等…就… / 下次… / 改天… / 到时候…

PROMISE_HINTS = (

    "等", "到时候", "下次", "改天", "以后",
    "约好", "说定", "一言为定", "记得叫",

)


PREFERENCE_HINTS = (

    "喜欢", "讨厌", "爱吃", "爱看", "爱好",
    "偏好", "钟意", "迷",

)


def _substance(text):

    """
    去掉标点和语气后的实质内容。
    """

    return _SUBSTANCE_RE.sub(
        "", text or ""
    ).strip()


def is_noise(text):

    """
    这句话值不值得占一条记忆。
    """

    text = (text or "").strip()

    if not text:

        return True

    core = _substance(text)

    # 没实质内容（纯标点/纯表情）

    if len(core) < 2:

        return True

    # 语气词

    if text.lower() in NOISE:

        return True

    if core in NOISE:

        return True

    # 复读：哈哈哈 / 好好好

    if _REPEAT_RE.match(core):

        return True

    # 同一个字占了大半

    if core:

        top = max(
            core.count(c)
            for c in set(core)
        )

        if (
            len(core) >= 3
            and top / len(core) > 0.7
        ):

            return True

    return False


def summarize(text, limit=40):

    """
    一句话摘要。
    取第一句，超长截断。
    不额外调模型，省一次网络往返。
    """

    text = (text or "").strip()

    first = re.split(
        r"[。！？!?\n]", text
    )[0].strip()

    if not first:

        first = text

    if len(first) > limit:

        first = first[:limit] + "…"

    return first or text[:limit]


def classify(text):

    """
    给记忆打个标签，
    只在面板展示时使用，
    判断错了也不影响检索。
    """

    if any(
        h in text
        for h in PROMISE_HINTS
    ):

        return "promise"

    if any(
        h in text
        for h in PREFERENCE_HINTS
    ):

        return "preference"

    if re.search(
        r"我在|我住|我是|我家|我来自",
        text
    ):

        return "fact"

    return "statement"


class MemoryPipeline:

    def __init__(self, llm=None):

        # llm 留着兼容旧调用，
        # 宽进模式下不再让它决定"记不记"

        self.llm = llm

        self.memory = LongMemory()

        self.vector_memory = VectorMemory()


    # ==================================================
    # 用户消息：轻噪过滤后全量入库
    # ==================================================

    def process(self, message, role="user"):

        text = (message or "").strip()

        if is_noise(text):

            return {
                "saved": False,
                "reason": "noise",
            }

        record = self.vector_memory.add_memory(

            text,

            summary=summarize(text),

            role=role,

            kind=classify(text),

            importance=_guess_importance(
                text
            ),

        )

        return {
            "saved": record is not None,
            "record": record,
        }


    # ==================================================
    # Soulmate 自己的回复：
    # 抽出她说过的关于自己的事实
    # ==================================================

    def process_reply(self, reply):

        """
        她说的每一句"我在…""我是…"
        都要落库。
        这是她人格一致性的底，
        否则下次换个说法，
        用户一眼就看出在编。
        """

        text = (reply or "").strip()

        if not text:

            return []

        saved = []

        seen = set()

        # 已入库的原文不重复存。
        # "我在…"这种句式她一天要说很多次，
        # 不去重的话记忆库会被刷爆。

        for record in (
            self.vector_memory
            .all_records()
        ):

            seen.add(
                (
                    record.get("text") or ""
                ).strip()
            )

        for pattern in ECHO_FACT_PATTERNS:

            for m in re.finditer(
                pattern, text
            ):

                fact = m.group(0).strip()

                if fact in seen:

                    continue

                seen.add(fact)

                record = (
                    self.vector_memory
                    .add_memory(

                        fact,

                        summary=summarize(
                            fact
                        ),

                        role="echo",

                        kind="fact",

                        # 她说过的关于自己
                        # 的事实：一致性的底，
                        # 保质期给到最长一档

                        importance=0.85,

                    )
                )

                if record:

                    saved.append(record)

        return saved
