# emotion.py
#
# 情绪分析：
# 优先用大模型判断，
# 失败或没有模型时退回关键词规则

import json
import re


class EmotionAnalyzer:


    def __init__(self, llm=None):

        self.llm = llm


    def analyze(self, text):

        # =========================
        # 1. 大模型判断
        # =========================

        if self.llm:

            try:

                return self._llm_analyze(
                    text
                )

            except Exception as e:

                print(
                    "情绪分析模型调用失败，"
                    "退回规则判断:",
                    e
                )


        # =========================
        # 2. 关键词规则兜底
        # =========================

        return self._rule_analyze(text)



    # =========================
    # 大模型情绪分析
    # =========================

    def _llm_analyze(self, text):

        prompt = f"""

请分析下面这句话里说话人的情绪状态。

原话：

{text}

只返回JSON，不要返回任何其他内容：

{{

  "emotion": "happy/sad/tired/anxious/angry/neutral 之一",

  "intensity": 0到1之间的小数,

  "need": "comfort/listen/share/advice/normal 之一"

}}

"""

        raw = self.llm.generate(

            prompt,

            system="你是一个情绪分析器，只输出JSON。"

        )


        # 从回复中提取JSON
        # （模型有时会包一层废话）

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


        # 校验字段，缺了就走规则兜底

        if (

            "emotion" not in result

            or "intensity" not in result

            or "need" not in result

        ):

            raise ValueError(
                "JSON字段不完整"
            )


        result["intensity"] = max(

            0.0,

            min(

                1.0,

                float(result["intensity"])

            )

        )


        return result



    # =========================
    # 关键词规则兜底
    # =========================

    def _rule_analyze(self, text):

        emotion = "neutral"

        intensity = 0.0

        need = "normal"


        if "累" in text or "疲惫" in text:

            emotion = "tired"

            intensity = 0.7

            need = "comfort"


        elif "难过" in text or "伤心" in text:

            emotion = "sad"

            intensity = 0.8

            need = "listen"


        elif "开心" in text or "高兴" in text:

            emotion = "happy"

            intensity = 0.8

            need = "share"


        return {

            "emotion": emotion,

            "intensity": intensity,

            "need": need

        }
