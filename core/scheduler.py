from datetime import datetime

from core import storage

from core.intention import IntentionSystem

from core.interruption import InterruptionControl

from core.proactive import ProactiveConversation

from core.proactive_guard import _terms





class Scheduler:



    def __init__(

        self,

        brain

    ):


        self.brain = brain



        # =========================
        # 主动意图系统
        # =========================

        self.intention = IntentionSystem()



        # =========================
        # 打扰控制
        # =========================

        self.interruption = InterruptionControl()



        # =========================
        # 主动对话生成
        # =========================

        self.proactive = ProactiveConversation(

            self.brain.llm,

            self.brain.prompt_builder

        )


    # ==================================================
    # 话茬：理解端记下的
    # "对方近期的安排/悬念"。
    #
    # 新旧判断分两种：
    #   - 那件事有明确时间（due）：
    #     按事件算 —— 事过了三天内
    #     都来得及问"怎么样"，
    #     事还没到的也留着
    #   - 没有时间：退回按提及时间
    #     1~48 小时
    # ==================================================

    def _followups_file(self):

        return (

            storage.data_dir()

            / "memory"
            / "followups.json"

        )


    @staticmethod
    def _due_of(item):

        text = item.get("due") or ""

        if not text:

            return None

        try:

            return datetime.strptime(

                text,
                "%Y-%m-%d %H:%M:%S"

            )

        except (TypeError, ValueError):

            return None


    def _load_follow_ups(self):

        items = storage.read_json(

            self._followups_file(), []

        ) or []

        now = datetime.now()

        fresh = []

        for item in items:

            if item.get("consumed"):

                continue

            try:

                t = datetime.strptime(

                    item.get("time", ""),

                    "%Y-%m-%d %H:%M:%S"

                )

            except ValueError:

                continue

            age_hours = (

                now - t

            ).total_seconds() / 3600


            # 刚说完就问像复读，
            # 有没有事件时间都一样

            if age_hours < 1:

                continue


            due = self._due_of(item)

            if due is not None:

                # 事已经过去三天以上，
                # 再问就假了

                overdue_hours = (

                    now - due

                ).total_seconds() / 3600

                if overdue_hours > 72:

                    continue

                # 事刚过（24小时内）：
                # 这是最该问的时刻，
                # 打个标记让意图提优先级

                if 0 <= overdue_hours <= 24:

                    item["_due_hit"] = True

                fresh.append(item)

                continue


            # 没有事件时间：
            # 太旧的过时

            if age_hours <= 48:

                fresh.append(item)


        return fresh[-3:]


    @staticmethod
    def used_follow_ups(
        message, follow_ups
    ):

        """
        生成的那句话实际问了哪几条话茬。

        判定：话茬里任意一个 2 字切片
        出现在消息里 —— 和守门人
        核对"你说过…"用的是同一把尺。

        一句话通常只问一件事，
        没被问到的话茬必须留下来，
        下次再问。
        """

        if not message or not follow_ups:

            return []

        used = []

        for item in follow_ups:

            pieces = _terms(

                item.get("text") or "", 2

            )

            if pieces and any(

                p in message
                for p in pieces

            ):

                used.append(item)

        return used


    def mark_follow_ups_asked(self, used):

        """
        主动消息真的发出去之后
        才调用。
        中途被守门人丢掉的
        不算问过。
        """

        self._consume_follow_ups(used)


    def _consume_follow_ups(self, used):

        if not used:

            return

        texts = {
            i.get("text") for i in used
        }

        items = storage.read_json(

            self._followups_file(), []

        ) or []

        for item in items:

            if item.get("text") in texts:

                item["consumed"] = True

        storage.write_json(

            self._followups_file(), items

        )





    # ==================================================
    # 单次主动检查
    # ==================================================

    def run_once(self, avoid_imagery=None):


        print(

            "Scheduler 正在检查..."

        )



        # =========================
        # 1. 获取当前状态
        # =========================


        state = (

            self.brain.state.get()

        )



        # =========================
        # 2. 获取用户画像
        #    （名字/喜好/目标，
        #    意图系统要看目标）
        # =========================


        identity = (

            self.brain.memory.get_profile()

        )



        # =========================
        # 3. 获取长期记忆
        # =========================


        memories = (

            self.brain.memory.get_experiences()

        )



        # =========================
        # 4. 获取关系状态
        # =========================


        relationship = (

            self.brain.relationship.get_status()

        )



        # =========================
        # 5. 生成主动意图
        # =========================


        intentions = self.intention.analyze(

            state,

            identity,

            memories

        )



        print(

            "主动意图:",

            intentions

        )



        # =========================
        # 话茬优先：
        # 对方提过近期的安排，
        # 主动问后续是最像朋友的
        # 主动方式。
        #
        # 那件事刚好到点（过去 24
        # 小时内）的话茬提到最高
        # 优先级 —— 这是整个主动
        # 系统里最接近"事件驱动"
        # 的时刻
        # =========================

        follow_ups = self._load_follow_ups()

        if follow_ups:

            due_hit = any(

                i.get("_due_hit")
                for i in follow_ups

            )

            intentions.append({

                "type": "follow_up",

                "reason": (

                    "他提的那件事刚到点"
                    if due_hit
                    else "对方之前提过近期安排"
                ),

                "priority": (
                    0.95 if due_hit else 0.9
                ),

            })



        # =========================
        # 没有主动需求
        # =========================


        if not intentions:


            print(

                "暂无主动需求"

            )


            return None




        # =========================
        # 6. 判断是否允许打扰
        # =========================


        interrupt_result = (

            self.interruption.check(

                intentions,

                state,

                relationship

            )

        )



        print(

            "打扰判断:",

            interrupt_result

        )





        if not interrupt_result["allowed"]:


            return None





        # =========================
        # 7. 生成主动消息
        # 带上最近聊的内容，
        # 她才说得像接着话茬，
        # 而不是自说自话
        # =========================


        recent_dialogue = []

        try:

            from memory.conversation import (
                ConversationManager
            )

            recent_dialogue = (

                ConversationManager()
                .get_recent(8)

            )

        except Exception:

            recent_dialogue = []


        message = self.proactive.generate(

            interrupt_result["selected"],

            state,

            identity,

            memories,

            echo_context=(
                self.brain._echo_context()
            ),

            recent_dialogue=recent_dialogue,

            follow_ups=follow_ups,

            avoid_imagery=avoid_imagery

        )


        print(

            "EchoLover:",

            message

        )


        # 话茬跟着消息一起交出去。
        # 只有守门人审核通过、
        # 消息真的发出去了，
        # 调用方才调 mark_follow_ups_asked
        # 把它标记为已问——
        # 中途被丢掉的话茬留着下次再问。

        return {

            "text": message,

            "follow_ups": follow_ups,

        }
