# special_days.py
#
# The days that only matter because of who he is: his birthday, the day
# you two first talked. Near-term plans already live in followups.json
# with a 72-hour shelf life -- these are the ones that come back every
# year and must never be silently dropped.
# 特别的日子:只因为"他是谁"才重要的日子——他的生日、你们第一次
# 说话的那天。近期安排住在 followups.json 里,过了 72 小时会淡出;
# 这里管的是每年都会回来、绝不能悄悄丢掉的那些。
#
# Two sources, no user config:
#   birthday   <- user_memory.json basic.birthday (a free-text string
#                 perception fills in; parse it, don't trust its format)
#   anniversary<- conversations.json first message time (the day itself,
#                 plus 100/365/1000-day milestones computed on the fly)
# 两个来源,用户不用配置:
#   生日   <- user_memory.json 的 basic.birthday(理解端随手填的
#             自由文本,解析它,但不信它的格式)
#   纪念日 <- conversations.json 第一条消息的时间(纪念日当天,
#             以及满 100/365/1000 天,按天动态算,不入库)
#
# State in memory/events.json. last_asked doubles as the throttle: one
# mention per day, ever -- wishing happy birthday twice is worse than
# missing it once.
# 状态写在 memory/events.json。last_asked 兼作节流:每个日子一天
# 只说一次——生日快乐说两遍比少说一遍更假。

import re

from datetime import datetime

from core import storage


_TIME_FMT = "%Y-%m-%d %H:%M:%S"


# Milestone day counts since first chat. Not every round number --
# only the ones a person would actually notice.
# 认识满多少天算里程碑。不是每个整数都算——只留一个人真会在意的。

MILESTONES = (100, 365, 1000)


# Month lengths checked against a leap year so Feb 29 parses.
# 用闰年校验每月天数,2 月 29 日才过得来。

_DAYS_IN_MONTH = {
    1: 31, 2: 29, 3: 31,
    4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30,
    10: 31, 11: 30, 12: 31,
}


# "1998-05-10" / "1998.5.10" / "1998年5月10日"
# Full dates carry a year; the month-day part is what we keep.

_FULL_DATE_RE = re.compile(
    r"(\d{4})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})"
)


# "5月10日" / "5月10号" / "12月3日"

_MONTH_DAY_RE = re.compile(
    r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?"
)


# "05-10" / "5.10" -- anchored, so prose containing a dash won't match.

_BARE_MD_RE = re.compile(
    r"^(\d{1,2})\s*[-/.]\s*(\d{1,2})$"
)


# First-chat cache. Reading all of conversations.json on every 60-second
# tick is the wrong price, so it is read once per process.
# 第一次聊天日期的缓存。每 60 秒的轮询都重读整份聊天记录不划算,
# 一个进程读一次就够。

_first_chat = None

_first_chat_loaded = False


def _events_file():

    return (
        storage.data_dir()
        / "memory"
        / "events.json"
    )


def _md(m, d):

    return f"{m:02d}-{d:02d}"


def _parse_md(m, d):

    """
    (month, day) -> "MM-DD", or None when out of range.
    (月, 日) -> "MM-DD",越界返回 None。
    """

    try:

        m = int(m)

        d = int(d)

    except (TypeError, ValueError):

        return None

    if m < 1 or m > 12:

        return None

    if d < 1 or d > _DAYS_IN_MONTH.get(m, 0):

        return None

    return _md(m, d)


def parse_birthday(text):

    """
    Free text -> "MM-DD" or None. Tries full date, then Chinese
    month-day, then bare MM-DD. Anything it cannot read it refuses,
    so a half-parsed "birthday" never reaches the calendar.
    自由文本 -> "MM-DD" 或 None。先试完整日期,再中文月日,再裸的
    MM-DD。读不出来就拒绝,不让半懂的"生日"进日历。
    """

    if not isinstance(text, str):

        return None

    text = text.strip()

    if not text:

        return None

    hit = _FULL_DATE_RE.search(text)

    if hit:

        md = _parse_md(hit.group(2), hit.group(3))

        if md:

            return md

    hit = _MONTH_DAY_RE.search(text)

    if hit:

        md = _parse_md(hit.group(1), hit.group(2))

        if md:

            return md

    hit = _BARE_MD_RE.match(text)

    if hit:

        return _parse_md(hit.group(1), hit.group(2))

    return None


def _read_items():

    return (
        storage.read_json(
            _events_file(), []
        )
        or []
    )


def _upsert(items, record):

    """
    Replace by id, append when absent. Returns True when the list
    actually changed, so the caller only writes on a real change.
    按 id 替换,没有就追加。列表真变了才返回 True,调用方只在
    有变化时写盘。
    """

    for i, old in enumerate(items):

        if old.get("id") == record["id"]:

            if old.get("date") == record["date"]:

                return False

            items[i] = record

            return True

    items.append(record)

    return True


def _first_chat_date():

    """
    The date of the very first message, cached per process.
    第一条消息的日期,进程内缓存。
    """

    global _first_chat, _first_chat_loaded

    if _first_chat_loaded:

        return _first_chat

    _first_chat_loaded = True

    _first_chat = None

    try:

        talks = storage.read_json(

            storage.data_dir()
            / "memory"
            / "conversations.json",

            []

        ) or []

        first = (

            talks[0].get("time") or ""

            if talks
            and isinstance(talks[0], dict)

            else ""

        )

        if first:

            _first_chat = datetime.strptime(

                first[:10],
                "%Y-%m-%d"

            ).date()

    except (ValueError, AttributeError, TypeError):

        _first_chat = None

    return _first_chat


