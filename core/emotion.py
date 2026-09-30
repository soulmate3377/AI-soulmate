# emotion.py
# Emotion analysis: LLM first, keyword rules as fallback
# 情绪分析：优先大模型判断，失败或没模型时退回关键词规则

import json
import re


class EmotionAnalyzer:

    def __init__(self, llm=None):
        self.llm = llm

    def analyze(self, text):
        # 1. LLM pass: only when a model is configured, and the call can throw
        # 1. 大模型判断：只有配了模型才走这里，调用可能抛异常。
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

        # 2. Keyword rules: no model at all, or the call above blew up
        # 2. 关键词规则兜底：没模型，或者上面模型调用失败了。
        return self._rule_analyze(text)

    # LLM emotion analysis: returns emotion / intensity / need
    # 大模型情绪分析：返回 emotion/intensity/need，出错由 analyze() 兜底。
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

        # The model sometimes wraps the JSON in chatter, so pull out {...} only
        # 模型有时会包一层废话，所以只抠出 {...}
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

        # Missing fields -> raise, caller falls back to the rules
        # 字段缺了就抛，交给规则兜底
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

    # Keyword rule fallback: crude substring buckets, everything else is neutral
    # 关键词规则兜底：按关键词粗分累、难过、开心，其余都是 neutral。
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
