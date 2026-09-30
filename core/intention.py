class IntentionSystem:

    def __init__(self):
        pass

    def _her_name(self):
        """
        她的名字（档案里起过的优先），
        用户消息里提到名字 = 在聊她的事。
        """
        try:
            from core.identity import (
                Identity,
            )
            return (
                Identity().get("echo_name")
                or "Soulmate"
            )
        except Exception:
            return "Soulmate"

    def analyze(
        self,
        state,
        identity,
        memories
    ):
        intents = []

        # 1. Emotional care: state shows a low mood
        # 1. 情绪关怀：state 显示近期情绪状态较低。
        # state.json keeps it under current_emotion as {"emotion": "sad", ...}
        # state.json 里存在 current_emotion 下，形如 {"emotion": "sad", ...}
        emotion_data = (
            state.get(
                "current_emotion"
            )
            or state.get(
                "emotion"
            )
        )
        if isinstance(
            emotion_data,
            dict
        ):
            emotion = emotion_data.get(
                "emotion",
                ""
            )
        else:
            emotion = emotion_data or ""
        if emotion in [
            "压力",
            "焦虑",
            "疲惫",
            "难过",
            "sad",
            "tired",
            "anxious"
        ]:
            intents.append({
                "type":
                "emotional_support",
                "reason":
                "用户近期情绪状态较低",
                "priority":
                0.8
            })

        # 2. Goal follow-up: goals may be a dict or a list
        # 2. 目标跟进：goals 可能是 dict 也可能是 list，都取第一条。
        goals = identity.get(
            "goals",
            []
        )
        if goals:
            if isinstance(
                goals,
                dict
            ):
                goal_text = list(
                    goals.values()
                )[0]
            else:
                goal_text = goals[0]
            intents.append({
                "type":
                "goal_follow",
                "reason":
                "用户存在长期目标",
                "goal":
                goal_text,
                "priority":
                0.5
            })

        # 3. Interest chat: same dict-or-list shape as goals
        # 3. 兴趣交流：和 goals 一样有 dict / list 两种形状。
        interests = identity.get(
            "interests",
            []
        )
        if interests:
            if isinstance(
                interests,
                dict
            ):
                interest_text = list(
                    interests.values()
                )[0]
            else:
                interest_text = interests[0]
            intents.append({
                "type":
                "interest_chat",
                "reason":
                "用户存在长期兴趣",
                "topic":
                interest_text,
                "priority":
                0.4
            })

        # 4. Project company: a memory mentioning 项目/开发 or her name is enough
        # 4. 项目陪伴：记忆里提到项目、开发或她的名字就够，命中一条就停。
        for memory in memories:
            text = str(memory)
            if (
                "项目" in text
                or
                "开发" in text
                or
                self._her_name() in text
            ):
                intents.append({
                    "type":
                    "project_follow",
                    "reason":
                    "用户正在推进项目",
                    "priority":
                    0.7
                })
                break
        return intents
