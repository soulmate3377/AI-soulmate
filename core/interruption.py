from datetime import datetime
from core.proactive_guard import (
    DAY_START_HOUR,
    DAY_END_HOUR,
)


class InterruptionControl:

    def __init__(self):
        self.min_priority = 0.5

    def check(
        self,
        intentions,
        state,
        relationship
    ):
        result = {
            "allowed":
            False,
            "reason":
            "",
            "selected":
            None
        }

        # 1. No proactive intention, nothing to do
        # 1. 没有主动意图，直接返回。
        if not intentions:
            result["reason"] = (
                "没有主动需求"
            )
            return result

        # 2. Time guard: at night only high-priority emotional support gets through
        # 2. 时间保护：夜里只有高优先级的情绪关怀放行。
        hour = datetime.now().hour

        # Same window constants as the guard, so one edit updates both
        # 时间窗和守门人共用一份常量，改一处两边都生效
        if (
            hour < DAY_START_HOUR
            or
            hour >= DAY_END_HOUR
        ):
            # High-priority emotional support still gets through
            # 高优先级情绪情况仍然放行
            urgent = False
            for item in intentions:
                if (
                    item.get("type")
                    ==
                    "emotional_support"
                    and
                    item.get(
                        "priority",
                        0
                    )
                    >=0.9
                ):
                    urgent = True
            if not urgent:
                result["reason"] = (
                    "当前时间不适合打扰"
                )
                return result

        # 3. Relationship check: below level 0.2 she doesn't butt in
        # 3. 关系判断：等级低于 0.2 就不打扰。
        level = relationship.get(
            "level",
            0
        )
        if level < 0.2:
            result["reason"] = (
                "关系等级不足"
            )
            return result

        # 4. Pick the best intention by priority
        # 4. 选择最佳意图：按 priority 取最大。
        selected = max(
            intentions,
            key=lambda x:
            x.get(
                "priority",
                0
            )
        )

        # 5. Priority check: below the threshold it isn't worth interrupting
        # 5. 优先级判断：低于阈值就不值得打扰。
        if (
            selected.get(
                "priority",
                0
            )
            <
            self.min_priority
        ):
            result["reason"] = (
                "主动价值不足"
            )
            return result
        result["allowed"] = True
        result["selected"] = selected
        result["reason"] = (
            "允许主动联系"
        )
        return result
