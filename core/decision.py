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
        # 1. 时间因素
        # =================

        last_time = state.get(
            "last_chat_time"
        )


        if last_time:

            last = datetime.strptime(
                last_time,
                "%Y-%m-%d %H:%M:%S"
            )


            now = datetime.now()


            # 注意：要用 total_seconds()
            # .seconds 不包含整天数，隔一天以上会算错

            hours = (
                (now-last)
                .total_seconds() / 3600
            )


            if hours > 24:

                score += 0.3



        # =================
        # 2. 关系因素
        # =================

        trust = relationship.get(
            "trust",
            0
        )


        if trust > 0.3:

            score +=0.3



        # =================
        # 3. 情绪因素
        # =================

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
        # 决策
        # =================


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