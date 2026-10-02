# tests/test_special_days.py
#
# The first tests in this repo. They cover the pure logic behind the
# event follow-up feature: birthday parsing, which special days land
# on today, the throttle, and the follow-up time window. No network,
# no LLM, and never the real SoulmateData -- every test points
# data_dir() at a throwaway directory.
# 这个仓库的第一批测试。覆盖事件回访功能背后的纯逻辑：
# 生日解析、哪些日子落在今天、节流、话茬的时间窗。
# 不联网、不调模型、绝不碰真实的 SoulmateData ——
# 每个测试都把 data_dir() 指到临时目录。

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock


sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)


from core import special_days  # noqa: E402

from core.scheduler import (  # noqa: E402
    Scheduler,
)


_TIME_FMT = "%Y-%m-%d %H:%M:%S"


def _write(tmp, rel, data):

    path = Path(tmp) / rel

    path.parent.mkdir(
        parents=True, exist_ok=True
    )

    path.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )


def _read(tmp, rel):

    path = Path(tmp) / rel

    if not path.exists():

        return None

    return json.loads(
        path.read_text(encoding="utf-8")
    )


class _TempDataTestCase(unittest.TestCase):

    """
    Base: every data_dir() call lands in a
    throwaway directory, and the first-chat
    cache is reset per test.
    基类：data_dir() 全部指向临时目录，
    每个测试重置第一次聊天的缓存。
    """

    def setUp(self):

        tmp = tempfile.TemporaryDirectory()

        self.addCleanup(tmp.cleanup)

        self.tmp = tmp.name

        patcher = mock.patch(
            "core.special_days.storage.data_dir",
            return_value=Path(self.tmp),
        )

        patcher.start()

        self.addCleanup(patcher.stop)

        special_days._first_chat = None

        special_days._first_chat_loaded = (
            False
        )


class TestParseBirthday(unittest.TestCase):

    def test_chinese_month_day(self):

        self.assertEqual(
            special_days.parse_birthday(
                "5月10日"
            ),
            "05-10",
        )

    def test_full_iso_date(self):

        self.assertEqual(
            special_days.parse_birthday(
                "1998-05-10"
            ),
            "05-10",
        )

    def test_full_chinese_date(self):

        self.assertEqual(
            special_days.parse_birthday(
                "1998年5月10日"
            ),
            "05-10",
        )

    def test_bare_month_day(self):

        self.assertEqual(
            special_days.parse_birthday(
                "05-10"
            ),
            "05-10",
        )

        self.assertEqual(
            special_days.parse_birthday(
                "5.10"
            ),
            "05-10",
        )

    def test_feb29_is_valid(self):

        self.assertEqual(
            special_days.parse_birthday(
                "2月29日"
            ),
            "02-29",
        )

    def test_invalid_dates_rejected(self):

        # 13th month / day beyond month length
        # 十三月 / 超出当月天数的日子

        self.assertIsNone(
            special_days.parse_birthday(
                "13月10日"
            )
        )

        self.assertIsNone(
            special_days.parse_birthday(
                "2月30日"
            )
        )

    def test_garbage_rejected(self):

        for text in (
            "",
            None,
            "随便聊聊",
            "生日还没想好",
        ):

            self.assertIsNone(
                special_days.parse_birthday(
                    text
                )
            )


