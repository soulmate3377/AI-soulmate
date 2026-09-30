# proactive_guard.py
#
# 主动消息守门人
#
# 她主动开口前要过四道关：
#
#   1. 冷却阶梯
#      连续没人回应就越来越久地闭嘴
#      30 分钟 → 1 小时 → 2 小时 → 当天不再主动
#
#   2. 意象去重
#      24 小时内同一个意象（下雨/月亮/晚风…）
#      只允许出现一次
#
#   3. 回溯性承诺
#      不许说"你上次说好…""你答应过…"，
#      除非话茬里能翻出原文证据。
#      说错一次比不说更伤人。
#
#   4. 当下场景
#      用户在打字、刚回过消息、她自己正在回复
#      —— 一律不打扰
#
#   5. 她自己不想说
#      前面四道关全是关于他的
#      （在不在打字、忙不忙、有没有已读不回）。
#      这一道是关于她的 ——
#      她也有不太想开口的日子。
#
# 状态写在 memory/proactive_state.json。
# 重启后冷却记录和意象记录都还在，
# 不会换个进程就重新开始轰炸。

import re

from datetime import datetime

from core import storage

from core import inclination

from core.paths import data_dir


_TIME_FMT = "%Y-%m-%d %H:%M:%S"


# 连续无人回应时的冷却阶梯（分钟）。
# 阶梯走完就是当天不再主动，
# 第二天自然重新开始。

COOLDOWN_MINUTES = [30, 60, 120]


# 每天这个点之后才允许主动开口

DAY_START_HOUR = 8

DAY_END_HOUR = 23


# 用户刚说过话后的安静期（秒）。
# 他话才说到一半，别抢话。

QUIET_AFTER_USER = 300


# 意象组。
#
# 她一开口就容易反复用同一批画面，
# 这里把会串味的说法归到一组。
# 24 小时内一组只允许出现一次。
#
# 词表保守一点，宁可漏也不要误伤
# 正常表达。

IMAGERY = {

    "毛毛雨": (
        "毛毛雨", "细雨", "雨丝", "雨还在下",
        "下着雨", "小雨", "毛毛的", "下得毛毛",
    ),

    "下雨": (
        "下雨", "雨天", "雨声", "阵雨", "暴雨",
        "被雨淋", "雨停",
    ),

    "月亮": ("月亮", "月光"),

    "花开": ("花", "开花", "花开了"),

    "晚风": ("晚风", "风", "吹风"),

    "散步": ("散步", "走圈", "跑圈"),

    # 只拦"刚下课"这种开场套话。
    # 不拦"上课""教室"——那不是意象，
    # 是她的日常，
    # 拦了她一整天都没法提学校。

    "下课": ("刚下课", "下课了"),

    "图书馆": ("图书馆", "自习"),

    "太阳": ("太阳", "放晴", "天晴", "日头"),

    "月亮": ("月亮", "夜色", "星空", "月色"),

    "风": ("起风", "吹风", "风一吹", "有点风"),

    "吃饭": (
        "吃饭", "晚饭", "午饭", "吃啥", "吃了没",
        "炒饭", "盖饭", "点了碗", "加了个蛋",
    ),

    "宿舍": ("宿舍", "寝室"),

}


# 每天最多主动开口的次数。
# 冷却阶梯管的是"间隔"，
# 这个管的是"总量" ——
# 就算他句句都认真回，
# 她一天也不该追着他说个没完。

MAX_PROACTIVE_PER_DAY = 6


# 敷衍应声词。
# "嗯""哈哈"这种回了等于没回，
# 不该把冷却清零。

PERFUNCTORY = {

    "嗯", "嗯嗯", "嗯嗯嗯", "嗯呢",
    "哦", "哦哦", "好", "好的", "好嘞",
    "好哒", "行", "可以", "可以可以",
    "哈哈", "哈哈哈", "呵呵", "嘿嘿",
    "对", "是", "是的", "在", "在的",
    "ok", "okk", "嗯哼",

}


def _is_perfunctory(text):

    """
    判断一句回复是不是敷衍应声。

    剥掉标点空白后不超过两个字，
    或整句就是应声词，都算敷衍。
    只回了个表情/标点也算。
    """

    if not text:

        return False

    cleaned = re.sub(

        r"[\s~～!！?？。.,，、…·\-]+",
        "",
        text

    )

    if not cleaned:

        return True

    if len(cleaned) <= 2:

        return True

    return cleaned.lower() in {
        w.lower() for w in PERFUNCTORY
    }


