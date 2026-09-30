import json
import os

from core.paths import resolve_data_file



class LongTermMemory:



    def __init__(self):


        self.file = resolve_data_file(
            "memory/long_term_memory.json"
        )


        if not os.path.exists(
            self.file
        ):


            with open(
                self.file,
                "w",
                encoding="utf-8"
            ) as f:


                json.dump(
                    [],
                    f,
                    ensure_ascii=False,
                    indent=4
                )




    def add(self, memory):


        with open(
            self.file,
            "r",
            encoding="utf-8"
        ) as f:

            data=json.load(f)



        data.append(
            memory
        )



        with open(
            self.file,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )




    def get_all(self):


        with open(
            self.file,
            "r",
            encoding="utf-8"
        ) as f:


            return json.load(f)