import json
import os
from datetime import datetime

from core.paths import resolve_data_file



class StateMemory:


    def __init__(self):

        self.file = resolve_data_file(
            "database/state.json"
        )


        if not os.path.exists(self.file):

            data = {

                "last_chat_time": None,

                "last_message": None,

                "last_topic": None,

                "conversation_count": 0,

                "current_emotion": None

            }


            with open(
                self.file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    data,
                    f,
                    ensure_ascii=False,
                    indent=4
                )



    def update(
        self,
        message,
        emotion=None
    ):


        with open(
            self.file,
            "r",
            encoding="utf-8"
        ) as f:

            data=json.load(f)



        data["last_chat_time"] = (
            datetime.now()
            .strftime("%Y-%m-%d %H:%M:%S")
        )


        data["last_message"] = message


        data["conversation_count"] += 1


        if emotion:

            data["current_emotion"] = emotion



        with open(
            self.file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )


        return data



    def get(self):


        with open(
            self.file,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)