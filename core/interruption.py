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





        # =====================
        # 1. 没有主动意图
        # =====================


        if not intentions:


            result["reason"] = (

                "没有主动需求"

            )


            return result






        # =====================
        # 2. 时间保护
        # =====================


        hour = datetime.now().hour


        # 时间窗和守门人共用一份
        # 常数，改一处两边都变


        if (

            hour < DAY_START_HOUR

            or

            hour >= DAY_END_HOUR

        ):


            # 高优先级情绪情况允许

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






        # =====================
        # 3. 关系判断
        # =====================


        level = relationship.get(

            "level",

            0

        )


        if level < 0.2:


            result["reason"] = (

                "关系等级不足"

            )


            return result





        # =====================
        # 4. 选择最佳意图
        # =====================


        selected = max(

            intentions,

            key=lambda x:

            x.get(

                "priority",

                0

            )

        )





        # =====================
        # 5. 优先级判断
        # =====================


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