class TestSyncAndDueToday(
    _TempDataTestCase
):

    def _set_birthday(self, text):

        _write(
            self.tmp,
            "memory/user_memory.json",
            {
                "basic": {
                    "name": "33",
                    "birthday": text,
                }
            },
        )

    def test_birthday_synced_and_fires(
        self,
    ):

        today = date.today()

        # Use the real today so the throttle
        # stamp and the hit land on the same
        # day.
        # 用真实的今天：节流时间戳和命中
        # 落在同一天。

        self._set_birthday(
            f"{today.month}月{today.day}日"
        )

        special_days.sync()

        stored = _read(
            self.tmp,
            "memory/events.json",
        )

        birthday = [
            i
            for i in stored
            if i.get("id") == "birthday"
        ]

        self.assertEqual(len(birthday), 1)

        self.assertEqual(
            birthday[0]["date"],
            f"{today.month:02d}"
            f"-{today.day:02d}",
        )

        hits = special_days.due_today()

        self.assertEqual(
            [i["id"] for i in hits],
            ["birthday"],
        )

        self.assertEqual(
            hits[0]["text"], "他的生日"
        )

    def test_throttled_after_mark_asked(
        self,
    ):

        today = date.today()

        self._set_birthday(
            f"{today.month}月{today.day}日"
        )

        special_days.sync()

        self.assertEqual(
            len(special_days.due_today()), 1
        )

        special_days.mark_asked(
            ["birthday"]
        )

        self.assertEqual(
            special_days.due_today(), []
        )

    def test_sync_is_idempotent(self):

        today = date.today()

        self._set_birthday(
            f"{today.month}月{today.day}日"
        )

        special_days.sync()

        first = _read(
            self.tmp,
            "memory/events.json",
        )

        special_days.sync()

        second = _read(
            self.tmp,
            "memory/events.json",
        )

        self.assertEqual(first, second)

    def test_emptied_birthday_removed(self):

        self._set_birthday("5月10日")

        special_days.sync()

        self._set_birthday("")

        special_days.sync()

        stored = _read(
            self.tmp,
            "memory/events.json",
        )

        self.assertNotIn(
            "birthday",
            [i.get("id") for i in stored],
        )

    def test_unparseable_keeps_old(self):

        self._set_birthday("5月10日")

        special_days.sync()

        self._set_birthday("不知道")

        special_days.sync()

        stored = _read(
            self.tmp,
            "memory/events.json",
        )

        birthday = [
            i
            for i in stored
            if i.get("id") == "birthday"
        ]

        self.assertEqual(
            birthday[0]["date"], "05-10"
        )

    def test_no_anniversary_on_day_one(
        self,
    ):

        # The day they first talked is not an
        # anniversary; a "we met today" line
        # on day one would be a bug.
        # 第一次聊天当天不算纪念日，
        # 认识第一天就说"我们今天认识"
        # 是 bug 不是时刻。

        now = datetime.now()

        _write(
            self.tmp,
            "memory/conversations.json",
            [
                {
                    "time": now.strftime(
                        _TIME_FMT
                    ),
                    "role": "user",
                    "content": "你好",
                }
            ],
        )

        special_days.sync()

        hits = special_days.due_today()

        self.assertEqual(hits, [])

    def test_anniversary_after_years(self):

        now = datetime.now()

        try:

            first = now.replace(
                year=now.year - 2
            )

        except ValueError:

            self.skipTest(
                "Feb 29 edge, skip"
            )

        _write(
            self.tmp,
            "memory/conversations.json",
            [
                {
                    "time": first.strftime(
                        _TIME_FMT
                    ),
                    "role": "user",
                    "content": "你好",
                }
            ],
        )

        special_days.sync()

        hits = special_days.due_today()

        anniversary = [
            i
            for i in hits
            if i.get("id")
            == "anniversary"
        ]

        self.assertEqual(
            len(anniversary), 1
        )

        self.assertIn(
            "2周年",
            anniversary[0]["text"],
        )

    def test_milestone_100_days(self):

        now = datetime.now()

        first = now - timedelta(days=100)

        _write(
            self.tmp,
            "memory/conversations.json",
            [
                {
                    "time": first.strftime(
                        _TIME_FMT
                    ),
                    "role": "user",
                    "content": "你好",
                }
            ],
        )

        special_days.sync()

        hits = special_days.due_today()

        self.assertEqual(
            [i["id"] for i in hits],
            ["anniversary-100"],
        )

        self.assertIn(
            "100天", hits[0]["text"]
        )

        # 200 days is not a milestone
        # 200 天不是里程碑

        special_days.mark_asked(
            ["anniversary-100"]
        )

        _write(
            self.tmp,
            "memory/conversations.json",
            [
                {
                    "time": (
                        now
                        - timedelta(
                            days=200
                        )
                    ).strftime(_TIME_FMT),
                    "role": "user",
                    "content": "你好",
                }
            ],
        )

        special_days._first_chat = None

        special_days._first_chat_loaded = (
            False
        )

        self.assertEqual(
            special_days.due_today(), []
        )


