import json
import os

from core.paths import resolve_data_file



class PersonalityState:



    def __init__(self):


        self.file = resolve_data_file(
            "memory/personality_state.json"
        )


        if not os.path.exists(
            self.file
        ):


            self.state = {

                "warmth":0.8,

                "patience":0.9,

                "curiosity":0.8,

                "technical_depth":0.5,

                "humor":0.5,

                "emotional_support":0.7

            }


            self.save()



        else:


            self.load()




    # =====================
    # Save the personality state / 保存人格状态
    # =====================

    def save(self):


        with open(

            self.file,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                self.state,

                f,

                ensure_ascii=False,

                indent=4

            )





    # =====================
    # Load the personality state / 加载人格状态
    # =====================

    def load(self):


        with open(

            self.file,

            "r",

            encoding="utf-8"

        ) as f:


            self.state = json.load(f)





    # =====================
    # Read the state dict / 获取状态
    # =====================

    def get(self):


        return self.state





    # =====================
    # Nudge one trait value / 更新人格参数
    # =====================

    def update(

        self,

        key,

        value

    ):


        if key in self.state:


            self.state[key] += value



            # Clamp at 1.0 / 最大限制

            if self.state[key] > 1:


                self.state[key] = 1



            # Clamp at 0.0 / 最小限制

            if self.state[key] < 0:


                self.state[key] = 0



            self.save()