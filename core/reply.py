# reply.py
#
# Replies get split so Soulmate texts like a person: several short
# messages instead of one wall of text.
# 回复消息切分：让 Soulmate 像真人一样分几条短消息说话，
# 别让一整段话全糊在一个气泡里。
#
# Three layers, first hit wins — separators (--- / ——— / ***),
# then blank lines, then sentence fallback for a long paragraph.
# 三层策略：先按分隔符（---、———、*** 都认），再按空行，
# 最后按句子兜底切。

import re


# Separators come in several spellings — the model won't stick to ---
# 分隔符有好几种写法，模型不一定乖乖只用 ---

_SEP = (
    r"(?:-{3,}|—{2,}|–{3,}|\*{3,})"
)

_SEP_RE = re.compile(

    r"\n\s*" + _SEP + r"\s*(?=\n|$)"

)


# Sentence-ending punctuation / 句子结尾标点

_SENT_END = (
    "。！？!?…~"
)


def split_reply(text):


    if not text:

        return []


    # Separators first, blank lines second / 先按分隔符，其次按空行

    parts = _SEP_RE.split(text)

    if len(parts) <= 1:

        parts = re.split(
            r"\n{2,}", text
        )


    result = []

    for part in parts:

        part = part.strip()

        if part:

            result.append(part)


    # Still one piece, but clearly a long paragraph — a wall of text
    # shouldn't land in a single bubble.
    # 仍然只有一条但明显是一长段话，按句子兜底分组，别糊在一个气泡里。

    if (

        len(result) <= 1

        and result

        and len(result[0]) > 60

    ):

        grouped = _split_by_sentence(
            result[0]
        )

        if len(grouped) > 1:

            result = grouped


    return result



def _split_by_sentence(text):


    sents = [

        s.strip()

        for s in re.split(

            r"(?<=["
            + _SENT_END
            + r"])\s*",

            text

        )

        if s.strip()

    ]


    # 2~3 sentences isn't long, don't force it / 两三句不算长，不硬拆

    if len(sents) <= 2:

        return [text]


    # 2~3 sentences per message, max 3 / 每条 2~3 句，最多拆 3 条

    n_groups = min(

        3,

        max(2, round(len(sents) / 2.5))

    )

    per = -(-len(sents) // n_groups)


    return [

        "".join(sents[i:i + per])

        for i in range(
            0, len(sents), per
        )

    ]
