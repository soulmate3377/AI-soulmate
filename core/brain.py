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
from core.identity import Identity as SoulmateIdentity
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


        # Personality system
        # 人格系统

        self.personality = Personality()


        # Shared personality state: reflection, growth and evolution are reading and writing the same one
        # 共享人格状态：反思、成长、人格演进读写同一份

        self.personality_state = PersonalityState()


        # Personality evolution
        # 人格演进系统

        self.personality_evolver = PersonalityEvolver(
            self.personality_state
        )


        # How she is today: not just tone, but whether she feels like talking at all. See core/inclination.py
        # 她今天的状态：不只是语气，还包括她今天想不想说话（详见 core/inclination.py）

        self.inclination = Inclination()



        # LLM API, built early because emotion and memory analysis both need it
        # 大模型接口：提前创建，情绪分析和记忆分析都需要它

        self.llm = LLM()


        # Emotion system
        # 情绪系统

        self.emotion = EmotionAnalyzer(
            self.llm
        )



        # Memory system
        # 记忆系统

        self.memory = LongMemory()


        self.memory_retriever = MemoryRetriever()


        self.memory_pipeline = MemoryPipeline(
            self.llm
        )


        # Perception layer: one call produces every judgement, falling back to the rule analyzers above when it fails
        # 理解端（感知层）：一次调用产出全部判断，失败时回退到上面的规则分析组件

        self.perception = Perception(
            self.llm
        )



        # User identity system
        # 用户身份系统

        self.identity = UserIdentity()


        # Echo's own profile: hometown / current city / occupation
        # Echo 自己的身份资料：家乡/现居地/职业

        self.echo_identity = SoulmateIdentity()


        # What she is doing right now
        # 她此刻在做的事

        self.activity = ActivityEngine()



        # Relationship system
        # 关系系统

        self.relationship = Relationship()



        # Current state
        # 当前状态系统

        self.state = StateMemory()


        # Decision system
        # 决策系统

        self.decision = DecisionEngine()



        # Prompt system: must exist before the scheduler, which references it while initialising
        # Prompt 系统：必须在调度系统之前创建，调度器初始化时要引用它

        self.prompt_builder = PromptBuilder()


        # Action system
        # 行动系统

        self.action = ActionExecutor(

            self.llm

        )
        # Proactive scheduler
        # 主动调度系统

        self.scheduler = Scheduler(

            self

        )
        # Reflection, the third of the three APIs: understand -> reply -> reflect -> shape the next turn. Pass llm in or it is an empty shell
        # 回看系统：三个 API 里的第三个（理解 -> 输出 -> 回看 -> 影响下一轮）；传 llm 进去它才真的会想，不传就是个空壳

        self.reflection = SelfReflection(
            self.llm
        )

        # Where the last line went wrong, kept for the next one to patch up
        # 上一句哪里说错了，留给下一句找补

        self._reflection_note = None



        # Full prompt from the last turn, reused verbatim on regenerate. It was assembled the moment his message arrived (that moment's memory, relationship, understanding), so reusing it keeps the side effects -- relationship counters, memory writes -- from running twice
        # 上一轮拼好的完整 prompt：重新生成时原样复用。它是在收到他那句话那一刻拼的（当时的记忆、关系、理解），重用才不会把关系计数、记忆入库这些副作用再跑一遍

        self._last_prompt_msg = None

        self._last_prompt = None



        # Growth system
        # 成长系统

        self.growth = GrowthSystem(
            self.personality_state
        )



        # Daily auto backup. Memory and chat logs exist only in the data dir, so zip the whole thing at startup when it is due. A failed backup only logs, never stops her from coming up
        # 每日自动备份：记忆和聊天记录只有数据目录这一份，启动时到点就整个 zip 一份；备份失败只记日志，绝不拦着她起来

        try:

            run_if_due()

        except Exception:

            import logging

            logging.getLogger(
                "echo.brain"
            ).exception(
                "备份失败（已跳过）"
            )






    # Assemble the full context for this turn
    # 拼装本轮对话的完整上下文

    def _prepare_prompt(self, user_message):



        # Update relationship
        # 更新关系

        self.relationship.interact()



        # Retrieve related memory
        # 检索相关记忆

        related_memory = self.memory_retriever.retrieve(

            user_message

        )




        # User profile
        # 用户资料

        user_profile = (

            self.memory.get_profile()

        )



        # Experience memory
        # 经历记忆

        experience_memory = (

            self.memory.get_experiences()

        )



        # User identity model
        # 用户身份模型

        user_identity = (

            self.identity.get()

        )



        # The last few exchanges. She has to see what she just said, or she keeps raising the same thing and circles one topic
        # 刚才聊的几句：她得看得见自己刚说过什么，才不会反复提同一件事、在一个话题里打转

        recent_dialogue = []

        try:

            recent = (

                ConversationManager()
                .get_recent(9)

            )

            # This message is already on disk, drop it so it does not show up twice in "the last few exchanges"
            # 当前这条消息已落盘，别在“刚才的对话”里又重复出现一次

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



        # Perception layer: one call yields emotion / scene / reply length / memory ops. On failure fall back to the rule components so the chat never stops
        # 理解端（感知层）：一次调用产出情绪/场景/回复长短/记忆操作；失败回退到规则组件，聊天永不中断

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

            # Same-day mood drift: he is cheerful, she comes alive; he is down, keeping company drains her. It runs before current() reads the file so this turn's prompt already sees the drifted state. Blowing up is harmless to the chat
            # 当天兴致漂移：他开心/笑成一串，她也跟着活；他难过，陪人是耗电的。放在 current() 读档之前，本轮提示词就能用上漂移后的状态。挂了不影响对话

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

            # Fallback path: the old memory / emotion analyzers
            # 回退路径：旧的记忆/情绪分析组件

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


        # Update current state
        # 更新当前状态

        self.state.update(

            user_message,

            emotion_result

        )



        # User name. The profile keeps it under the basic group; fall back to the default when it is missing
        # 用户名字：画像里名字在 basic 分组下，取不到就用默认称呼
        user_name = (
            user_profile.get(
                "basic", {}
            ).get(
                "name"
            )
        )



        if not user_name:


            user_name = "朋友"





        # Relationship status in plain language: stage + trust + the milestones between them
        # 关系状态（自然语言描述）：阶段 + 信任程度 + 你们之间的里程碑

        relationship_status = (

            self.relationship.describe()

        )





        # Echo's personality
        # Echo 人格

        personality_info = (

            self.personality.introduce()

        )





        # Echo's own life: hometown / city / identity / what she is doing now / weather outside
        # Echo 自己的生活：家乡/现居地/身份/此刻在做的事/窗外天气

        echo_context = (
            self._echo_context()
        )


        # Long or short this time -- she reads it off his message
        # 这次回复该长还是该短，由她根据对方的话把握

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


        # What he is reacting to. A bare "hahaha" carries nothing on its own and perception already hung it on the previous line; passing that to the output keeps her from answering "laughing at what"
        # 他在回应什么：「哈哈哈哈」这类自己不带内容，理解端已经把它挂回上一句了；拿过来给输出用，她才不会回一句「笑啥呢」

        reacts_to = None

        if understanding is not None:

            reacts_to = understanding.get(
                "reacts_to"
            )


        # Where the last line went wrong. Taken and cleared in one go -- leave it set and she keeps apologising
        # 上一句说错了的地方：取走就清空，不清她会一直道歉

        reflection_note = (
            self._reflection_note
        )

        self._reflection_note = None


        # Build prompt
        # 构建 Prompt

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





        # Context assembled
        # 上下文拼装完成

        return prompt


    # Echo's life state right now
    # Echo 此刻的生活状态

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

            # Cached for an hour; on failure it returns None and the chat goes on
            # 有一小时缓存，失败返回 None 不影响聊天

            weather = get_weather(city)


        return {
            "hometown": hometown,
            "current_city": city,
            "occupation": occupation,
            "activity": activity,
            "next_activity": next_activity,
            "weather": weather,
        }


    # Apply what perception concluded: memory writes / relationship events / follow-ups. Every step has its own try, one failure does not take the others down
    # 执行理解端结论：记忆写入 / 关系事件登记 / 话茬登记；每一步独立容错，单个失败不影响其余

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


        # Loose memory intake. The model no longer judges whether something is "worth remembering": most user messages are small talk, that judgement threw them all away and a promise disappeared with them. Now a light noise filter lets everything into storage and relevance is ranked at retrieval time
        # 记忆宽进：不再让模型判断“值不值得记”。用户的消息大多是闲聊，一判断就全被丢掉，重要的约定这种转眼就没了；现在轻噪过滤后全量入库，相关性交给检索时排序

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


        # Relationship event: hand it to the relationship system to push the dimensions and log milestones
        # 关系事件：交给关系系统推进维度、记里程碑

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


        # Follow-up log, consumed later by the proactive phase
        # 话茬登记（主动消息阶段消费）

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

                # When the thing happens: carried along when perception can work it out, the scheduler uses it to tell expired from fresh
                # 那件事的发生时间：感知端推得出就带着，调度器按它判断过没过期

                due = understanding.get(
                    "follow_up_due"
                )

                # De-dupe: two mentions of "interview" inside three days should not pile up two follow-ups. When the text is too close to one still unasked, refresh the old entry instead of registering a new one
                # 去重：三天里提两次“面试”，不该攒出两条话茬。跟没问过的话茬太像时，刷新旧条目的时间，而不是新登记一条

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


    # Perception scene -> reply length
    # 理解端的场景 → 回复长短

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


    # Reply length hint, used by the fallback path: fire back quickly at a short message, stay longer for an outpouring or heavy emotion
    # 回复长短提示（回退路径用）：短消息随手回，长倾诉/重情绪多陪几句

    @staticmethod
    def _reply_length_hint(
        message,
        emotion
    ):


        text = message.strip()


        # Emotion intensity. The shape is not guaranteed, so treat anything missing as normal
        # 情绪强度（结构不确定，取不到就按普通处理）

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


    # Wrap-up after a reply: store the facts she stated about herself + reflection + personality growth
    # 回复后的收尾：她说过的关于自己的事实落库 + 反思 + 人格成长

    def _post_process(
        self,
        user_message,
        response
    ):


        # "Where I study", "where I live" -- whatever she says about herself in a reply has to be remembered, or a different wording next time turns into a fabrication
        # 她在回复里说的"我在哪读书""我住哪"必须记住，否则下次换一套说法就成了编造

        try:

            self.memory_pipeline.process_reply(
                response
            )

        except Exception as e:

            print(
                "Echo 自述入库失败（跳过）:",
                e
            )


        # Reflection: did she make that last line up? It runs after the reply while the user is already reading, so a bit of slowness goes unnoticed. The dialogue is fetched here only so recent_dialogue does not have to be threaded through every call site
        # 回看：她刚这句有没有编。发生在回复之后，用户已经在看了，这里慢一点没人感觉到；对话在这里自己取一次，不想为了它把 recent_dialogue 一路传到每个调用点

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


        # Saved for her next line: patch up what went wrong in the last one, the way people actually talk
        # 留给她下一句：上一句哪里说错了，自然找补一句。人也是这么聊的

        self._reflection_note = (
            reflection_result.get("note")
        )


        self.growth.apply(

            reflection_result

        )


    # Wrap-up after a proactive message goes out: store the facts she stated + reflect. Opening with nobody handing her a line is the easiest channel for her to invent things, so it needs the same reflection a normal reply gets. Called by the UI on a background thread
    # 主动消息发出后的收尾：她自述的事实落库 + 回看。主动开口没有人递话，是最容易被她编出事的通道，普通回复有的回看，这里一样要有；由界面在后台线程里调用

    def reflect_proactive(
        self, message, follow_ups=None
    ):


        # "I'm at the library", "just got out of class" -- what she says in a proactive message goes into storage too, or a rephrasing next time turns into a fabrication
        # 她在主动消息里说的"我在图书馆""刚下课"同样要入库，不然下次换套说法就成了编造

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


        # The note waits for her "next line", i.e. when he answers this proactive message. If an old note was never taken, the newer mistake matters more and overwrites it
        # 便签留到她"下一句"——他回这条主动消息的时候；若旧便签还没被取走，新的错更要紧，覆盖掉

        note = reflection_result.get("note")

        if note:

            self._reflection_note = note


        self.growth.apply(
            reflection_result
        )


    # User-driven chat mode, one shot
    # 用户主动聊天模式（一次性返回）

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


    # Streaming chat mode: yields piece by piece so the UI shows it live
    # 流式聊天模式：逐段产出，界面即时显示

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



    # Prompt for this turn. Normal message: build and cache it now. Regenerate: reuse the cached prompt verbatim -- he said the same thing, so the world she should see is still that moment's, and re-running _prepare_prompt would count the relationship interaction and store the user message again, giving one line the weight of two turns. On a mismatch (different message, no cache) build it fresh: better to double-count once than to let her talk to a context that does not exist
    # 取本轮 prompt。正常消息：现拼并缓存；重新生成：上一轮缓存的 prompt 原样复用——他还是那句话，她该看见的世界还是那一刻的，重跑 _prepare_prompt 会把关系互动计数、用户消息入库再计一遍，等于一句话聊出了两轮的存在感。对不上号（消息不一致、没有缓存）就老老实实现拼，宁可多计一次，不能让她对着不存在的上下文说话

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








    # Echo's proactive thinking mode
    # Echo 主动思考模式

    def proactive_think(self):



        # Current state
        # 当前状态

        state = self.state.get()



        # Relationship
        # 关系

        relationship = (

            self.relationship.get_status()

        )



        # Experience memory
        # 经历记忆

        memories = (

            self.memory.get_experiences()

        )



        # User identity
        # 用户身份

        identity = (

            self.identity.get()

        )

        personality_state = (
          self.personality_evolver.evolve(
        identity
          )
        )



        # Decision
        # 决策

        decision = self.decision.decide(


            state,


            relationship,


            memories


        )



        # Execute the action
        # 执行动作

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