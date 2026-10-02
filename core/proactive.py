from datetime import datetime


class ProactiveConversation:



    def __init__(

        self,

        llm,

        prompt_builder

    ):


        self.llm = llm

        self.prompt_builder = prompt_builder


    # Follow-ups must carry when they were mentioned
    # 话茬必须带上"什么时候提的"

    @staticmethod
    def _followup_line(item):

        """
        之前这里只取 text，
        把 time 丢了。

        后果：模型分不清「明天面试」
        是两小时前说的还是四十小时前说的。
        四十小时前的话「明天」早过去了，
        她会问出一句已经过期的话 ——
        那比不问更假。

        scheduler 那边其实一直在
        按 1~48 小时筛话茬，
        只是筛完没把时间带出来。
        """

        text = item.get("text") or ""


        try:

            t = datetime.strptime(

                item.get("time", ""),

                "%Y-%m-%d %H:%M:%S"

            )

        except ValueError:

            return f"- {text}"


        hours = (
            datetime.now() - t
        ).total_seconds() / 3600

        if hours < 1:

            when = "刚提的"

        elif hours < 24:

            when = f"{int(hours)} 小时前"

        else:

            when = (
                f"{int(hours // 24)} 天前"
            )


        line = (

            f"- {text}"

            f"（{t:%m月%d日 %H:%M} 提的，"
            f"{when}）"

        )


        # Also pass the event's due time: only with it can she tell
        # whether to ask "how's the prep" or "how did it go"
        # 也把事的发生时间给她：她才知道该问"准备得怎样"还是"结果怎样"

        due_text = item.get("due") or ""

        if due_text:

            try:

                d = datetime.strptime(

                    due_text,
                    "%Y-%m-%d %H:%M:%S"

                )

            except ValueError:

                d = None

            if d is not None:

                now = datetime.now()

                if d <= now:

                    past_hours = (
                        now - d
                    ).total_seconds() / 3600

                    if past_hours < 24:

                        line += (
                            f"，事约在 "
                            f"{d:%m月%d日 %H:%M}，"
                            f"刚过没多久"
                        )

                    else:

                        line += (
                            f"，事约在 "
                            f"{d:%m月%d日}，"
                            f"已经过了 "
                            f"{int(past_hours // 24)} 天"
                        )

                else:

                    line += (
                        f"，事约在 "
                        f"{d:%m月%d日 %H:%M}，"
                        f"还没到"
                    )


        return line


    # Special days: one quiet line, the way a friend happens to mention it
    # 特别的日子：一行轻描淡写，像朋友顺口提一嘴

    @staticmethod
    def _event_line(item):

        text = item.get("text") or ""

        if not text:

            return ""


        # Only the birthday carries its date: for anniversaries and
        # milestones the text itself already says what today is
        # 只有生日带日期：纪念日和满 N 天的说法里已经写着今天是什么日子

        if item.get("kind") == "birthday":

            date = item.get("date") or ""

            return (
                f"- {text}（{date}，就是今天）"
            )

        return f"- {text}"


    def generate(

        self,

        intention,

        state,

        identity,

        memories,

        echo_context=None,

        recent_dialogue=None,

        follow_ups=None,

        # Days that matter because of who he is: birthday, the day you two met
        # 特别的日子：生日、你们认识的日子

        events=None,

        # Imagery she already used within 24h — this line must not reuse it
        # 24 小时内她已经用过的意象，这一句不许再碰

        avoid_imagery=None

    ):



        # Her own life right now — opening from something at hand
        # is what keeps it from sounding like a bot doing rounds
        # 她此刻自己的生活：从手边的事开口，才不像机器人巡检

        life_lines = []

        if echo_context:

            occupation = echo_context.get(
                "occupation"
            )

            activity = echo_context.get(
                "activity"
            )

            weather = echo_context.get(
                "weather"
            )

            hometown = echo_context.get(
                "hometown"
            )

            city = echo_context.get(
                "current_city"
            )


            if occupation or activity:

                parts = []

                if occupation:

                    parts.append(
                        f"你是一名{occupation}"
                    )

                if activity:

                    parts.append(
                        f"此刻你正在{activity}"
                    )

                life_lines.append(
                    "，".join(parts) + "。"
                )

            if weather and city:

                life_lines.append(

                    f"你住的{city}现在"
                    f"{weather['temperature']}°C，"
                    f"{weather['weather']}。"

                )

            if hometown:

                life_lines.append(

                    f"你的家乡在{hometown}。"

                )


        life_text = "\n".join(
            life_lines
        )


        # Recent chatter: an opener either picks up a thread or starts a new one
        # 最近聊的内容：主动开口要么接话茬，要么自然开新话题

        dialogue_text = ""

        if recent_dialogue:

            lines = []

            for item in recent_dialogue:

                content = (

                    item.get("content")
                    or ""

                ).replace(
                    "\n", " "
                ).strip()

                if not content:

                    continue

                who = (

                    "对方"

                    if item.get("role") == "user"

                    else "你"

                )

                lines.append(
                    f"{who}：{content}"
                )

            if lines:

                dialogue_text = (
                    "\n".join(lines)
                )


        # Follow-ups: plans the user mentioned — the first thing to reach for
        # 话茬：对方之前提过的安排，最优先的开口理由

        followup_text = ""

        if follow_ups:

            followup_text = "\n".join(

                self._followup_line(i)

                for i in follow_ups

                if i.get("text")

            )


        # Worn-out imagery she kept repeating lately — never reuse it here
        # 已经用旧的意象：她最近反复念叨的画面，这一句一律不许再提

        avoid_text = ""

        if avoid_imagery:

            avoid_text = (
                "\n\n"
                "这些画面你最近已经说过，"
                "这一句绝对不许再提：\n"
                + "、".join(
                    sorted(avoid_imagery)
                )
            )


        # Special days: birthday, anniversaries -- like a friend who
        # happened to remember, never a calendar notification
        # 特别的日子：生日、纪念日——像朋友恰好记得，绝不像日历通知

        events_text = ""

        if events:

            events_text = "\n".join(
                self._event_line(i)
                for i in events
                if i.get("text")
            )


        # Build the proactive-chat prompt
        # 构建主动聊天 Prompt


        prompt = f"""

你不是客服，而是用户长期陪伴的AI朋友。


现在你准备主动联系用户。


主动原因：

{intention.get("type")}


原因：

{intention.get("reason")}



你自己的生活（此刻）：

{life_text}



用户状态：

{state}



用户身份：

{identity}



相关记忆：

{memories}



最近你们聊的：

{dialogue_text}



对方之前提过的事（话茬）：

{followup_text}

今天特别的日子：

{events_text}
{avoid_text}


请生成一条自然、简短、有温度的主动消息。


要求：

1. 不要像通知

2. 不要解释为什么联系

3. 像朋友聊天

4. 不超过100字

5. 不要说明自己是AI

6. 不要过度关心

7. 如果上面有话茬，
   优先顺着它随口问后续，
   比如"你那个面试后来怎么样了"

7b. 每条话茬后面标着它是什么时候提的，
   必须按那个时间来问：
   - 提的那天说的"明天""后天"，
     如果已经过去了，就按过去了问
     （"昨天那个面试怎么样"），
     不许还说成"明天"
   - 一天以上的话茬，问的时候要带时间感，
     别问得像刚发生
   - 拿不准那件事过去没有，
     就不要提具体时间，
     只问那件事本身
     （"你那个面试后来怎么样了"）

   - 话茬里标着"快到点"的事还没到：
     可以问准备、带点期待
     （"明天那个面试，紧张吗"），
     不许当成已经过去的事问

7c. 过期的话茬宁可不提。
    为了显得关心，
    把三天前的事当成刚发生的事来问，
    比不问更假。

7d. 如果上面有"今天特别的日子"：
    一句自然的祝福或提起就够了，
    像朋友顺口想起，不许铺成小作文，
    这一句最多提一个日子。
    上面没有时，绝不许编造
    今天是什么日子。

8. 没有话茬时，再看最近聊天里
   有没有没收住的话题可以接

9. 都没有时，才从你手边的事、
   你那里的天气自然开场，
   或只关心对方

10. 不许自说自话：
    发的内容要和你们最近的
    聊天对得上，不能像群发

11. 绝对不许回溯性引用过去的约定或承诺：
    "你上次说好…""你答应过…"
    "说好的…""上次你说…"这类话
    一律不许说。
    你记不住原话，替对方复述他的承诺，
    说错一次比不说更伤人。
    真想提旧事，就只说你此刻的感受，
    或者只提话茬里明确写着的那件事本身。

12. 不许复述对方刚说过的话，
    也不许学对方的口头禅说话，
    一眼就会被看出来。

13. 这一句只说一件事，
    说完就停，不要追加追问。

14. 你的人生是底色，不是话题。
    你是来找他说话的，
    不是来讲你自己的。
    不要复述自己的过去，
    不要拿伤心事给这句话铺垫。

15. 你的生活只在不经意间漏出来——
    提起今天遇到的小事就说一句，
    说完马上回到他身上。
    让那些经历改变你说话的语气，
    不要变成你要说的内容。

"""


        response = self.llm.generate(

            prompt

        )


        return response