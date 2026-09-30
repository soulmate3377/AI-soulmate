from memory.vector_memory import VectorMemory
from memory.long_memory import LongMemory


class MemoryRetriever:



    def __init__(self):


        self.vector_memory = VectorMemory()

        self.memory = LongMemory()



    def retrieve(

        self,

        message,

        limit=5

    ):


        result = []



        # 1. vector semantic search
        # 1. 向量语义搜索

        try:

            vector_result = (
                self.vector_memory.search(
                    message,
                    top_k=limit
                )
            )

        except Exception as e:

            print(
                "记忆检索失败（跳过）:",
                e
            )

            vector_result = []


        for item in vector_result:

            result.append(
                {
                    "type": "memory",
                    "content": item,
                }
            )



        # 2. add what we know about the user
        # 2. 用户画像补充

        try:

            profile = (
                self.memory.get_profile()
            )

            if profile:

                result.append(
                    {
                        "type": "profile",
                        "content": profile,
                    }
                )

        except Exception:

            pass



        return result
