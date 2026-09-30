# mood.py
#
# Soulmate - daily mood
# Soulmate 的每日心情系统
# She wakes up a bit different each day: lively, quiet or sleepy
# 她每天醒来状态都不一样：有时活泼，有时安静，有时犯困
# One mood holds all day, then rerolls tomorrow
# 一天之内保持稳定，第二天重新随机

import json
import random

from datetime import datetime

from core.paths import resolve_data_file


# Mood pool: description + how it bends her replies / 心情池

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
    # Today's mood: one roll a day, no reroll inside a day
    # 获取今天的心情：一天只掷一次，当天不重掷
    # =====================

    def current(self):


        today = datetime.now().strftime(
            "%Y-%m-%d"
        )


        # Reuse today's record / 读已有记录

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



        # New day: roll and persist / 新的一天，生成心情

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
