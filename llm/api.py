import os
import time
import logging

import openai

from openai import OpenAI

from core.paths import data_dir


log = logging.getLogger("echo.llm")


# ==========================================================
# 模型分工
# ----------------------------------------------------------
# Echo 一次对话要调三处模型，
# 这三处的活不一样，不该用同一个模型。
#
#   【理解】每句话之前，阻塞    → Flash + 开思考
#   【回看】说完之后，不阻塞    → Pro   + 开思考
#   【说话】她开口，阻塞        → Flash + 关思考
#
# 这么分是 2026-08-31 实测出来的，
# 不是拍脑袋。原始数据在下面。
#
# ---------- 一、关于「思考」----------
#
# V4 两个模型默认都开着思考。
# 思考能不能关？能。但理解端不能关：
#
#   输入「哈哈哈哈」（上一句是坏消息）
#     开思考 → emotion=sad，reacts_to="自嘲/苦笑"
#     关思考 → emotion=happy            ← 读反了
#
# 两个模型关思考后都读成 happy。
# 用户抱怨的正是「哈哈哈哈她理解不了」，
# 所以理解端和回看端必须留着思考，
# 输出端反过来 —— 她照着理解结果说话，
# 不需要再从零想一遍。
#
# ---------- 二、关于 max_tokens（最要命的一条）----------
#
# 思考用的 token 也算在 max_tokens 额度里。
# 原来这里写的是 400。实测真实理解端 prompt：
#
#   Flash 开思考 用了 795（其中 670 在想）
#   Pro   开思考 用了 1851~2425
#
# 也就是说 400 连 Flash 都装不下，
# 结果就是 finish_reason=length、content 为空 ——
# 不报错，json.loads 抛异常，
# brain 静默退回规则分析，
# understanding=None，reacts_to 永远是 None。
#
# **上一轮给理解端做的「哈哈哈哈」指代消解，
#   大概率从来没生效过。**
#
# 所以 MAX_TOKENS_THINK 给到 2400：
# 这是个上限，不影响计费，
# 花多少还是按实际 token 算。
# 给小了唯一的后果就是她悄悄变笨。
#
# ---------- 三、为什么理解端不上 Pro ----------
#
# 换 Pro 实测过一轮，
# 理解端上 Pro 是净损失：
#
#   Pro   开思考 2000 → 48 秒，理解正确
#   Pro   开思考 4000 → 52 秒，reacts_to 反而丢了
#   Pro   开思考 800  → 20 秒，返回空（想不完）
#   Flash 开思考      → 8.5 秒，理解正确
#
# 理解端在阻塞路径上 ——
# 他发一句话，要等它跑完她才开口。
# 48 秒的沉默不是"更聪明"，是"掉线了"。
#
# Pro 放在回看端：那一步在她说完话之后才跑，
# 慢不慢他感觉不到，正好用来补逻辑。
#
# 三个都能用环境变量单独盖掉，
# 想试 Pro 跑理解端就设 ECHO_MODEL_THINK，
# 不用改代码。
#
# ---------- 四、关于 deepseek-chat ----------
#
# 原来写死的 "deepseek-chat" 实测已被服务端
# 静默映射成 deepseek-v4-flash
# （返回值的 model 字段写的是 v4-flash）。
# 官方 7 月 24 日就宣布下线旧名，
# 现在是兼容期，哪天直接 404 都不意外。
# 所以换成显式的新 ID。
# ==========================================================

def _env_model(name, default):

    return (
        os.environ.get(name, "").strip()
        or default
    )


# ==========================================================
# 服务商与模型
# ----------------------------------------------------------
# 现在不止支持 DeepSeek：
# 任何 OpenAI 兼容接口都能用
# （DeepSeek / Kimi / 智谱 / 千问 / OpenRouter / 本地 Ollama……），
# 在设置页选服务商或手填 Base URL 就行。
#
# 这里只是「什么都没配时」的出厂默认。
# 读取顺序（每个都能单独盖掉）：
#   环境变量 → 设置页保存的配置 → 出厂默认
# ==========================================================

DEFAULT_BASE_URL = "https://api.deepseek.com"

DEFAULT_MODELS = {

    # 理解端：阻塞路径，要快

    "think": "deepseek-v4-flash",

    # 回看端：非阻塞，可以慢，用强模型补逻辑

    "reflect": "deepseek-v4-pro",

    # 说话：要快，且不需要思考

    "speak": "deepseek-v4-flash",
}

# 思考 token 占 max_tokens 的额度。
# 实测 Pro 最坏用掉 2425，所以给 2400 是不够的 ——
# 给 3000 留余量。这只是上限，不影响计费。
MAX_TOKENS_THINK = 3000

# 关掉思考的写法
THINKING_OFF = {"type": "disabled"}


# ==========================================================
# 瞬时错误重试
# ----------------------------------------------------------
# DeepSeek 偶发网络抖动 / 超时 / 限流 / 服务端 5xx，
# 隔一两秒再试一次往往就过了。之前没有重试：
# 她正说着话网络抖一下就直接哑掉。
#
# 认证错误、余额不足、参数不对不在这里重试——
# 重试也没用，只会把真正的报错拖慢。
#
# 流式请求只在"建立连接"这一段重试；
# 已经开始吐字之后断掉不重试，
# 重试同一段会输出两遍。
# ==========================================================

