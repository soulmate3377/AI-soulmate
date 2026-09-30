import time
from datetime import datetime
from core.event import SoulmateEvent


class Scheduler:


    def __init__(
        self,
        brain,
        interval=60
    ):

        self.brain = brain

        # 检查间隔（秒）

        self.interval = interval

        self.running = False



    def start(self):


        self.running = True


        print(
            "Echo Scheduler 已启动"
        )


        while self.running:


            self.check()


            time.sleep(
                self.interval
            )



    def stop(self):

        self.running = False



    def check(self):


        print(
            "Scheduler检查:",
            datetime.now()
        )


        result = (
            self.brain.proactive_think()
        )


        if result["action"] == "send_message":


            print(
                "Echo主动消息:"
            )


            print(
                result["message"]
            )