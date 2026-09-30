from core.personality_state import PersonalityState




class PersonalityEvolver:



    def __init__(self, state=None):

        # Own state by default, shared with Brain when injected
        # 默认自建状态；由 Brain 注入时共享同一份人格状态

        self.state = (
            state or PersonalityState()
        )



    def evolve(
        self,
        identity
    ):



        # Tech-leaning interests and goals / 技术倾向

        interests = (
            identity.get(
                "interests",
                []
            )
        )


        goals = (
            identity.get(
                "goals",
                []
            )
        )



        if (
            "人工智能" in interests
            or
            "AI" in interests
        ):


            self.state.update(

                "technical_depth",

                0.1

            )



        for goal in goals:


            if (
                "工程师" in goal
                or
                "开发" in goal
            ):


                self.state.update(

                    "technical_depth",

                    0.1

                )



        return (
            self.state.get()
        )