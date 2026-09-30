from datetime import datetime


class DecisionEngine:


    def decide(
        self,
        state,
        relationship,
        memories
    ):


        score = 0



        # =================
        # 1. Time: silence past 24h adds weight
        # 1. 时间因素：超过 24 小时没聊就加分

        last_time = state.get(
            "last_chat_time"
        )


        if last_time:

            last = datetime.strptime(
                last_time,
                "%Y-%m-%d %H:%M:%S"
            )


            now = datetime.now()


            # Use total_seconds(); .seconds drops whole days.
            # 要用 total_seconds()；.seconds 不含整天，隔天以上会算错

            hours = (
                (now-last)
                .total_seconds() / 3600
            )


            if hours > 24:

                score += 0.3



        # =================
        # 2. Relationship: trust past 0.3 counts
        # 2. 关系因素：trust 超过 0.3 才算数

        trust = relationship.get(
            "trust",
            0
        )


        if trust > 0.3:

            score +=0.3



        # =================
        # 3. Emotion: +0.4 for sad/tired/anxious — not enough on its own
        # 3. 情绪因素：难过/累/焦虑加 0.4，单靠这一项到不了 0.6

        emotion = state.get(
            "current_emotion"
        )


        if emotion:


            if emotion.get(
                "emotion"
            ) in [
                "sad",
                "tired",
                "anxious"
            ]:

                score +=0.4



        # =================
        # Final call: 0.6 or more and she reaches out
        # 决策：总分到 0.6 她就主动联系


        if score >=0.6:

            return {

                "type":"send_message",

                "should_contact":True,

                "reason":score

            }


        else:

            return {

                "type":"none",

                "should_contact":False,

                "reason":score

            }