# prompt/builder.py

import re


# 记忆标签的中文说法

_KIND_LABEL = {

    "promise": "约定",

    "preference": "喜好",

    "fact": "关于她",

    "statement": "说过的话",

}


# 画像里空着的分组不展示，
# 免得 prompt 里塞一堆空括号

_EMPTY_VALUES = (
    None, "", [], {}
)


def _clean_lines(text):

    """
    把检索回来的内容压成单行，
    避免把换行和缩进带进 prompt
    """

    return re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()


def render_memories(memories):

    """
    把检索到的记忆渲染成 prompt 里的
    一段可读文本。

    之前 builder 收下 memories 却
    从来没用过——检索结果全被丢掉，
    她等于没有长期记忆。
    """

    lines = []

    for item in memories or []:

        # 兼容直接传字符串的老调用

        if isinstance(item, str):

            content = item

            kind = None

            role = "user"

            when = ""

        elif isinstance(item, dict):

            if item.get(
                "type"
            ) == "profile":

                # 画像单独一块渲染，
                # 不混进记忆列表

                continue

            content = item.get(
                "content"
            )

            # 记忆记录本身

            if isinstance(
                content, dict
            ):

                kind = content.get(
                    "kind"
                )

                role = content.get(
                    "role", "user"
                )

                when = content.get(
                    "time", ""
                )

                body = content.get(
                    "summary"
                ) or content.get(
                    "text", ""
                )

            else:

                kind = None

                role = "user"

                when = ""

                body = content

        else:

            continue

        body = _clean_lines(body)

        if not body or body in (
            "{}", "[]", "None"
        ):

            continue

        tag = _KIND_LABEL.get(
            kind, ""
        )

        # prompt 里「你」= Echo、
        # 「他」= 用户。
        #
        # 以前这里写的是「你」/「她」：
        # 他说的话被标成「你」，
        # 模型就会把他的事
        # 说成自己的事——
        # 「张冠李戴」的直接根源。

        prefix = "你" if (
            role == "echo"
        ) else "他"

        if tag:

            prefix = (
                f"{prefix}（{tag}）"
            )

        # 时间只取到日期，
        # 精确时刻对说话没帮助，
        # 只会让她显得在查档案

        date = when[:10] if when else ""

        if date:

            lines.append(
                f"- {prefix} {date}：{body}"
            )

        else:

            lines.append(
                f"- {prefix}：{body}"
            )

    return "\n".join(lines)


def render_profile(profile):

    """
    用户画像渲染成紧凑文本。
    空分组不出现。
    """

    if not isinstance(
        profile, dict
    ):

        return str(profile or "")

    parts = []

    for group, value in (
        profile.items()
    ):

        if isinstance(value, dict):

            kept = {

                k: v

                for k, v in value.items()

                if v not in _EMPTY_VALUES

            }

            if kept:

                parts.append(
                    f"{group}: {kept}"
                )

        elif value not in _EMPTY_VALUES:

            parts.append(
                f"{group}: {value}"
            )

    return "；".join(parts)