RETRYABLE = (

    # 网络断 / 超时（超时是它的子类）

    openai.APIConnectionError,

    # 429 限流

    openai.RateLimitError,

    # 5xx 服务端错误

    openai.InternalServerError,

)

# 每次重试前的等待秒数。
# 首发失败 → 等 1 秒 → 再失败 → 等 3 秒 → 最后一次

RETRY_DELAYS = (1, 3)


def _is_retryable(e):

    if isinstance(e, RETRYABLE):

        return True

    # 非 SDK 抛出来的异常
    # 按状态码兜底判断

    code = getattr(e, "status_code", None)

    return code is not None and (

        code == 429 or code >= 500

    )


class LLM:

    def __init__(self):

        # =========================
        # 服务商配置读取顺序：
        # 1. 环境变量（ECHO_API_*，
        #    旧的 DEEPSEEK_* 继续认）
        # 2. 设置页保存的配置文件
        # 3. 出厂默认（DeepSeek）
        # =========================

        cfg = self._load_llm_settings()

        self.api_base = (

            os.environ.get(
                "ECHO_API_BASE"
            )

            or os.environ.get(
                "DEEPSEEK_BASE_URL"
            )

            or cfg.get("api_base")

            or DEFAULT_BASE_URL

        )


        # =========================
        # API Key：
        # 环境变量优先（开发时好覆盖），
        # 其次设置页保存的密文。
        # 旧的 DEEPSEEK_API_KEY 继续认
        # =========================

        api_key = (

            os.environ.get(
                "ECHO_API_KEY"
            )

            or os.environ.get(
                "DEEPSEEK_API_KEY"
            )

            or ""

        ).strip() or None


        if not api_key:

            api_key = (
                self._load_saved_key()
            )


        if not api_key:

            raise RuntimeError(
                "未找到 API Key。\n"
                "请打开设置页填写 API Key，\n"
                "或设置环境变量 ECHO_API_KEY。"
            )


        self.client = OpenAI(

            api_key=api_key,

            base_url=self.api_base,

            timeout=60

        )


        # =========================
        # 三个角色各用哪个模型
        # =========================

        self.models = {}

        for role, default in (
            DEFAULT_MODELS.items()
        ):

            self.models[role] = (

                _env_model(
                    "ECHO_MODEL_"
                    + role.upper(),
                    "",
                )

                or cfg.get(
                    "model_" + role
                )

                or default

            )


        # 模型不可用时只警告一次，
        # 不然每次对话都刷一行
        self._fallback_warned = False


    # =========================
    # 设置页保存的服务商配置
    # （base_url 和三个模型名）
    # =========================

    @staticmethod
    def _load_llm_settings():

        try:

            from core.storage import (
                load_llm_settings,
            )

            return (
                load_llm_settings()
            )

        except Exception:

            return {}


    # =========================
    # 从设置页保存的配置读key
    # （DPAPI 密文，
    # 旧版明文自动迁移）
    # =========================

    @staticmethod
    def _load_saved_key():

        from core.storage import (
            load_api_key
        )

        return load_api_key()


    # =========================
    # 统一的底层调用
    # --------------------------------------------------
    # 所有请求都从这里出去，
    # 模型名、思考开关、降级只在这一处管。
    # =========================

    def _create(
        self,
        messages,
        *,
        role="speak",
        temperature=0.8,
        max_tokens=None,
        response_format=None,
        stream=False
    ):

        if role == "speak":

            model = self.models["speak"]

            # 关思考目前只有 DeepSeek V4 认：
            # thinking 参数走 extra_body
            # （直接写会被 SDK 拒，2026-08-31 实测）。
            # 别家不认识这个参数，
            # 乱发可能直接 400，
            # 所以只对 DeepSeek 发。

            if "deepseek" in (
                self.api_base.lower()
            ):

                extra = {
                    "extra_body": {
                        "thinking": (
                            THINKING_OFF
                        )
                    }
                }

            else:

                extra = {}

        elif role == "reflect":

            model = self.models["reflect"]

            # 不传 thinking 参数：
            # DeepSeek V4 默认开着思考

            extra = {}

            if max_tokens is None:

                max_tokens = MAX_TOKENS_THINK

        else:  # role == "think"

            model = self.models["think"]

            extra = {}

            if max_tokens is None:

                max_tokens = MAX_TOKENS_THINK

        kwargs = {

            "model": model,

            "messages": messages,

            "temperature": temperature,

            "stream": stream,

        }

        if max_tokens is not None:

            kwargs["max_tokens"] = max_tokens

        if response_format is not None:

            kwargs["response_format"] = response_format

        kwargs.update(extra)

        try:

            return self._raw_create(kwargs)

        except Exception as e:

            # =========================
            # 只有"这个模型调不了"才降级。
            # 余额不足、限流、网络断了
            # 都不该换模型 ——
            # 换了也是一样的错，
            # 还把真原因盖住了。
            # =========================

            if not self._model_unavailable(e):

                raise

            # 说话模型就是兜底：
            # 它自己都不行就没处退了

            if model == (
                self.models["speak"]
            ):

                raise

            if not self._fallback_warned:

                self._fallback_warned = True

                log.warning(
                    "模型 %s 不可用，已降级到 %s。"
                    "原始错误：%s",
                    model,
                    self.models["speak"],
                    e,
                )

            kwargs["model"] = (
                self.models["speak"]
            )

            return self._raw_create(kwargs)


    # =========================
    # 真正发起请求
    # --------------------------------------------------
    # 带瞬时错误重试。
    # 模型不可用的降级判断
    # 不在这层做，
    # 原样抛给 _create 处理。
    # =========================

    def _raw_create(self, kwargs):

        for attempt in range(
            len(RETRY_DELAYS) + 1
        ):

            try:

                return (

                    self.client
                    .chat.completions
                    .create(**kwargs)

                )

            except Exception as e:

                if not _is_retryable(e):

                    raise


                if attempt >= len(
                    RETRY_DELAYS
                ):

                    log.warning(
                        "重试 %d 次后仍失败: %s",
                        attempt,
                        e,
                    )

                    raise


                delay = (
                    RETRY_DELAYS[attempt]
                )

                log.warning(
                    "调用瞬时失败"
                    "（第 %d 次），"
                    "%d 秒后重试: %s",
                    attempt + 1,
                    delay,
                    e,
                )

                time.sleep(delay)


    @staticmethod
    def _model_unavailable(e):

        """
        判断这个异常是不是"模型本身调不了"。

        宁可判断保守一点：
        认不出来的异常一律不降级，
        让它照常抛出去。
        """

        code = getattr(e, "status_code", None)

        if code in (400, 401, 403, 404):

            text = str(e).lower()

            for kw in (
                "model",
                "not found",
                "does not exist",
                "unsupported",
                "permission",
                "no access",
                "invalid",
            ):

                if kw in text:

                    return True

        return False


    # =========================
    # 说话（她开口）
    # --------------------------------------------------
    # 对话回复、主动消息、动作文案都走这里。
    # Flash + 关思考 —— 要的是快（实测 0.77 秒）。
    # =========================

    def generate(
        self,
        prompt,
        system=None,
        think=False,
        temperature=0.8
    ):

        response = self._create(

            messages=[

                {
                    "role": "system",
                    "content": (
                        system
                        or "你是一个温柔的AI陪伴助手。"
                    )
                },

                {
                    "role": "user",
                    "content": prompt
                }

            ],

            role="reflect" if think else "speak",

            temperature=temperature

        )

        return response.choices[0].message.content


    # =========================
    # 想（理解端 / 回看端）
    # --------------------------------------------------
    # JSON 模式：强制模型只输出 JSON。
    # 开思考 —— 关了会把苦笑读成开心。
    #
    # reflect=False → 理解端，Flash，阻塞路径
    # reflect=True  → 回看端，Pro，说完之后才跑
    #
    # max_tokens 是硬约束：
    # 思考 token 吃这个额度，
    # 给小了会想不完，
    # 想不完 content 是空的且不报错。
    # =========================

    def generate_json(
        self,
        prompt,
        system,
        max_tokens=MAX_TOKENS_THINK,
        reflect=False
    ):

        response = self._create(

            messages=[

                {
                    "role": "system",
                    "content": system
                },

                {
                    "role": "user",
                    "content": prompt
                }

            ],

            role="reflect" if reflect else "think",

            temperature=0.2,

            max_tokens=max_tokens,

            response_format={
                "type": "json_object"
            }

        )

        content = (
            response.choices[0]
            .message.content
        )

        # 想完了但没说出话来，
        # 多半是思考把额度吃光了。
        # 记一笔，调用方按自己的默认值兜。
        if not (content or "").strip():

            log.warning(
                "JSON 端返回空内容（role=%s），"
                "可能是 max_tokens=%s 不够想完。",
                "reflect" if reflect else "think",
                max_tokens
            )

        return content


    # =========================
    # 流式生成：逐段产出，
    # 不用等整段写完
    # --------------------------------------------------
    # 只取 delta.content。
    # V4 的思考走的是 delta.reasoning_content，
    # 另一个字段，不会串进对话里 ——
    # 2026-08-31 流式实测确认过。
    # 而且这里本来就关了思考。
    # =========================

    def generate_stream(
        self,
        prompt,
        system=None,
        temperature=0.8
    ):

        stream = self._create(

            messages=[

                {
                    "role": "system",
                    "content": (
                        system
                        or "你是一个温柔的AI陪伴助手。"
                    )
                },

                {
                    "role": "user",
                    "content": prompt
                }

            ],

            role="speak",

            temperature=temperature,

            stream=True

        )

        for chunk in stream:

            if not chunk.choices:

                continue

            delta = (
                chunk.choices[0]
                .delta.content
            )

            if delta:

                yield delta
