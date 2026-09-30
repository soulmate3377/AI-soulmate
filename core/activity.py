# core/activity.py
#
# Soulmate 自己的日常：
# 她不是永远等你说话，
# 她有课要上、有图要画、有班要上。
#
# 同一小时内活动保持稳定，
# 过一小时自然换下一件事，
# 这样顶栏状态和她嘴里说的
# 是同一件事

import random

from datetime import (
    datetime,
    timedelta,
)


# 各身份的日常安排
_SCHEDULES = {
    "学生": {
        "morning": [
            "在上课，偷偷看了眼窗外",
            "在图书馆背书",
            "在赶昨天没写完的作业",
        ],
        "afternoon": [
            "在上课",
            "在图书馆自习",
            "在操场慢慢走圈",
        ],
        "evening": [
            "在写作业",
            "在宿舍看剧",
            "在食堂纠结吃什么",
        ],
        "night": [
            "在刷手机",
            "在收拾书包准备睡觉",
        ],
    },
    "设计师": {
        "morning": [
            "在改一版海报",
            "在翻灵感网站找参考",
        ],
        "afternoon": [
            "在和客户对需求",
            "在调一个怎么都不对的配色",
        ],
        "evening": [
            "在赶稿子",
            "在给自己画点小东西放松",
        ],
        "night": [
            "在整理素材库",
            "在听歌发呆",
        ],
    },
    "程序员": {
        "morning": [
            "在看昨晚的报错日志",
            "在写一个新功能",
        ],
        "afternoon": [
            "在开需求会",
            "在和一个 bug 较劲",
        ],
        "evening": [
            "在等构建跑完",
            "在补今天没写完的代码",
        ],
        "night": [
            "在看技术文章",
            "在给 side project 添两行代码",
        ],
    },
    "教师": {
        "morning": [
            "在备课",
            "在批作业",
        ],
        "afternoon": [
            "在上课",
            "在找学生谈话",
        ],
        "evening": [
            "在批试卷",
            "在准备明天的课件",
        ],
        "night": [
            "在看书",
            "在泡脚休息",
        ],
    },
    "自由职业": {
        "morning": [
            "刚起床，在冲咖啡",
            "在安排今天的活",
        ],
        "afternoon": [
            "在做手上的项目",
            "在咖啡馆干活",
        ],
        "evening": [
            "在出门散步",
            "在拍点照片",
        ],
        "night": [
            "在看电影",
            "在记账复盘今天",
        ],
    },
}

_DEFAULT = {
    "morning": [
        "在看一本书",
        "在整理桌面",
    ],
    "afternoon": [
        "在看书",
        "在窗边发呆",
    ],
    "evening": [
        "在做饭",
        "在听音乐",
    ],
    "night": [
        "在写日记",
        "准备睡了",
    ],
}


def _slot(hour):

    if 6 <= hour < 11:

        return "morning"

    if 11 <= hour < 18:

        return "afternoon"

    if 18 <= hour < 23:

        return "evening"

    return "night"


class ActivityEngine:


    def _pick(self, occupation, moment):

        schedule = _SCHEDULES.get(
            occupation, _DEFAULT
        )

        pool = schedule[_slot(moment.hour)]

        # 种子含日期和半小时段：
        # 每半小时自然换下一件事，
        # 同一半小时内任何入口拿到的
        # 都是同一件事

        half = moment.minute // 30

        rng = random.Random(

            f"{occupation}-"
            f"{moment:%Y-%m-%d-%H}-{half}"
        )

        return rng.choice(pool)


    def current(self, occupation=""):

        return self._pick(
            occupation, datetime.now()
        )


    def later(self, occupation=""):

        # 待会要做的事：
        # 取一小时后所在的时段，
        # 让她能随口说出接下来的安排

        return self._pick(

            occupation,
            datetime.now()
            + timedelta(hours=1),
        )
