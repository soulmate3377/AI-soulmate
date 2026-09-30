import json
import os

from core.paths import resolve_data_file



class UserIdentity:



    def __init__(self):


        self.file = resolve_data_file(
            "memory/user_identity.json"
        )


        # Create the file on first run
        # 初始化文件

        if not os.path.exists(
            self.file
        ):


            with open(
                self.file,
                "w",
                encoding="utf-8"
            ) as f:


                json.dump(
                    {

                        "traits": [],

                        "interests": [],

                        "goals": [],

                        "patterns": []

                    },

                    f,

                    ensure_ascii=False,

                    indent=4

                )




    # Save the identity model
    # 保存身份模型

    def save(self, identity):


        with open(
            self.file,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(

                identity,

                f,

                ensure_ascii=False,

                indent=4

            )





    # Read the identity model back
    # 获取身份模型

    def get(self):


        with open(
            self.file,
            "r",
            encoding="utf-8"
        ) as f:


            return json.load(f)





    # Incremental update
    # 增量更新

    def update_item(
        self,
        category,
        value
    ):


        identity = self.get()



        if category not in identity:


            identity[category] = []



        if value not in identity[category]:


            identity[category].append(
                value
            )



        self.save(
            identity
        )