class TestFeb29(unittest.TestCase):

    """
    Fixed-date cases: no throttle involved,
    so no need for the real today.
    固定日期的用例：不涉及节流，
    不需要用真实的今天。
    """

    def setUp(self):

        tmp = tempfile.TemporaryDirectory()

        self.addCleanup(tmp.cleanup)

        self.tmp = tmp.name

        patcher = mock.patch(
            "core.special_days.storage.data_dir",
            return_value=Path(self.tmp),
        )

        patcher.start()

        self.addCleanup(patcher.stop)

        special_days._first_chat = None

        special_days._first_chat_loaded = (
            False
        )

        _write(
            self.tmp,
            "memory/user_memory.json",
            {
                "basic": {
                    "birthday": "2月29日"
                }
            },
        )

        special_days.sync()

    def test_fires_feb28_non_leap(self):

        hits = special_days.due_today(
            datetime(2027, 2, 28)
        )

        self.assertEqual(
            [i["id"] for i in hits],
            ["birthday"],
        )

    def test_quiet_feb28_leap_year(self):

        hits = special_days.due_today(
            datetime(2028, 2, 28)
        )

        self.assertEqual(hits, [])

    def test_fires_feb29_leap_year(self):

        hits = special_days.due_today(
            datetime(2028, 2, 29)
        )

        self.assertEqual(
            [i["id"] for i in hits],
            ["birthday"],
        )


class TestWindowFlags(unittest.TestCase):

    """
    _window_flags(mentioned, due, now)
    -> (keep, due_hit, due_soon)
    """

    NOW = datetime(2026, 10, 2, 12, 0, 0)

    def _flags(self, age_h, due_h=None):

        mentioned = self.NOW - timedelta(
            hours=age_h
        )

        due = (

            self.NOW + timedelta(hours=due_h)
            if due_h is not None
            else None

        )

        return Scheduler._window_flags(
            mentioned, due, self.NOW
        )

    def test_due_hit_just_passed(self):

        self.assertEqual(
            self._flags(2, due_h=-5),
            (True, True, False),
        )

    def test_due_soon_within_24h(self):

        self.assertEqual(
            self._flags(2, due_h=12),
            (True, False, True),
        )

    def test_far_future_kept_quiet(self):

        self.assertEqual(
            self._flags(2, due_h=100),
            (True, False, False),
        )

    def test_expired_dropped(self):

        self.assertEqual(
            self._flags(80, due_h=-80),
            (False, False, False),
        )

    def test_no_due_within_48h(self):

        self.assertEqual(
            self._flags(5),
            (True, False, False),
        )

    def test_no_due_too_old(self):

        self.assertEqual(
            self._flags(50),
            (False, False, False),
        )

    def test_just_mentioned_skipped(self):

        self.assertEqual(
            self._flags(0.5),
            (False, False, False),
        )


class TestLoadFollowUps(
    _TempDataTestCase
):

    """
    _load_follow_ups end-to-end on real
    files (in the temp dir), including the
    consumed flag and the marking.
    _load_follow_ups 在真实文件（临时目录）
    上端到端跑，含 consumed 标记。
    """

    def setUp(self):

        super().setUp()

        self.scheduler = Scheduler(
            mock.Mock()
        )

    def test_due_soon_marked(self):

        now = datetime.now()

        _write(
            self.tmp,
            "memory/followups.json",
            [
                {
                    "text": "明天下午面试",
                    "time": (
                        now
                        - timedelta(hours=2)
                    ).strftime(_TIME_FMT),
                    "due": (
                        now
                        + timedelta(hours=12)
                    ).strftime(_TIME_FMT),
                }
            ],
        )

        items = (
            self.scheduler._load_follow_ups()
        )

        self.assertEqual(len(items), 1)

        self.assertTrue(
            items[0].get("_due_soon")
        )

        self.assertNotIn(
            "_due_hit", items[0]
        )

    def test_consumed_skipped(self):

        now = datetime.now()

        _write(
            self.tmp,
            "memory/followups.json",
            [
                {
                    "text": "明天下午面试",
                    "time": (
                        now
                        - timedelta(hours=2)
                    ).strftime(_TIME_FMT),
                    "due": (
                        now
                        + timedelta(hours=12)
                    ).strftime(_TIME_FMT),
                    "consumed": True,
                }
            ],
        )

        self.assertEqual(
            self.scheduler._load_follow_ups(),
            [],
        )


class TestEventsUsed(unittest.TestCase):

    def test_birthday_recognised(self):

        used = Scheduler._events_used(
            "生日快乐呀！",
            [
                {
                    "id": "birthday",
                    "text": "他的生日",
                }
            ],
        )

        self.assertEqual(used, ["birthday"])

    def test_unrelated_message(self):

        used = Scheduler._events_used(
            "今天天气不错",
            [
                {
                    "id": "birthday",
                    "text": "他的生日",
                }
            ],
        )

        self.assertEqual(used, [])

    def test_empty_inputs(self):

        self.assertEqual(
            Scheduler._events_used(
                "", [{"id": "x", "text": "y"}]
            ),
            [],
        )

        self.assertEqual(
            Scheduler._events_used(
                "随便", []
            ),
            [],
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
