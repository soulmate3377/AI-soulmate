class ActionExecutor:


    def __init__(

        self,

        llm=None

    ):


        self.llm = llm



    def execute(

        self,

        action,

        data=None

    ):


        """

        执行EchoLover主动行为

        """


        if action is None:

            return None


        action_type = action.get(

            "type",

            ""

        )


        # =====================
        # 主动发送消息
        # =====================

        if action_type == "send_message":

            content = action.get(

                "content",

                ""

            )

            # 决策层只给出"该不该联系"，
            # 没给内容时由行动层现场生成

            if not content and self.llm:

                content = self._generate_message(

                    data

                )

            if not content:

                return None

            return {

                "type": "message",

                "content": content

            }

        # 明确不联系

        if action_type == "none":

            return None

        return None


    # =====================
    # 生成主动消息内容
    # =====================

    def _generate_message(self, data=None):

        data = data or {}

        prompt = f"""

你是用户长期陪伴的AI朋友。

现在你想主动联系用户。

用户当前状态：

{data.get("state")}

你们的关系：

{data.get("relationship")}

相关记忆：

{data.get("memories")}

请生成一条自然、简短、有温度的主动消息。

要求：

1. 不要像通知

2. 不要解释为什么联系

3. 像朋友聊天

4. 不超过100字

"""

        return self.llm.generate(

            prompt

        )
