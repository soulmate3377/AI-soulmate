from memory.long_memory import LongMemory

from memory.long_term_memory import LongTermMemory


class MemoryConsolidator:



    def __init__(self):

        self.memory = LongMemory()



    def summarize(self):


        experiences = (
            self.memory.get_experiences()
        )



        if len(experiences) < 10:

            return None



        important = []



        for item in experiences:


            if item.get(
                "importance",
                0
            ) >= 0.7:


                important.append(

                    item.get(
                        "content"
                    )

                )



        if not important:

            return None



        summary = {

            "type":
            "long_term_summary",


            "content":
            "用户长期关注："
            +
            "；".join(
                important[-5:]
            ),


            "importance":
            1

        }


        self.long_memory.add(
        summary
        )
        return summary