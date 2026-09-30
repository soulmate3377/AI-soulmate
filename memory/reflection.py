from memory.long_term_memory import LongTermMemory




class MemoryReflection:



    def __init__(self):

        self.memory = LongTermMemory()





    def reflect(self):


        memories = (
            self.memory.get_all()
        )



        if not memories:


            return None



        identity = {

            "type":
            "user_identity",


            "traits":[],

            "interests":[],

            "goals":[]

        }



        for item in memories:


            content = (
                item.get("content","")
            )



            if "AI" in content or "人工智能" in content:


                identity["interests"].append(
                    "人工智能"
                )



            if "成为" in content or "目标" in content:


                identity["goals"].append(
                    content
                )



            if "开发" in content or "项目" in content:


                identity["traits"].append(
                    "喜欢创造和实践"
                )



        return identity