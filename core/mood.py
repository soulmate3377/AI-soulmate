# mood.py
#
# EchoLover 的每日心情系统
#
# 真人不会每天状态一样。
# 每天清晨她会"醒"在一个稍微不同的状态里：
# 有时活泼，有时安静，有时有点犯困。
# 一天之内保持稳定，第二天重新随机。

import json
import random

from datetime import datetime

from core.paths import resolve_data_file


# 心情池：描述 + 对回复风格的影响

MOODS = [

    {
        "name": "精神不错",
        "desc":
            "今天精力不错，心情平稳。"
            "回复可以自然活泼一点，"
            "有兴致多问一句。",
    },

    {
        "name": "有点安静",
        "desc":
            "今天有点安静，不太想说太多话。"
            "回复比平时简短，"
            "但陪伴感不变。",
    },

    {
        "name": "有点小困",
        "desc":
            "今天有点懒洋洋的。"
            "说话软软的，节奏慢一点，"
            "可以用一点点撒娇的语气。",
    },

    {
        "name": "心情很好",
        "desc":
            "今天心情很好。"
            "会更主动分享想法，"
            "偶尔开个小玩笑、调侃一下用户。",
    },

    {
        "name": "若有所思",
        "desc":
            "今天有点若有所思。"
            "说话会比平时多一点感慨，"
            "容易把话题聊得深一点。",
    },

]


class Mood:


    def __init__(self):

        self.file = resolve_data_file(
            "memory/mood.json"
        )


    # =====================
    # 获取今天的心情
    # 同一天内保持不变
    # =====================

    def current(self):


        today = datetime.now().strftime(
            "%Y-%m-%d"
        )


        # 读已有记录

        data = None

        try:

            with open(

                self.file,
                "r",
                encoding="utf-8"

            ) as f:

                data = json.load(f)

        except (OSError, ValueError):

            data = None


        if (

            data

            and data.get("date") == today

        ):

            return data



        # 新的一天，生成心情

        mood = random.choice(MOODS)


        data = {

            "date": today,

            "name": mood["name"],

            "desc": mood["desc"],

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


        return data
