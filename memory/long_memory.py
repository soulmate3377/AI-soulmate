import json
import os

from core.paths import resolve_data_file




class LongMemory:


    def __init__(self):


        self.profile_file = resolve_data_file(
            "memory/user_memory.json"
        )


        self.experience_file = resolve_data_file(
            "memory/experience_memory.json"
        )



        # 初始化用户画像

        if not os.path.exists(
            self.profile_file
        ):

            self.init_profile()



        # 初始化经历记忆

        if not os.path.exists(
            self.experience_file
        ):

            with open(
                self.experience_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    [],
                    f,
                    ensure_ascii=False,
                    indent=4
                )




    # =========================
    # 创建用户画像
    # =========================

    def init_profile(self):


        data = {


            "basic":{

                "name":"",

                "birthday":"",

                "career":""

            },


            "preferences":{


                "hobbies":[],

                "favorite_music":[],

                "favorite_topics":[]


            },


            "goals":{


                "dreams":[],

                "plans":[]


            },


            "events":[]


        }



        with open(
            self.profile_file,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(

                data,

                f,

                ensure_ascii=False,

                indent=4

            )





    # =========================
    # 原子写入：
    # 先写临时文件再替换，
    # 中途断电/崩溃也不会留下
    # 半个 JSON
    # =========================

    @staticmethod
    def _save_json(path, data):

        tmp = path + ".tmp"

        with open(
            tmp,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(

                data,

                f,

                ensure_ascii=False,

                indent=4

            )

        os.replace(tmp, path)



    # =========================
    # 更新单个资料
    # =========================

    def update_profile(

        self,

        category,

        key,

        value

    ):


        with open(
            self.profile_file,
            "r",
            encoding="utf-8"
        ) as f:

            data=json.load(f)



        # 分析器可能提取出
        # schema 里没有的新键，
        # 没有就当场建，不崩

        category_data = data.setdefault(
            category, {}
        )

        category_data[key]=value


        self._save_json(
            self.profile_file, data
        )





    # =========================
    # 添加列表记忆
    # =========================

    def add_profile_item(

        self,

        category,

        key,

        value

    ):


        with open(
            self.profile_file,
            "r",
            encoding="utf-8"
        ) as f:

            data=json.load(f)




        # 同上：新类别/新键
        # 自动落位

        category_data = data.setdefault(
            category, {}
        )

        items = category_data.setdefault(
            key, []
        )

        if not isinstance(items, list):

            items = [items]

            category_data[key] = items


        if value not in items:


            items.append(value)



        self._save_json(
            self.profile_file, data
        )





    # =========================
    # 获取用户画像
    # =========================

    def get_profile(self):


        with open(

            self.profile_file,

            "r",

            encoding="utf-8"

        ) as f:


            return json.load(f)





    # =========================
    # 经历记忆
    # =========================

    def add_experience(

        self,

        memory

    ):


        with open(
            self.experience_file,
            "r",
            encoding="utf-8"
        ) as f:

            data=json.load(f)



        data.append(
            memory
        )



        self._save_json(
            self.experience_file, data
        )





    def get_experiences(

        self,

        limit=5

    ):


        with open(
            self.experience_file,
            "r",
            encoding="utf-8"
        ) as f:


            data=json.load(f)



        return data[-limit:]