# 回溯性引用过去的约定、承诺、说法。
#
# 这些句式一旦说错，
# 用户会觉得她在编造，
# 比沉默更伤信任。

PROMISE_PATTERNS = (

    "你上次说好", "上次说好", "你说好要", "你说好了",
    "你答应过", "你答应", "上次答应", "说好的",
    "你说过要", "你之前说要", "你上次提到",
    "你还记得你说", "你不是说要", "你不是说",
    "约好的", "约好了", "上次你说", "你上次说",
    "你跟我约", "你答应我",

)


# 归因内容的边界：
# 承诺句式后面先吃掉这些虚词，
# 再取到第一个标点为止

# 注意不要放"来"：
# "你上次说好要来闻的"里
# "来"是被归因的内容本身，
# 吃掉就只剩"闻的"了

_CLAIM_LEAD = r"[要会说过能就还得好去]*"

_CLAIM_BODY = r"([^，。！？!?、,;\n]{2,12})"


_CJK_RUN = re.compile(
    r"[\u4e00-\u9fff]+"
)


def _now_text():

    return datetime.now().strftime(
        _TIME_FMT
    )


def _age_seconds(time_text):

    if not time_text:

        return None

    try:

        t = datetime.strptime(
            time_text,
            _TIME_FMT
        )

    except (TypeError, ValueError):

        return None

    return (
        datetime.now() - t
    ).total_seconds()


def _terms(text, size):

    """
    取中文的连续片段作为指纹。
    size=2 粗一些，size=3 更严格。
    """

    out = set()

    for run in _CJK_RUN.findall(
        text or ""
    ):

        if len(run) < size:

            out.add(run)

            continue

        for i in range(
            len(run) - size + 1
        ):

            out.add(run[i:i + size])

    return out


def _similarity(a, b):

    """
    两段中文的 3-gram Jaccard 相似度。
    用来拦住"换个说法又说一遍"。
    """

    ta = _terms(a, 3)

    tb = _terms(b, 3)

    if not ta or not tb:

        return 0.0

    return len(ta & tb) / len(ta | tb)


def followup_same(a, b):

    """
    两条话茬说的是不是同一件事。

    话茬很短，3-gram 一换措辞就
    一个都对不上，这里用 2-gram。
    先剥掉"的了呢吗"这类虚字 ——
    "明天的面试" 和 "明天下午面试"
    就差一个"的"，剥掉才并得上；
    "去医院复查" 和 "去医院拿报告"
    内容字不同，仍然并不上。

    判定：Jaccard >= 0.3，
    或短的一方的切片整个是
    长的子集（"面试" 和
    "明天的面试" 就是同一件事）。
    """

    def norm(text):

        return re.sub(

            r"[的了着呢吗吧啊呀嘛]",
            "",
            text or ""

        )

    ta = _terms(norm(a), 2)

    tb = _terms(norm(b), 2)

    if not ta or not tb:

        return False

    if ta <= tb or tb <= ta:

        return True

    return (
        len(ta & tb) / len(ta | tb)
    ) >= 0.3


def claim_spans(message):

    """
    抠出被归因到对方身上的说法片段。

    "你上次说好要来闻的，可别光说不来呀"
        → ["来闻的"]

    "你答应过下周一起去" → ["下周一起去"]
    """

    text = message or ""

    spans = []

    for pattern in PROMISE_PATTERNS:

        start = 0

        while True:

            i = text.find(
                pattern, start
            )

            if i < 0:

                break

            tail = text[
                i + len(pattern):
            ]

            m = re.match(

                _CLAIM_LEAD
                + _CLAIM_BODY,

                tail

            )

            if m:

                spans.append(
                    m.group(1)
                )

            start = i + len(pattern)

    # 同一个片段被多个句式重复命中时，
    # 只留最长的那个，
    # 免得把本来能过的话卡死

    maximal = [

        s for s in spans

        if not any(

            s != other
            and s in other

            for other in spans

        )

    ]

    # 去重但保留顺序

    seen = set()

    out = []

    for s in maximal:

        if s not in seen:

            seen.add(s)

            out.append(s)

    return out


def references_past_promise(message):

    """
    这句话有没有提"你说过/答应过/说好的"。
    """

    text = message or ""

    return any(
        p in text
        for p in PROMISE_PATTERNS
    )


