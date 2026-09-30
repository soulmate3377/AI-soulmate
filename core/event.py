class EchoLoverEvent:



    def __init__(self):


        self.listeners = []





    def subscribe(

        self,

        callback

    ):


        self.listeners.append(

            callback

        )





    def emit(

        self,

        message

    ):


        for callback in self.listeners:


            callback(

                message

            )