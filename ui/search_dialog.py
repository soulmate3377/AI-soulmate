# ui/search_dialog.py
# Chat history search (Ctrl+F) re-runs on every keystroke: the history is one
# local json, so filtering it whole beats an index and always matches the newest
# records.
# 聊天记录搜索（Ctrl+F）。每敲一个字现搜一遍：记录就一个本地 json，
# 全量过滤比建索引简单，也永远和最新记录一致。
# Double-click a hit to jump to that bubble. Anything older than the 80 the
# current view loaded can't be jumped to, so it points at export instead.
# 双击某条结果跳回聊天里对应的气泡；比当前界面加载的 80 条更早的消息跳不过去，提示改用导出。

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QLabel,
    QListWidget,
    QListWidgetItem,
)

from PySide6.QtCore import Qt

from ui.i18n import tr
from ui.i18n import her_name


# role in the record -> label to show
# 记录里的 role → 显示称呼

def _role_labels():
    return {
        "user": tr("我"),
        "echo": her_name(),
    }



class ChatSearchDialog(QDialog):


    def __init__(
        self,
        fetch_records,
        on_jump,
        parent=None,
    ):

        super().__init__(parent)


        # Pull the whole history on every search
        # 每次搜索现取整份记录

        self.fetch_records = (
            fetch_records
        )


        # Callback on double-click, gets the whole record
        # 双击结果时回调，带上那条完整记录

        self.on_jump = on_jump


        self.setWindowTitle(
            tr("搜索聊天记录")
        )

        self.setModal(False)

        self.resize(480, 420)


        layout = QVBoxLayout()


        self.search_box = QLineEdit()

        self.search_box.setPlaceholderText(
            tr("搜点什么……")
        )

        self.search_box.textChanged.connect(
            self._search
        )

        layout.addWidget(
            self.search_box
        )


        self.count_label = QLabel(
            tr("输入关键词开始搜索")
        )

        layout.addWidget(
            self.count_label
        )


        self.result_list = (
            QListWidget()
        )

        self.result_list.itemDoubleClicked.connect(
            self._jump
        )

        layout.addWidget(
            self.result_list
        )


        self.hint_label = QLabel("")

        self.hint_label.setWordWrap(
            True
        )

        self.hint_label.setStyleSheet(
            "color:#999;"
            "font-size:11px;"
        )

        layout.addWidget(
            self.hint_label
        )


        self.setLayout(layout)


    def set_hint(self, text):

        self.hint_label.setText(
            text or ""
        )


    def _search(self, text):

        self.set_hint("")

        self.result_list.clear()


        text = (
            text or ""
        ).strip()

        if not text:

            self.count_label.setText(
                tr("输入关键词开始搜索")
            )

            return


        needle = text.lower()


        records = []

        try:

            records = (
                self.fetch_records()
                or []
            )

        except Exception:

            records = []


        hits = [

            r for r in records

            if needle in str(
                r.get("content") or ""
            ).lower()

        ]


        # Newest first
        # 最新的排最上面

        for r in reversed(hits):

            when = str(
                r.get("time") or ""
            )


            who = (
                _role_labels().get(
                    r.get("role")
                )
                or r.get("role")
                or "?"
            )


            content = " ".join(
                str(
                    r.get("content")
                    or ""
                ).split()
            )


            if len(content) > 60:

                content = (
                    content[:60]
                    + "…"
                )


            item = QListWidgetItem(

                "%s  %s：%s"
                % (
                    when[5:],
                    who,
                    content,
                )

            )


            item.setData(
                Qt.UserRole,
                r,
            )

            self.result_list.addItem(
                item
            )


        if hits:

            self.count_label.setText(
                tr("找到 %d 条")
                % len(hits)
            )

        else:

            self.count_label.setText(
                tr("没有找到")
            )


    def _jump(self, item):

        record = item.data(
            Qt.UserRole
        )


        if (
            record is None
            or self.on_jump is None
        ):

            return


        self.on_jump(record)