def has_evidence(message, follow_ups):

    """
    这句话里每一处"你说过…"，
    都要能在话茬记录里翻到原文依据。

    判定：归因片段的任意 2 字切片
    出现在某条话茬里。
    只按主题相同不算证据——
    "你上次说好要一起看的"和
    "等月亮圆了你叫我一声"
    都聊月亮，但根本不是一回事。

    提到了过去、却又抠不出具体内容的
    （比如"上次说好的，等你来闻呀"
    这种逗号后面才说正题的），
    一律当没有证据处理。
    """

    if not references_past_promise(
        message
    ):

        return True

    spans = claim_spans(message)

    # 提了旧事但说不出说的是什么，
    # 更不可信

    if not spans:

        return False

    if not follow_ups:

        return False

    corpus = " ".join(

        str(i.get("text") or "")

        for i in follow_ups

    )

    if not corpus.strip():

        return False

    for span in spans:

        pieces = _terms(span, 2)

        if not pieces:

            return False

        if not any(
            p in corpus
            for p in pieces
        ):

            return False

    return True


class ProactiveGuard:

    def __init__(self):

        self.file = (
            data_dir()
            / "memory"
            / "proactive_state.json"
        )

        self.state = (
            storage.read_json(
                self.file, {}
            )
            or {}
        )

        self._rollover()


    # ==================================================
    # 状态读写
    # ==================================================

    def _rollover(self):

        """
        跨天就把冷却清零。
        意象记录按 24 小时滚动，
        不跟着天走。
        """

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )

        if self.state.get("date") != today:

            self.state["date"] = today

            self.state["unanswered"] = 0

            self.state["sent_today"] = 0

            self._save()


    def _save(self):

        storage.write_json(
            self.file, self.state
        )


    # ==================================================
    # 记录：用户开口 / 她开口
    # ==================================================

    def note_user_message(self, text=None):

        """
        用户说话了。

        认真回了一句：
            冷却清零，她重新从 30 分钟开始。
        只回了句"嗯""哈哈"：
            冷却不清零 —— 那不叫回应，
            追着敷衍他的人一直聊
            就是打卡机了。

        无论哪种都更新 last_user：
        他在，别抢话。
        """

        self._rollover()

        if not _is_perfunctory(text or ""):

            self.state["unanswered"] = 0

        self.state["last_user"] = (
            _now_text()
        )

        self._save()


    def note_proactive_sent(
        self, message
    ):

        """
        主动消息真的发出去了：
        累计无人回应次数，
        并记下这次用到的意象。
        """

        self._rollover()

        self.state["unanswered"] = (
            int(
                self.state.get(
                    "unanswered", 0
                )
            )
            + 1
        )

        # 当天总量计数，
        # 到顶就闭嘴到明天

        self.state["sent_today"] = (
            int(
                self.state.get(
                    "sent_today", 0
                )
            )
            + 1
        )

        self.state[
            "last_proactive"
        ] = _now_text()

        self.state[
            "last_proactive_text"
        ] = message or ""

        imagery = self.state.setdefault(
            "imagery", {}
        )

        for name in self.imagery_hits(
            message
        ):

            imagery[name] = _now_text()

        self._save()


    # ==================================================
    # 冷却阶梯
    # ==================================================

    def _willingness(self):

        """
        她今天有多想主动开口。
        1.0 很想，0.0 完全不想。
        """

        return inclination.current().get(
            "willingness", 1.0
        )


    def cooldown_minutes(self):

        """
        当前应当间隔多少分钟。
        返回 None 表示当天不再主动。
        """

        n = int(
            self.state.get(
                "unanswered", 0
            )
        )

        if n >= len(COOLDOWN_MINUTES):

            return None


        minutes = COOLDOWN_MINUTES[n]

        w = self._willingness()


        # 她今天不太想说话：
        # 一整天都不主动开口。
        # 注意这不等于她不回他 ——
        # 他找过来，她还是会回。

        if w < inclination.WILLINGNESS_BLOCK:

            return None


        # 兴致不高：冷却翻倍，
        # 而不是完全闭嘴

        if w < inclination.WILLINGNESS_SLOW:

            minutes = int(minutes * 2)


        return minutes


    def silence_left(self):

        """
        还要闭嘴多少秒。
        0 表示现在就可以开口。
        """

        cooldown = self.cooldown_minutes()

        if cooldown is None:

            return None

        last = self.state.get(
            "last_proactive"
        )

        if not last:

            return 0

        gap = _age_seconds(last)

        if gap is None:

            return 0

        return max(
            0,
            cooldown * 60 - gap
        )


    # ==================================================
    # 前置判断：
    # 现在值不值得去想一句主动消息
    # ==================================================

    def should_attempt(self, ui_state=None):

        """
        返回 (bool, 原因)
        """

        self._rollover()

        ui_state = ui_state or {}

        # --------------------
        # 深夜不打扰
        # --------------------

        hour = datetime.now().hour

        if (
            hour < DAY_START_HOUR
            or hour >= DAY_END_HOUR
        ):

            return False, "深夜不打扰"


        # --------------------
        # 他正在打字
        # --------------------

        if ui_state.get(
            "user_typing"
        ):

            return (
                False,
                "用户正在输入"
            )


        # --------------------
        # 她正在回复
        # --------------------

        if ui_state.get(
            "echo_busy"
        ):

            return (
                False,
                "她正在回复"
            )


        # --------------------
        # 她今天不太想说话
        #
        # 前面每一票都是关于他的：
        # 他在不在打字、他忙不忙、
        # 他有没有已读不回。
        #
        # 这一票是关于她的。
        # 一个只在对方方便时开口的人
        # 不是随和，是没有自己。
        #
        # 冷却里已经按意愿拉长过一轮，
        # 这里只拦最不想说话的那一档
        # --------------------

        if (
            self._willingness()
            < inclination.WILLINGNESS_BLOCK
        ):

            return (
                False,
                "她今天不太想说话"
            )


        # --------------------
        # 他刚说过话，
        # 让话头凉一凉
        # --------------------

        last_user = self.state.get(
            "last_user"
        )

        if last_user:

            gap = _age_seconds(
                last_user
            )

            if (
                gap is not None
                and gap < QUIET_AFTER_USER
            ):

                return (
                    False,
                    f"用户 {int(gap)} 秒前"
                    f"刚说过话"
                )


        # --------------------
        # 冷却
        # --------------------

        if int(

            self.state.get("sent_today", 0)

        ) >= MAX_PROACTIVE_PER_DAY:

            return (
                False,
                "今天主动说得够多了"
            )


        left = self.silence_left()

        if left is None:

            return (
                False,
                "今天已经说得够多了，"
                "闭嘴到明天"
            )

        if left > 0:

            return (
                False,
                f"冷却中（还剩 "
                f"{int(left / 60) + 1} 分钟）"
            )

        return True, "可以开口"


    # ==================================================
    # 后置审核：
    # 生成出来的这句话能不能发
    # ==================================================

    def imagery_hits(self, message):

        """
        这句话用到了哪些意象组。
        """

        text = message or ""

        hits = []

        for name, words in (
            IMAGERY.items()
        ):

            for w in words:

                if w in text:

                    hits.append(name)

                    break

        return hits


    def fresh_imagery(self):

        """
        24 小时内已经用过的意象。
        返回 {意象名: 还剩多少小时解禁}
        """

        used = self.state.get(
            "imagery", {}
        )

        out = {}

        for name, when in used.items():

            age = _age_seconds(when)

            if age is None:

                continue

            if age < 86400:

                out[name] = round(
                    (86400 - age) / 3600,
                    1
                )

        return out


    def screen(
        self, message, follow_ups=None
    ):

        """
        返回 (bool, 原因)

        不通过的消息直接丢掉，
        不落盘、不通知、不重试。
        下一轮再想一句新的。
        """

        if (
            not message
            or not message.strip()
        ):

            return False, "空消息"


        # --------------------
        # 意象去重
        # --------------------

        fresh = self.fresh_imagery()

        for name in self.imagery_hits(
            message
        ):

            if name in fresh:

                return (
                    False,
                    f"「{name}」"
                    f"{fresh[name]} 小时内"
                    f"已经用过"
                )


        # --------------------
        # 跟上一句太像
        # --------------------

        prev = self.state.get(
            "last_proactive_text"
        )

        if prev and _similarity(
            prev, message
        ) >= 0.5:

            return (
                False,
                "和上一句几乎一样"
            )


        # --------------------
        # 回溯性承诺引用
        # --------------------

        if references_past_promise(
            message
        ):

            if not has_evidence(
                message, follow_ups
            ):

                return (
                    False,
                    "引用了过去的约定，"
                    "但话茬里找不到原文证据"
                )

        return True, "通过"
