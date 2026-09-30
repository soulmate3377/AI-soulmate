import json

from datetime import datetime

from memory.long_memory import LongMemory
from memory.memory_retriever import MemoryRetriever
from memory.memory_pipeline import MemoryPipeline
from memory.relationship import Relationship
from memory.state import StateMemory
from memory.user_identity import UserIdentity
from memory.conversation import ConversationManager

from core.personality_evolver import PersonalityEvolver
from core.personality_state import PersonalityState
from core.personality import Personality
from core.emotion import EmotionAnalyzer
from core.decision import DecisionEngine
from core.action import ActionExecutor
from core.self_reflection import SelfReflection
from core.growth import GrowthSystem
from core.inclination import Inclination
from core.scheduler import Scheduler
from core.activity import ActivityEngine
from core.weather import get_weather
from core.identity import Identity as EchoLoverIdentity
from core.perception import Perception
from core.proactive_guard import (
    followup_same,
)
from core.paths import data_dir
from core import storage
from core.backup import run_if_due
from llm.api import LLM
from prompt.builder import PromptBuilder





class Brain:



    def __init__(self):


        # =========================
        # 人格系统
        # =========================

        self.personality = Personality()


        # =========================
        # 共享人格状态
        # 反思、成长、人格演进
        # 读写同一份状态
        # =========================

        self.personality_state = PersonalityState()


        # =========================
        # 人格演进系统
        # =========================

        self.personality_evolver = PersonalityEvolver(
            self.personality_state
        )


        # =========================
        # 她今天的状态
        #
        # 不只是语气，还包括
        # 她今天想不想说话。
        # 详见 core/inclination.py
        # =========================

        self.inclination = Inclination()



        # =========================
        # 大模型接口
        # 提前创建，情绪分析和
        # 记忆分析都需要它
        # =========================

        self.llm = LLM()


        # =========================
        # 情绪系统
        # =========================

        self.emotion = EmotionAnalyzer(
            self.llm
        )



        # =========================
        # 记忆系统
        # =========================

        self.memory = LongMemory()


        self.memory_retriever = MemoryRetriever()


        self.memory_pipeline = MemoryPipeline(
            self.llm
        )


        # =========================
        # 理解端（感知层）：
        # 一次调用产出全部判断，
        # 失败时回退到上面的
        # 规则分析组件
        # =========================

        self.perception = Perception(
            self.llm
        )



        # =========================
        # 用户身份系统
        # =========================

        self.identity = UserIdentity()


        # =========================
        # Echo 自己的身份资料
        # 家乡/现居地/职业
        # =========================

        self.echo_identity = EchoLoverIdentity()


        # =========================
        # 她此刻在做的事
        # =========================

        self.activity = ActivityEngine()



        # =========================
        # 关系系统
        # =========================

        self.relationship = Relationship()



        # =========================
        # 当前状态系统
        # =========================

        self.state = StateMemory()


        # =========================
        # 决策系统
        # =========================

        self.decision = DecisionEngine()



        # =========================
        # Prompt系统
        # 必须在调度系统之前创建，
        # 调度器初始化时要引用它
        # =========================

        self.prompt_builder = PromptBuilder()


        # =========================
        # 行动系统
        # =========================

        self.action = ActionExecutor(

            self.llm

        )
        # =========================
        # 主动调度系统
        # =========================

        self.scheduler = Scheduler(

            self

        )
        # =========================
        # 回看系统
        #
        # 三个 API 里的第三个：
        # 理解 -> 输出 -> 回看 -> 影响下一轮。
        # 传 llm 进去它才真的会想，
        # 不传就是个空壳。
        # =========================

        self.reflection = SelfReflection(
            self.llm
        )

        # 上一句哪里说错了，
        # 留给下一句找补

        self._reflection_note = None



        # =========================
        # 上一轮拼好的完整 prompt
        #
        # 重新生成时复用：
        # prompt 是在收到他那句话的
        # 那一刻拼的（当时的记忆、
        # 关系、理解），原样重用
        # 才不会把关系计数、
        # 记忆入库这些副作用
        # 再跑一遍。
        # =========================

        self._last_prompt_msg = None

        self._last_prompt = None



         # =========================
         # 成长系统
         # =========================

        self.growth = GrowthSystem(
            self.personality_state
        )



        # =========================
        # 每日自动备份
        #
        # 记忆和聊天记录只有
        # 数据目录这一份，
        # 启动时到点就整个 zip 一份。
        # 备份失败只记日志，
        # 绝不拦着她起来。
        # =========================

        try:

            run_if_due()

        except Exception:

            import logging

            logging.getLogger(
                "echo.brain"
            ).exception(
                "备份失败（已跳过）"
            )






    # ==================================================
    # 拼装本轮对话的完整上下文
    # ==================================================

    def _prepare_prompt(self, user_message):



        # =========================
        # 更新关系
        # =========================

        self.relationship.interact()



        # =========================
        # 检索相关记忆
        # =========================

        related_memory = self.memory_retriever.retrieve(

            user_message

        )




        # =========================
        # 用户资料
        # =========================

        user_profile = (

            self.memory.get_profile()

        )



        # =========================
        # 经历记忆
        # =========================

        experience_memory = (

            self.memory.get_experiences()

        )



        # =========================
        # 用户身份模型
        # =========================

        user_identity = (

            self.identity.get()

        )



        # =========================
        # 刚才聊的几句：
        # 她得看得见自己刚说过什么，
        # 才不会反复提同一件事、
        # 在一个话题里打转
        # =========================

        recent_dialogue = []

        try:

            recent = (

                ConversationManager()
                .get_recent(9)

            )

            # 当前这条消息已落盘，
            # 别在“刚才的对话”里
            # 又重复出现一次

            if (

                recent

                and recent[-1].get("role")
                    == "user"

                and recent[-1].get("content")
                    == user_message

            ):

                recent = recent[:-1]

            recent_dialogue = recent[-8:]

        except Exception:

            recent_dialogue = []



        # =========================
        # 理解端（感知层）：
        # 一次调用产出情绪/场景/
        # 回复长短/记忆操作。
        # 失败回退到规则组件，
        # 聊天永不中断
        # =========================

        understanding = None

        try:

            profile_summary = json.dumps(

                user_profile,
                ensure_ascii=False

            )[:500]

            understanding = (
                self.perception.understand(

                    user_message,
                    recent_dialogue,
                    profile_summary

                )
            )

        except Exception as e:

            print(
                "理解端失败，"
                "回退规则分析:",
                e
            )


        if understanding is not None:

            emotion_result = {
                "emotion":
                    understanding["emotion"],
                "intensity":
                    understanding["intensity"],
                "need":
                    understanding["need"],
            }

            self._apply_understanding(
                understanding,
                user_message
            )

            # =========================
            # 当天兴致漂移：
            # 他开心/笑成一串，她也跟着活；
            # 他难过，陪人是耗电的。
            # 放在 current() 读档之前，
            # 本轮提示词就能用上
            # 漂移后的状态。
            # 挂了不影响对话。
            # =========================

            try:

                self.inclination.notify_exchange(

                    understanding.get("emotion"),

                    understanding.get(
                        "intensity", 0
                    ),

                    user_message,

                )

            except Exception:

                pass

        else:

            # 回退路径：
            # 旧的记忆/情绪分析组件

            try:

                self.memory_pipeline.process(
                    user_message
                )

            except Exception as e2:

                print(
                    "记忆分析失败（已跳过）:",
                    e2
                )

            emotion_result = (
                self.emotion.analyze(
                    user_message
                )
            )


        # =========================
        # 更新当前状态
        # =========================

        self.state.update(

            user_message,

            emotion_result

        )



        # =========================
        # 用户名字
        # 画像里名字在 basic 分组下，
        # 取不到就用默认称呼
        # =========================
        user_name = (
            user_profile.get(
                "basic", {}
            ).get(
                "name"
            )
        )



        if not user_name:


            user_name = "朋友"





        # =========================
        # 关系状态
        # 自然语言描述：
        # 阶段 + 信任程度 +
        # 你们之间的里程碑
        # =========================

        relationship_status = (

            self.relationship.describe()

        )





        # =========================
        # Echo人格
        # =========================

        personality_info = (

            self.personality.introduce()

        )





        # =========================
        # Echo 自己的生活：
        # 家乡/现居地/身份/
        # 此刻在做的事/窗外天气
        # =========================

        echo_context = (
            self._echo_context()
        )


        # =========================
        # 这次回复该长还是该短，
        # 由她根据对方的话把握
        # =========================

        if understanding is not None:

            reply_length = (
                self._reply_length_from_scene(
                    understanding
                )
            )

        else:

            reply_length = (
                self._reply_length_hint(
                    user_message,
                    emotion_result
                )
            )


        # =========================
        # 他在回应什么
        #
        # 「哈哈哈哈」这类自己不带内容，
        # 理解端已经把它挂回上一句了。
        # 拿过来给输出用，
        # 她才不会回一句「笑啥呢」。

        reacts_to = None

        if understanding is not None:

            reacts_to = understanding.get(
                "reacts_to"
            )


        # =========================
        # 上一句说错了的地方。
        #
        # 取走就清空：
        # 不清她会一直道歉。

        reflection_note = (
            self._reflection_note
        )

        self._reflection_note = None


        # =========================
        # 构建Prompt
        # =========================

        prompt = self.prompt_builder.build(


            personality_info,


            user_name,


            relationship_status,


            emotion_result,


            user_message,

            related_memory,


            user_profile,


            experience_memory,


            user_identity,


            self.inclination.current(),


            echo_context=echo_context,


            reply_length=reply_length,


            recent_dialogue=recent_dialogue,

            reacts_to=reacts_to,

            reflection_note=reflection_note


        )





        # =========================
        # 上下文拼装完成
        # =========================

        return prompt


    # ==================================================
    # Echo 此刻的生活状态
    # ==================================================

    def _echo_context(self):


        hometown = self.echo_identity.get(
            "hometown"
        )

        city = self.echo_identity.get(
            "current_city"
        )

        occupation = self.echo_identity.get(
            "occupation"
        )


        activity = None

        next_activity = None

        if occupation:

            activity = self.activity.current(
                occupation
            )

            next_activity = self.activity.later(
                occupation
            )


        weather = None

        if city:

            # 有一小时缓存，
            # 失败返回 None 不影响聊天

            weather = get_weather(city)


        return {
            "hometown": hometown,
            "current_city": city,
            "occupation": occupation,
            "activity": activity,
            "next_activity": next_activity,
            "weather": weather,
        }


    # ==================================================
    # 执行理解端结论：
    # 记忆写入 / 关系事件登记 /
    # 话茬登记。
    # 每一步独立容错，
    # 单个失败不影响其余
    # ==================================================

    def _apply_understanding(
        self, understanding, message
    ):

        ops = understanding.get(
            "memory_ops"
        ) or []


        for op in ops:

            try:

                action = op["action"]

                if action == "update_profile":

                    self.memory.update_profile(
                        op["category"],
                        op["key"],
                        op["value"]
                    )

                elif action == "add_profile_item":

                    self.memory.add_profile_item(
                        op["category"],
                        op["key"],
                        op["value"]
                    )

                else:

                    self.memory.add_experience({

                        "type": "event",

                        "content": op["value"],

                        "time": datetime.now()
                        .strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),

                    })

            except Exception as e:

                print(
                    "记忆操作失败（跳过）:",
                    e
                )


        # =========================
        # 记忆宽进：
        # 不再让模型判断"值不值得记"。
        # 用户的消息大多是闲聊，
        # 一判断就全被丢掉，
        # 重要的约定这种转眼就没了。
        # 现在轻噪过滤后全量入库，
        # 相关性交给检索时排序。
        # =========================

        try:

            self.memory_pipeline.process(
                message, role="user"
            )

        except Exception as e:

            print(
                "记忆入库失败（跳过）:",
                e
            )


        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )


        # 关系事件：
        # 交给关系系统推进维度、
        # 记里程碑

        rel_event = understanding.get(
            "relationship_event"
        )

        if rel_event:

            try:

                self.relationship.record_event(
                    rel_event, message
                )

            except Exception as e:

                print(
                    "关系事件登记失败:",
                    e
                )


        # 话茬登记
        # （主动消息阶段消费）

        follow_up = understanding.get(
            "follow_up"
        )

        if follow_up:

            try:

                path = (

                    data_dir()
                    / "memory"
                    / "followups.json"

                )

                items = (
                    storage.read_json(
                        path, []
                    ) or []
                )

                # 那件事的发生时间，
                # 感知端推得出就带着，
                # 调度器按它判断过没过期

                due = understanding.get(
                    "follow_up_due"
                )

                # 去重：
                # 三天里提两次"面试"，
                # 不该攒出两条话茬。
                # 跟没问过的话茬太像时，
                # 刷新旧条目的时间，
                # 而不是新登记一条

                merged = False

                for old in items:

                    if old.get("consumed"):

                        continue

                    if followup_same(

                        old.get("text") or "",
                        follow_up

                    ):

                        old["text"] = follow_up

                        old["time"] = now

                        if due:

                            old["due"] = due

                        merged = True

                        break

                if not merged:

                    item = {
                        "text": follow_up,
                        "time": now,
                    }

                    if due:

                        item["due"] = due

                    items.append(item)

                storage.write_json(
                    path, items[-50:]
                )

            except Exception as e:

                print(
                    "话茬登记失败:",
                    e
                )


    # ==================================================
    # 理解端的场景 → 回复长短
    # ==================================================

    @staticmethod
    def _reply_length_from_scene(
        understanding
    ):

        mapping = {

            "短":
                "对方只是随手一句。"
                "你也回短一点，"
                "一两个字或一句话都可以。",

            "正常":
                "正常闲聊，一两句话就好。",

            "多陪几句":
                "对方在倾诉、求助，"
                "或情绪很重。"
                "这次可以多聊几句、"
                "多陪一会儿，"
                "但每条消息仍然要短。",

        }

        return mapping.get(

            understanding["reply_length"],

            mapping["正常"]

        )


    # ==================================================
    # 回复长短提示（回退路径用）：
    # 短消息随手回，
    # 长倾诉/重情绪多陪几句
    # ==================================================

    @staticmethod
    def _reply_length_hint(
        message,
        emotion
    ):


        text = message.strip()


        # 情绪强度（结构不确定，
        # 取不到就按普通处理）

        strong = False

        if isinstance(emotion, dict):

            intensity = emotion.get(
                "intensity"
            )

            try:

                strong = (
                    intensity is not None
                    and float(intensity) >= 0.7
                )

            except (TypeError, ValueError):

                strong = False


        if len(text) <= 10 and not strong:

            return (
                "对方只发了短短一句。"
                "你也回短一点，一两句以内，"
                "像随手回消息。"
            )


        if len(text) > 80 or strong:

            return (
                "对方说了很多，或者情绪很重。"
                "这次可以多聊几句、多陪一会儿，"
                "但每条消息仍然要短。"
            )


        return "正常闲聊，一两句话就好。"


    # ==================================================
    # 回复后的收尾：
    # 她说过的关于自己的事实落库 + 反思 + 人格成长
    # ==================================================

    def _post_process(
        self,
        user_message,
        response
    ):


        # 她在回复里说的"我在哪读书""我住哪"
        # 必须记住，
        # 否则下次换一套说法就成了编造

        try:

            self.memory_pipeline.process_reply(
                response
            )

        except Exception as e:

            print(
                "Echo 自述入库失败（跳过）:",
                e
            )


        # 回看：她刚这句有没有编。
        # 发生在回复之后，用户已经在看了，
        # 这里慢一点没人感觉到。
        #
        # 对话在这里自己取一次：
        # 不想为了它把 recent_dialogue
        # 一路传到每个调用点。

        try:

            recent = (
                ConversationManager()
                .get_recent(8)
            )

        except Exception:

            recent = []


        reflection_result = (
            self.reflection.analyze(

                user_message,

                response,

                recent_dialogue=recent,

            )
        )


        # 留给她下一句：
        # 上一句哪里说错了，自然找补一句。
        # 人也是这么聊的。

        self._reflection_note = (
            reflection_result.get("note")
        )


        self.growth.apply(

            reflection_result

        )


    # ==================================================
    # 主动消息发出后的收尾：
    # 她自述的事实落库 + 回看
    #
    # 主动开口没有人递话，
    # 是最容易被她编出事的通道，
    # 普通回复有的回看，
    # 这里一样要有。
    # 由界面在后台线程里调用。
    # ==================================================

    def reflect_proactive(
        self, message, follow_ups=None
    ):


        # 她在主动消息里说的
        # "我在图书馆""刚下课"
        # 同样要入库，
        # 不然下次换套说法就成了编造

        try:

            self.memory_pipeline.process_reply(
                message
            )

        except Exception as e:

            print(
                "主动消息自述入库失败（跳过）:",
                e
            )


        try:

            recent = (
                ConversationManager()
                .get_recent(8)
            )

        except Exception:

            recent = []


        try:

            reflection_result = (
                self.reflection.analyze_proactive(

                    message,

                    recent_dialogue=recent,

                    follow_ups=follow_ups,

                )
            )

        except Exception:

            return


        # 便签留到她"下一句"——
        # 他回这条主动消息的时候。
        # 若旧便签还没被取走，
        # 新的错更要紧，覆盖掉

        note = reflection_result.get("note")

        if note:

            self._reflection_note = note


        self.growth.apply(
            reflection_result
        )


    # ==================================================
    # 用户主动聊天模式（一次性返回）
    # ==================================================

    def think(self, user_message):


        prompt = self._prompt_for(
            user_message
        )


        response = self.llm.generate(
            prompt
        )


        self._post_process(
            user_message,
            response
        )


        return response


    # ==================================================
    # 流式聊天模式：
    # 逐段产出，界面即时显示
    # ==================================================

    def think_stream(self, user_message, regenerate=False):


        prompt = self._prompt_for(
            user_message,

            regenerate=regenerate,

        )


        parts = []

        for delta in self.llm.generate_stream(
            prompt
        ):

            parts.append(delta)

            yield delta


        self._post_process(

            user_message,

            "".join(parts)

        )



    # ==================================================
    # 取本轮 prompt
    #
    # 正常消息：现拼，并缓存。
    # 重新生成：上一轮缓存的 prompt
    #   原样复用 —— 他还是那句话，
    #   她该看见的世界还是那一刻的。
    #   重跑 _prepare_prompt 会把
    #   关系互动计数、用户消息的记忆
    #   入库再计一遍，等于一句话
    #   聊出了两轮的存在感。
    #
    # 对不上号（消息不一致、没有缓存）
    # 就老老实实现拼——宁可多计一次，
    # 不能让她对着不存在的上下文说话。
    # ==================================================

    def _prompt_for(
        self,
        user_message,
        regenerate=False
    ):


        if (

            regenerate

            and self._last_prompt_msg
                == user_message

            and self._last_prompt
                is not None

        ):

            return self._last_prompt


        prompt = (
            self._prepare_prompt(
                user_message
            )
        )


        self._last_prompt_msg = (
            user_message
        )

        self._last_prompt = prompt


        return prompt








    # ==================================================
    # Echo主动思考模式
    # ==================================================

    def proactive_think(self):



        # 当前状态

        state = self.state.get()



        # 关系

        relationship = (

            self.relationship.get_status()

        )



        # 经历记忆

        memories = (

            self.memory.get_experiences()

        )



        # 用户身份

        identity = (

            self.identity.get()

        )

        personality_state = (
          self.personality_evolver.evolve(
        identity
          )
        )



        # =========================
        # 决策
        # =========================

        decision = self.decision.decide(


            state,


            relationship,


            memories


        )



        # =========================
        # 执行动作
        # =========================

        result = self.action.execute(


            decision,


            {


                "state":state,


                "relationship":relationship,


                "memories":memories,


                "identity":identity


            }

        )



        return result