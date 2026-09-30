# understanding_schema.py
#
# 理解端输出的校验层：
# 模型返回的 JSON 一律先过这里，
# 不合法的字段被丢弃或修正，
# 绝不让脏数据流进记忆和 prompt。
#
# 这是"记忆写入不再崩"的
# 根本保证（配合 long_memory 的
# setdefault 容错是双保险）


# 允许的画像类别

CATEGORIES = {
    "basic",
    "preferences",
    "goals",
    "events",
}

# 允许的记忆操作

ACTIONS = {
    "update_profile",
    "add_profile_item",
    "add_experience",
}

# 允许的场景判断

SCENES = {
    "闲聊", "分享", "倾诉",
    "求助", "玩笑",
}

# 允许的回复长短

REPLY_LENGTHS = {
    "短", "正常", "多陪几句",
}

# 允许的关系事件
# （关系事件化阶段的入口，
# 先记录，阶段2再消费）

RELATIONSHIP_EVENTS = {
    "脆弱分享", "好消息", "冲突",
    "和解", "第一次", "感谢",
}

# 话茬事件时间的合法格式。
#
# 模型可以只给日期（"下周一面试"
# 推不出几点），只给日期的
# 一律归到当天 18:00 ——
# 傍晚再问"怎么样"最不容易
# 问早了。

_DUE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
)

# 允许的情绪/需求
# （与 EmotionAnalyzer 的输出
# 形状保持一致，下游不用改）

EMOTIONS = {
    "happy", "sad", "tired",
    "anxious", "angry", "neutral",
}

NEEDS = {
    "comfort", "listen", "share",
    "advice", "normal",
}

# 单条字段的最大长度

_MAX_VALUE = 80

_MAX_FOLLOW_UP = 80

_MAX_REACTS_TO = 120



def _clean_str(value, limit):

    if not isinstance(value, str):

        return None

    value = value.strip()

    if not value:

        return None

    return value[:limit]



def _clean_due(value):

    """
    话茬的事件时间。

    接受 "YYYY-MM-DD [HH:MM[:SS]]"，
    只给日期的归到当天 18:00。
    解析不了、或不是字符串，
    一律返回 None ——
    调度器会退回按"提及时间"
    判断新旧。
    """

    if not isinstance(value, str):

        return None

    value = value.strip()

    if not value:

        return None

    from datetime import datetime

    for fmt in _DUE_FORMATS:

        try:

            t = datetime.strptime(
                value, fmt
            )

        except ValueError:

            continue

        if fmt == "%Y-%m-%d":

            t = t.replace(hour=18)

        return t.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    return None



def _clean_ops(raw_ops):

    """
    记忆操作逐条校验：
    动作/类别必须在白名单，
    value 必须是非空短字符串
    """

    if not isinstance(raw_ops, list):

        return []

    ops = []

    for raw in raw_ops[:5]:

        if not isinstance(raw, dict):

            continue

        action = raw.get("action")

        category = raw.get("category")

        if (
            action not in ACTIONS
            or category not in CATEGORIES
        ):

            continue

        value = _clean_str(
            raw.get("value"),
            _MAX_VALUE
        )

        if value is None:

            continue

        key = _clean_str(
            raw.get("key"),
            _MAX_VALUE
        )

        # update/add_item 必须有键，
        # add_experience 不需要

        if (
            action != "add_experience"
            and key is None
        ):

            continue

        ops.append({

            "action": action,
            "category": category,
            "key": key,
            "value": value,

        })

    return ops



def validate(raw):

    """
    把模型返回的原始 dict
    规整成可信的理解结果。
    任何字段缺失/非法都给默认值，
    这个函数本身永不抛异常。
    """

    if not isinstance(raw, dict):

        raw = {}


    # 情绪（形状对齐旧分析器）

    emotion = raw.get("emotion")

    if emotion not in EMOTIONS:

        emotion = "neutral"

    try:

        intensity = float(
            raw.get("intensity", 0)
        )

    except (TypeError, ValueError):

        intensity = 0.0

    intensity = max(
        0.0, min(1.0, intensity)
    )

    need = raw.get("need")

    if need not in NEEDS:

        need = "normal"


    # 场景

    scene = raw.get("scene")

    if scene not in SCENES:

        scene = "闲聊"


    # 回复长短

    reply_length = raw.get(
        "reply_length"
    )

    if reply_length not in (
        REPLY_LENGTHS
    ):

        reply_length = "正常"


    # 关系事件

    rel_event = raw.get(
        "relationship_event"
    )

    if rel_event not in (
        RELATIONSHIP_EVENTS
    ):

        rel_event = None


    # 话茬

    follow_up = _clean_str(

        raw.get("follow_up"),
        _MAX_FOLLOW_UP

    )


    # 话茬里那件事的发生时间。
    # 没有话茬，时间没有意义，
    # 一起丢掉。

    follow_up_due = None

    if follow_up is not None:

        follow_up_due = _clean_due(

            raw.get("follow_up_due")

        )


    # 他在回应什么。
    #
    # 「哈哈哈哈」「可以可以」「嗯嗯」这类
    # 自己不带内容，全靠挂在上一句上才有意思。
    # 不把它挂上去，她只能瞎猜 ——
    # 一猜就是编一句听着通顺的话。

    reacts_to = _clean_str(

        raw.get("reacts_to"),
        _MAX_REACTS_TO

    )


    return {

        "emotion": emotion,
        "intensity": intensity,
        "need": need,
        "scene": scene,
        "reply_length": reply_length,
        "memory_ops": _clean_ops(
            raw.get("memory_ops")
        ),
        "relationship_event":
            rel_event,
        "follow_up": follow_up,
        "follow_up_due": follow_up_due,
        "reacts_to": reacts_to,

    }
