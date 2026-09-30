import json
import os

from core.paths import resolve_data_file



class Identity:


    def __init__(self):


        self.file = resolve_data_file(
            "database/user_profile.json"
        )


        if not os.path.exists(
            self.file
        ):

            self.create_default()



    def create_default(self):


        data = {

            "echo_name":"Echo",

            "avatar":
            "assets/avatar/echo_avatar.png",

            # 留空：让 personality.py 里的
            # 完整默认设定生效。
            # 用户在设置里改过才会有值。

            "personality":"",

            "backstory":"",

            "hometown":"",

            "current_city":"",

            "occupation":"",

            "speaking_style":"",

            "emotional_pattern":"",

            "values":"",

            "quirks":"",

            "boundaries":"",

            "created_time":""

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



    def get(self,key):


        with open(
            self.file,
            "r",
            encoding="utf-8"
        ) as f:


            data=json.load(f)


        return data.get(
            key
        )



    def update(
        self,
        key,
        value
    ):


        with open(
            self.file,
            "r",
            encoding="utf-8"
        ) as f:


            data=json.load(f)



        data[key]=value



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