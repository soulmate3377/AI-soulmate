# memory_analyzer.py
#
# Memory analysis: let the LLM judge importance and category first, fall back
# to keyword rules when it fails or there is no model.
# 记忆分析：优先用大模型判断重要性和分类，失败或没有模型时退回关键词规则

import json
import re


class MemoryAnalyzer:


    def __init__(self, llm=None):

        self.llm = llm


    def analyze(self, message):

        # 1. Let the LLM judge first
        # 1. 大模型判断

        if self.llm:

            try:

                return self._llm_analyze(
                    message
                )

            except Exception as e:

                print(
                    "记忆分析模型调用失败，"
                    "退回规则判断:",
                    e
                )


        # 2. Keyword rules as the fallback
        # 2. 关键词规则兜底

        return self._rule_analyze(
            message
        )



    # LLM memory analysis
    # 大模型记忆分析

    def _llm_analyze(self, message):

        prompt = f"""

请判断下面这句话值不值得作为长期记忆保存。

原话：

{message}

判断标准：

- 涉及目标、梦想、重要决定 → 很重要

- 涉及喜好、讨厌、习惯 → 比较重要

- 涉及强烈情绪、重要事件 → 比较重要

- 日常闲聊、客套话 → 不重要

只返回JSON，不要返回任何其他内容：

{{

  "type": "goal/preference/emotion/important_event/normal 之一",

  "category": "goals/preferences/events 之一，普通内容填null",

  "key": "该信息的关键词，没有填null",

  "importance": 0到1之间的小数

}}

"""

        raw = self.llm.generate(

            prompt,

            system="你是一个记忆分析器，只输出JSON。"

        )


        match = re.search(

            r"\{.*\}",

            raw,

            re.DOTALL

        )


        if not match:

            raise ValueError(
                "模型未返回JSON"
            )


        result = json.loads(
            match.group(0)
        )


        if "importance" not in result:

            raise ValueError(
                "JSON缺少importance字段"
            )


        result["content"] = message

        result["importance"] = max(

            0.0,

            min(

                1.0,

                float(result["importance"])

            )

        )


        # Normalize the "null" string to None
        # null 字符串统一转成 None

        for field in (

            "category",
            "key"

        ):

            if result.get(field) in (

                "null",
                "",
                "无"

            ):

                result[field] = None


        result.setdefault(
            "type",
            "normal"
        )


        return result



    # Keyword-rule fallback
    # 关键词规则兜底

    def _rule_analyze(self, message):

        importance = 0

        memory_type = "normal"

        category = None

        key = None


        rules = {

            "goal":{

                "words":[

                    "想成为",
                    "希望成为",
                    "希望以后",
                    "以后成为",
                    "目标是",
                    "梦想是",
                    "我的目标",
                    "我想做",
                    "未来想"

                ],

                "importance":0.8,

                "category":"goals",

                "key":"dreams"

            },


            "preference":{

                "words":[

                    "喜欢",
                    "讨厌",
                    "偏好",
                    "爱好"

                ],

                "importance":0.6,

                "category":"preferences",

                "key":"hobbies"

            },


            "emotion":{

                "words":[

                    "难过",
                    "开心",
                    "焦虑",
                    "压力",
                    "累",
                    "迷茫"

                ],

                "importance":0.5,

                "category":None,

                "key":None

            },


            "important_event":{

                "words":[

                    "第一次",
                    "成功",
                    "失败",
                    "决定",
                    "改变人生"

                ],

                "importance":0.7,

                "category":"events",

                "key":None

            }

        }


        for t, rule in rules.items():

            for word in rule["words"]:

                if word in message:

                    memory_type = t

                    importance = rule["importance"]

                    category = rule["category"]

                    key = rule["key"]


        return {

            "type": memory_type,

            "category": category,

            "key": key,

            "content": message,

            "importance": importance

        }
