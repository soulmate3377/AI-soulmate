# relationship.py
#
# 关系系统（事件化）：
#
# 关系不再是"聊够 N 句就升级"
# 的计数器，而是三个维度：
#
#   familiarity 熟悉度——
#       相处时间慢慢泡出来
#   trust      信任——
#       被事件推动：
#       脆弱分享涨、冲突跌、和解大涨
#   bond       纽带——
#       共同经历推动：
#       好消息、第一次、感谢
#
# 每一次关系变化都能说出
# "因为发生了什么"。
#
# 旧版 {level, trust, count} 数据
# 首次打开时自动迁移。

from datetime import datetime

from core.paths import resolve_data_file
from core import storage


# 每种事件对维度的推动

_EVENT_EFFECTS = {

    "脆弱分享": {
        "trust": +0.08,
    },
    "好消息": {
        "bond": +0.05,
    },
    "冲突": {
        "trust": -0.05,
        "bond": -0.03,
    },
    "和解": {
        "trust": +0.10,
        "bond": +0.05,
    },
    "第一次": {
        "bond": +0.06,
    },
    "感谢": {
        "bond": +0.04,
    },

}

# 值得记住的"第一次"
# （写进里程碑，她会记得）

_EVENT_MILESTONE = {

    "脆弱分享": "你第一次对她展露脆弱",
    "好消息": "你第一次跟她分享好消息",
    "冲突": "你们第一次闹别扭",
    "和解": "你们第一次和好",
    "第一次": "你们第一次一起经历的事",
    "感谢": "你第一次认真谢她",

}

_STATUS_TEXT = {
    "stranger": "刚认识不久",
    "friend": "朋友",
    "close": "很亲近的人了",
}


class Relationship:


    def __init__(self):

        self.file = resolve_data_file(
            "database/relationship.json"
        )

        self._data = self._load()


    # ==================================================
    # 读取 + 旧版迁移
    # ==================================================

    def _load(self):

        data = storage.read_json(self.file)

        if not isinstance(data, dict):

            data = None

        # 旧版字段：level / trust /
        # interaction_count / status

        if data is None:

            data = {}

        migrated = {

            "familiarity": float(

                data.get(
                    "familiarity",
                    data.get("level", 0.1)
                )

            ),

            "trust": float(
                data.get("trust", 0.1)
            ),

            "bond": float(

                data.get(
                    "bond",
                    data.get("level", 0.1) * 0.5
                )

            ),

            "interaction_count": int(

                data.get(
                    "interaction_count", 0
                )

            ),

            "events": (
                data.get("events") or []
            ),

            "milestones": (
                data.get("milestones") or []
            ),

        }

        # 阶段一遗留的独立事件日志，
        # 并进来后删掉

        legacy_log = (

            storage.data_dir()

            / "memory"
            / "relationship_events.json"

        )

        legacy = storage.read_json(
            legacy_log, []
        )

        if legacy:

            for item in legacy:

                migrated["events"].append({

                    "event": item.get("event"),
                    "message":
                        item.get("message", ""),
                    "time": item.get("time", ""),

                })

            try:

                legacy_log.unlink()

            except OSError:

                pass


        migrated["status"] = (
            self._derive_status(migrated)
        )

        # 迁移或合并过时落盘一次

        if (

            legacy

            or "familiarity" not in data

        ):

            storage.write_json(
                self.file, migrated
            )


        return migrated


    # ==================================================
    # 综合分 → 关系阶段
    # level 字段保留给打扰判断用
    # ==================================================

    @staticmethod
    def _derive_status(data):

        score = (

            data["familiarity"] * 0.3

            + data["trust"] * 0.4

            + data["bond"] * 0.3

        )

        if score < 0.25:

            return "stranger"

        if score < 0.55:

            return "friend"

        return "close"


    def _save(self):

        self._data["status"] = (
            self._derive_status(self._data)
        )

        storage.write_json(
            self.file, self._data
        )


    # ==================================================
    # 日常互动：
    # 熟悉度慢慢涨，别的不动
    # ==================================================

    def interact(self):

        self._data[
            "interaction_count"
        ] += 1

        self._data["familiarity"] = min(

            1.0,

            self._data["familiarity"]
            + 0.008,

        )

        self._save()

        return self._data


    # ==================================================
    # 关系事件：
    # 真正的推进器。
    # 每种事件的第一次会记为里程碑
    # ==================================================

    def record_event(
        self, event, message=""
    ):

        effects = _EVENT_EFFECTS.get(
            event
        )

        if not effects:

            return


        for dim, delta in effects.items():

            self._data[dim] = max(

                0.0,

                min(

                    1.0,

                    self._data[dim] + delta

                ),

            )


        self._data["events"].append({

            "event": event,

            "message": (message or "")[:80],

            "time": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        })

        # 事件日志留最近 100 条

        self._data["events"] = (
            self._data["events"][-100:]
        )


        milestone = _EVENT_MILESTONE.get(
            event
        )

        if (

            milestone

            and milestone
                not in self._data[
                    "milestones"
                ]

        ):

            self._data[
                "milestones"
            ].append(milestone)


        self._save()


    # ==================================================
    # 给打扰判断用的原始数据
    # （level = 综合分，保持兼容）
    # ==================================================

    def get_status(self):

        data = dict(self._data)

        data["level"] = (

            data["familiarity"] * 0.3

            + data["trust"] * 0.4

            + data["bond"] * 0.3

        )

        return data


    # ==================================================
    # 给 prompt 用的自然语言描述
    # ==================================================

    def describe(self):

        d = self._data

        lines = [

            "你们的关系阶段："
            + _STATUS_TEXT.get(
                d["status"], "朋友"
            )
            + "。"

        ]


        if d["trust"] >= 0.5:

            lines.append(
                "他信任你，"
                "跟你说过不轻易"
                "对别人讲的事。"
            )

        elif d["trust"] >= 0.25:

            lines.append(
                "他在慢慢对你"
                "敞开心扉。"
            )


        if d["milestones"]:

            lines.append(

                "你们之间发生过："

                + "；".join(
                    d["milestones"][-4:]
                )

                + "。"

            )


        recent_events = d["events"][-3:]

        if recent_events:

            lines.append(

                "最近："

                + "；".join(

                    e["event"]

                    for e in recent_events

                )

                + "。"

            )


        return "\n".join(lines)