def _years_since(first, today):

    years = today.year - first.year

    if (today.month, today.day) < (first.month, first.day):

        years -= 1

    return years


def _matches_today(date_md, today):

    """
    Does this MM-DD land on today? A Feb 29 date fires on Feb 28 in
    non-leap years -- better one day early than a whole year silent.
    这个 MM-DD 是不是今天?2 月 29 的日子在平年落到 2 月 28 触发
    ——宁可早一天,不能整年不说。
    """

    try:

        m, d = (

            int(x)
            for x in date_md.split("-")

        )

    except (ValueError, AttributeError):

        return False

    if (m, d) == (today.month, today.day):

        return True

    return (
        (m, d) == (2, 29)
        and today.month == 2
        and today.day == 28
        and not _is_leap(today.year)
    )


def _is_leap(year):

    return (
        year % 4 == 0
        and (year % 100 != 0 or year % 400 == 0)
    )


def _asked_today(item, today):

    last = item.get("last_asked") or ""

    try:

        return (

            datetime.strptime(
                last, _TIME_FMT
            ).date()
            == today

        )

    except ValueError:

        return False


def sync():

    """
    Pull birthday and first-chat date into events.json. Idempotent,
    runs on every scheduler tick, writes only on a real change.
    把生日和第一次聊天日期同步进 events.json。幂等,每次调度都跑,
    只有真变了才写盘。
    """

    items = _read_items()

    changed = False

    now_text = datetime.now().strftime(
        _TIME_FMT
    )


    # Birthday: from the profile. An emptied field removes the day;
    # an unparseable one keeps yesterday's -- silence beats a guess.

    birthday_raw = ""

    try:

        profile = storage.read_json(

            storage.data_dir()
            / "memory"
            / "user_memory.json",

            {}

        ) or {}

        birthday_raw = (

            (profile.get("basic") or {})
            .get("birthday")
            or ""

        )

    except Exception:

        birthday_raw = ""

    if birthday_raw:

        md = parse_birthday(birthday_raw)

        if md:

            changed = _upsert(
                items,
                {
                    "id": "birthday",
                    "kind": "birthday",
                    "text": "他的生日",
                    "date": md,
                    "source": "profile",
                    "created": now_text,
                },
            ) or changed

    else:

        before = len(items)

        items = [
            i for i in items
            if i.get("id") != "birthday"
        ]

        changed = (
            changed
            or len(items) != before
        )


    # Anniversary: the day of the first message ever recorded.

    first = _first_chat_date()

    if first is not None:

        changed = _upsert(
            items,
            {
                "id": "anniversary",
                "kind": "anniversary",
                "text": "你们认识的日子",
                "date": _md(first.month, first.day),
                "source": "auto",
                "created": now_text,
            },
        ) or changed

    if changed:

        storage.write_json(
            _events_file(), items
        )


def due_today(now=None):

    """
    The special days landing on today, throttled to one mention a day.
   落在今天的特别日子,每天最多提一次。
    """

    today = (

        now or datetime.now()

    ).date()

    items = _read_items()

    out = []

    for item in items:

        date_md = item.get("date") or ""

        if not _matches_today(date_md, today):

            continue

        if _asked_today(item, today):

            continue

        record = dict(item)

        record["date"] = _md_text(date_md)

        if item.get("kind") == "anniversary":

            first = _first_chat_date()

            years = (

                _years_since(first, today)
                if first is not None
                else 0

            )

            # The day they first talked is not an anniversary -- a
            # "we met today" line on day one would be a bug, not a moment.
            # 第一次聊天当天不算纪念日——认识第一天就说"我们今天认识"
            # 是 bug,不是时刻。

            if years < 1:

                continue

            record["text"] = (
                f"你们认识{years}周年的日子"
            )

        out.append(record)


    # Milestones are computed, never stored: the file only ever holds
    # a throttle note saying this one was already said.
    # 里程碑按天算,不入库:文件里最多留一条"已经说过"的节流记录。

    first = _first_chat_date()

    if first is not None:

        days = (today - first).days

        if days in MILESTONES:

            item = {

                "id": f"anniversary-{days}",
                "kind": "milestone",
                "text": f"你们认识满{days}天",
                "date": _md_text(
                    _md(
                        first.month, first.day
                    )
                ),
                "source": "auto",

            }

            already = any(

                i.get("id") == item["id"]
                and _asked_today(i, today)

                for i in items

            )

            if not already:

                out.append(item)

    return out


def _md_text(date_md):

    """"MM-DD" -> "5月10日", for eyes not for parsing.
    "MM-DD" -> "5月10日",给人看的,不是给解析用的。"""

    try:

        m, d = (

            int(x)
            for x in date_md.split("-")

        )

        return f"{m}月{d}日"

    except (ValueError, AttributeError):

        return date_md


def mark_asked(ids):

    """
    Called only after the generated line actually named the day (the
    same slice-match the follow-ups use). One mention per day.
    只在生成的那句话真的提到了这个日子之后才调用(和话茬用同一把
    切片匹配的尺)。一天只许说一次。
    """

    if not ids:

        return

    ids = list(ids)

    now_text = datetime.now().strftime(
        _TIME_FMT
    )

    items = _read_items()

    known = set()

    for item in items:

        if item.get("id") in ids:

            item["last_asked"] = now_text

            known.add(item.get("id"))

    # Computed milestones have no standing record -- leave just enough
    # of one to remember it was said.

    for one in ids:

        if one not in known:

            items.append({
                "id": one,
                "kind": "milestone",
                "text": "",
                "date": "",
                "source": "auto",
                "created": now_text,
                "last_asked": now_text,
            })

    storage.write_json(
        _events_file(), items
    )