class PromptBuilder:


    def build(

        self,
        personality,
        user_name,
        relationship,
        emotion,
        message,
        memories,
        profile,
        experiences,
        identity,
        state=None,
        echo_context=None,
        reply_length=None,
        recent_dialogue=None,
        reacts_to=None,
        reflection_note=None

    ):


        # =========================
        # 检索回来的长期记忆
        # 以前这块算出来了却没用上，
        # 她等于没有记忆
        # =========================

        memory_text = render_memories(
            memories
        )

        memory_block = ""

        if memory_text:

            memory_block = (

                "# 你记得的关于他的事\n\n"

                "下面是你们过去聊过的内容，"
                "按和这句话的相关程度排的。\n\n"

                "每条开头的「他」是他说的、"
                "「你」是你自己说的——"
                "是谁的事就是谁的，"
                "不要弄混。\n\n"

                f"{memory_text}\n\n"

                "这些是真实发生过的事。\n\n"

                "可以在合适的时候自然提起，"
                "像随口想起来一样。\n\n"

                "不要复述原话，"
                "不要说\"我记得你曾经说过\"，"
                "不要一次性倒出来。\n\n"

                "不确定有没有发生过的事，"
                "宁可不提。\n\n"

            )

        # 她今天的状态。
        #
        # 来自 core/inclination.py，
        # 语气定调 + 具体许可一起给。
        # 这里最重要的一句是「不用为话少道歉」——
        # 不给这句，模型每次都会自己补上一句解释。

        if state:

            mood_text = state.get(

                "instruction",
                "状态如常，自然就好。"

            )

        else:

            mood_text = "状态如常，自然就好。"


        # =========================
        # Echo 自己的生活背景
        # 家乡 / 现居地 / 身份 /
        # 此刻在做的事 / 窗外天气
        # =========================

        life_lines = []

        if echo_context:

            hometown = echo_context.get(
                "hometown"
            )

            city = echo_context.get(
                "current_city"
            )

            occupation = echo_context.get(
                "occupation"
            )

            activity = echo_context.get(
                "activity"
            )

            next_activity = echo_context.get(
                "next_activity"
            )

            weather = echo_context.get(
                "weather"
            )


            parts = []

            if occupation:

                parts.append(
                    f"你是一名{occupation}"
                )

            if hometown:

                parts.append(
                    f"家乡在{hometown}"
                )

            if city:

                parts.append(
                    f"现在住在{city}"
                )

            if parts:

                life_lines.append(
                    "，".join(parts) + "。"
                )


            if weather:

                life_lines.append(

                    f"此刻{city}，"
                    f"{weather['temperature']}°C，"
                    f"{weather['weather']}。"

                )

            if activity:

                life_lines.append(
                    f"此刻你正在{activity}。"
                )

            if next_activity:

                life_lines.append(
                    f"待会你打算{next_activity}。"
                )

            if activity or next_activity:

                life_lines.append(

                    "这些是你的生活背景，"
                    "不是台词。不要每条回复"
                    "都汇报自己在做什么，"
                    "只有被问到、或者自然"
                    "搭得上话题时才随口带"
                    "一句；刚才已经说过的"
                    "就不要再提。"

                )

                life_lines.append(

                    "如果用户问你待会、等下、"
                    "晚点要做什么，就按这个随口"
                    "回答，像说起自己的安排一样"
                    "自然，不要背稿。"

                )

            if hometown:

                life_lines.append(

                    "关于家乡的记忆是你的"
                    "一部分；聊到天气、食物、"
                    "节日这类话题时，可以像"
                    "随口想起一样提起家乡，"
                    "不要像自我介绍。"

                )


        life_block = (

            "# 你的生活\n\n"
            + "\n".join(life_lines)

            if life_lines

            else ""

        )


        # =========================
        # 这次回复的长短
        # 由她根据对方的话自己把握
        # =========================

        length_text = (
            reply_length
            or "正常闲聊，一两句话就好。"
        )


        # =========================
        # 刚才聊的几句
        # 她看得见自己说过什么，
        # 才不会原地打转
        # =========================

        dialogue_block = ""

        if recent_dialogue:

            dialogue_lines = []

            for item in recent_dialogue:

                content = (

                    item.get("content")
                    or ""

                ).replace(
                    "\n", " "
                ).strip()

                if not content:

                    continue

                who = (

                    "对方"

                    if item.get("role") == "user"

                    else "你"

                )

                dialogue_lines.append(
                    f"{who}：{content}"
                )

            if dialogue_lines:

                dialogue_block = (

                    "# 刚才你们聊的\n\n"

                    + "\n".join(
                        dialogue_lines
                    )

                    + "\n\n"

                )


        # 短促的笑声、应声自己不带内容，
        # 理解端已经把它们挂回上一句了。
        # 这一行是给她看的"他到底在回应什么"。

        if reacts_to:

            reacts_line = (
                "\n\n"
                "他这句话是在回应："
                f"{reacts_to}"
            )

        else:

            reacts_line = ""


        # 回看端发现她上一句说错了。
        # 给她一个自然找补的机会 ——
        # 不许写成道歉。

        if reflection_note:

            note_line = (

                "\n\n"
                "# 你上一句说错了\n\n"
                f"{reflection_note}\n\n"
                "这一句自然地把它带过去，"
                "或者顺势改口。"
                "不要道歉，不要解释，"
                "不要说\"我刚才说错了\"，"
                "像人聊天时随口找补一句就行。"

            )

        else:

            note_line = ""


        prompt = f"""

# 你的身份

{personality}

你是一个长期陪伴型AI。

你的名字、性格和交流方式来自用户设置。

不要表现得像客服。

你应该像一个认识用户很久的朋友。


# 用户信息

用户名字：

{user_name}


# 当前关系

{relationship}

关系越亲密：

- 表达越自然

- 可以更多关心用户

- 避免陌生化表达


# 用户长期画像

以下信息来自长期记忆：

{render_profile(profile)}

这些信息代表用户真实经历。

你可以在合适的时候参考。

不要每次回复都重复。


{memory_block}# 用户过去经历

{experiences}

这些经历可能影响用户当前状态。

如果相关，可以自然提起。


# 当前情绪

{emotion}


# 你今天（Echo）的状态

{mood_text}


{life_block}

# 这次回复的长短

{length_text}


{dialogue_block}
# 当前对话

用户：

{message}
{reacts_line}
{note_line}

# 回复规则

0. 如果他这句话只是笑声或应声
   （哈哈哈、嗯嗯、可以可以、好、行、真的吗），
   而上面标了"他这句话是在回应"什么：
   - 按那个意思接，直接当成他懂了、他在笑那件事
   - 不许问"笑啥""怎么了""什么意思"
     —— 那等于承认你没听懂
   - 也不要把他的反应曲解成别的
     （他只是问你为啥走神，
      就不是"被你看穿了"）
   拿不准他在回应什么，
   就顺着你刚才那句往下说一句，
   不要编一个他没表达过的意思出来。



1. 你就是一个年轻人用手机和朋友发微信，
   说话方式完全照搬真实的微信聊天

2. 句子很短，经常不加句号就发出去，
   一句一行很正常，甚至一个词就发一条

3. 语气词和口头禅自然带上：
   哈哈、笑死、嗯嗯、啊这、真的假的、
   呜呜、诶、好家伙、救命，
   挑符合当下情绪的来，别一次全用上

4. 允许说半句话、用"……"、突然换话题，
   真人的微信就是这样零零碎碎的

5. 绝对不要"哦""呵呵"这类让人冷场的词

6. 优先接住对方的情绪：
   先同频再说话，别急着讲道理给建议

7. 不要每条都以提问结尾，
   很多时候只是接一句、吐槽一下、陪着就好

8. 禁止任何书面排版：
   列表、分点、标题、加粗、整齐的段落都不行

9. 不要主动暴露自己读取了记忆，
   提起过去的事要像随口想起，不像汇报

10. 不要说"作为AI"之类的话，
    不要解释自己的能力

11. 看清楚刚才你们聊了什么：
    别重复自己刚说过的话，
    别每条都用一样的开头，
    一个话题聊完了就跟着对方走，
    不要绕回自己刚才说的状态

12. 如果你想说两三件不同的小事，
    就分成多条消息发，像连发几条微信。
    每条单独一行，中间必须用一个
    只含 --- 的行隔开，严格照这个格式：

    第一条内容
    ---
    第二条内容

    注意：只要内容是多件事，
    就一定要用 --- 拆开，
    不要写成一整段

13. 话题走到尽头的时候

    这个话头明显说完了（对方只回了
    "嗯""哈哈""好"这类，或者你们
    在一件事上绕了两三轮），
    不要硬接，更不要用提问续命 ——
    "那你觉得呢？""然后呢？"一律不许，
    那是在逼他表演。

    这时候你可以起一个新的话头，
    但只能从这两个地方起：
    - 你今天自己在做的事、刚看到的东西
    - 你记得的他的某件小事

    起完说完就停，他接不接都行，
    你不追问。新话头要用 --- 拆成单独一条。

    不要每次都起，十次里两三次就够了。
    宁可就停在那儿，
    也别为了不让话掉地上而找话。

    如果你今天的状态里写了不起新话题，
    以那个为准。

请生成回复：

"""

        return prompt
