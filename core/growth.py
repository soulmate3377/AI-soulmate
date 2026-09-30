from core.personality_state import PersonalityState



class GrowthSystem:



    def __init__(self, state=None):

        # 默认自建状态；
        # 由 Brain 注入时共享同一份人格状态

        self.state = (
            state or PersonalityState()
        )



    def apply(
        self,
        reflection
    ):


        for item in reflection.get(
            "adjustments",
            []
        ):


            self.state.update(

                item["parameter"],

                item["value"]

            )



        return self.state.get()