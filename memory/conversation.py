import os
import shutil
from datetime import datetime

from core import storage
from core.paths import resolve_data_file



class ConversationManager:


    def __init__(self):

        self.file = resolve_data_file(
            "memory/conversations.json"
        )


        # Create it on first run; atomic writes mean a power cut loses at most one .tmp, never half a file
        # 没有聊天记录文件时创建。统一走原子写入，断电最多丢一个没写完的 .tmp，不会留下半个 conversations.json

        if not os.path.exists(self.file):

            storage.write_json(
                self.file,
                []
            )



    def _load(self):

        """
        读取整份聊天记录。

        之前每条消息都是
        open("w") 重写整个文件：
        写到一半断电/崩溃，
        整份记录就损坏了。
        现在读写统一走 storage
        的原子读写。

        还有一层兜底：
        文件真的损坏读不出来时，
        先留一份现场（.corrupt-时间戳）
        再从空开始——
        不让一次坏文件
        演变成整段历史被悄悄清空。
        """

        data = storage.read_json(
            self.file,
            None
        )


        if data is not None:

            return data


        # Either the file is gone or it is corrupt
        # 到这里要么文件不存在，要么已经损坏

        if os.path.exists(self.file):

            try:

                shutil.copy2(

                    self.file,

                    self.file

                    + ".corrupt-"

                    + datetime.now().strftime(
                        "%Y%m%d-%H%M%S"
                    ),

                )

            except OSError:

                pass


        return []



    def add_message(
        self,
        role,
        content
    ):


        conversations = self._load()


        message = {

            "time":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "role":
            role,

            "content":
            content
        }


        conversations.append(
            message
        )


        storage.write_json(
            self.file,
            conversations
        )



    def get_recent(
        self,
        limit=10
    ):


        conversations = self._load()


        return conversations[-limit:]



    def get_all(self):

        """
        整份聊天记录。
        搜索和导出用。
        """

        return self._load()



    def remove_last_echo(self):

        """
        删掉最后一条她的回复
        （重新生成用）。

        只认结尾的 echo 消息：
        最后一条不是她说的，
        说明状态不对，不动文件。

        返回删掉的内容；
        没删返回 None。
        """

        conversations = (
            self._load()
        )


        if not conversations:

            return None


        last = conversations[-1]


        if last.get("role") != "echo":

            return None


        conversations.pop()


        storage.write_json(
            self.file,
            conversations
        )


        return last.get("content")
