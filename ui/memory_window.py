# memory_window.py
#
# 「她记得的事」
#
# Echo 记住的每一条都摊开给用户看，
# 并且可以删。
#
# 这个面板不只是展示：
# 她记错了、记串了、把没发生过的事
# 当成真事——用户一眼就能发现，
# 删掉就等于纠正了她。
# 这是目前唯一的纠错通道。

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QMessageBox,
)

from PySide6.QtCore import Qt, Signal

from ui.i18n import tr

from ui.theme import get_theme


# 记忆分类的显示名

KIND_LABEL = {

    "promise": "约定",

    "preference": "喜好",

    "fact": "关于她",

    "statement": "说过的话",

}


class MemoryRow(QWidget):

    delete_requested = Signal(int)

    def __init__(self, index, record, theme):

        super().__init__()

        self.index = index

        t = theme

        text = record.get("text") or ""

        summary = (
            record.get("summary") or text
        )

        role = record.get("role") or "user"

        kind = record.get("kind") or (
            "statement"
        )

        when = record.get("time") or ""

        who = "她" if role == "echo" else "你"

        tag = KIND_LABEL.get(kind, "")


        layout = QHBoxLayout()

        layout.setContentsMargins(
            10, 8, 10, 8
        )

        layout.setSpacing(10)


        # --------------------
        # 左：摘要 + 原文
        # --------------------

        left = QVBoxLayout()

        left.setSpacing(2)


        head = QLabel(
            f"{who}"
            + (f" · {tag}" if tag else "")
        )

        head.setStyleSheet(
            f"""
            QLabel {{
                color:{t['status_color']};
                font-size:12px;
                font-weight:normal;
            }}
            """
        )

        left.addWidget(head)


        body = QLabel(summary)

        body.setWordWrap(True)

        body.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        body.setStyleSheet(
            f"""
            QLabel {{
                color:{t['bubble_in_text']};
                font-size:14px;
                font-weight:normal;
                background:transparent;
            }}
            """
        )

        left.addWidget(body)


        # 摘要是截断过的，
        # 和原文不一样才另外显示

        if (
            text
            and text != summary
        ):

            full = QLabel(text)

            full.setWordWrap(True)

            full.setTextInteractionFlags(
                Qt.TextSelectableByMouse
            )

            full.setStyleSheet(
                f"""
                QLabel {{
                    color:{t['time_color']};
                    font-size:12px;
                    font-weight:normal;
                    background:transparent;
                }}
                """
            )

            left.addWidget(full)


        if when:

            stamp = QLabel(when[:16])

            stamp.setStyleSheet(
                f"""
                QLabel {{
                    color:{t['time_color']};
                    font-size:11px;
                    font-weight:normal;
                    background:transparent;
                }}
                """
            )

            left.addWidget(stamp)


        layout.addLayout(left, 1)


        # --------------------
        # 右：删除
        # --------------------

        self.delete_button = QPushButton(
            "删掉"
        )

        self.delete_button.setObjectName(
            "rowDelete"
        )

        self.delete_button.setFixedWidth(64)

        self.delete_button.setToolTip(
            tr("她记错了就删掉这条")
        )

        self.delete_button.clicked.connect(
            self._on_delete
        )

        layout.addWidget(
            self.delete_button,
            0,
            Qt.AlignTop
        )


        self.setLayout(layout)


        self.setStyleSheet(
            f"""
            QWidget {{
                background-color:{t['bubble_in_bg']};
                border:1px solid {
                    t['bubble_in_border']
                };
                border-radius:10px;
            }}
            """
        )


    def _on_delete(self):

        self.delete_requested.emit(
            self.index
        )


class MemoryWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.theme = get_theme()

        self.vector = None

        # [(在库里的下标, 记录), ...]
        # 删完按下标重建索引，
        # 所以必须留住原下标

        self.rows = []

        self.init_ui()

        self.reload()


    # =========================
    # 界面
    # =========================

    def init_ui(self):

        t = self.theme

        self.setWindowTitle(
            tr("她记得的事")
        )

        self.resize(
            640, 620
        )

        layout = QVBoxLayout()

        layout.setContentsMargins(
            18, 16, 18, 16
        )

        layout.setSpacing(12)


        # --------------------
        # 标题
        # --------------------

        title = QLabel(tr("她记得的事"))

        title.setAlignment(
            Qt.AlignCenter
        )

        font = title.font()

        font.setPointSize(19)

        title.setFont(font)

        title.setStyleSheet(
            f"""
            QLabel {{
                color:{t['name_color']};
                background:transparent;
                font-weight:bold;
            }}
            """
        )

        layout.addWidget(title)


        hint = QLabel(

            "下面每一条她都会当真。"
            "记错了、记串了的，删掉就好。"

        )

        hint.setWordWrap(True)

        hint.setAlignment(
            Qt.AlignCenter
        )

        hint.setStyleSheet(
            f"""
            QLabel {{
                color:{t['status_color']};
                font-size:13px;
                font-weight:normal;
                background:transparent;
            }}
            """
        )

        layout.addWidget(hint)


        # --------------------
        # 搜索
        # --------------------

        self.search_box = QLineEdit()

        self.search_box.setPlaceholderText(
            "搜一下她记了什么..."
        )

        self.search_box.textChanged.connect(
            self.reload
        )

        layout.addWidget(
            self.search_box
        )


        # --------------------
        # 列表
        # --------------------

        self.scroll = QScrollArea()

        self.scroll.setWidgetResizable(
            True
        )

        self.list_widget = QWidget()

        self.list_layout = QVBoxLayout()

        self.list_layout.setContentsMargins(
            0, 0, 0, 0
        )

        self.list_layout.setSpacing(8)

        self.list_layout.setAlignment(
            Qt.AlignTop
        )

        self.list_widget.setLayout(
            self.list_layout
        )

        self.scroll.setWidget(
            self.list_widget
        )

        layout.addWidget(
            self.scroll, 1
        )


        # --------------------
        # 底部：计数 + 清空
        # --------------------

        footer = QHBoxLayout()

        self.count_label = QLabel("")

        self.count_label.setStyleSheet(
            f"""
            QLabel {{
                color:{t['status_color']};
                font-size:13px;
                font-weight:normal;
                background:transparent;
            }}
            """
        )

        footer.addWidget(
            self.count_label, 1
        )


        self.clear_button = QPushButton(
            tr("全部忘掉")
        )

        self.clear_button.clicked.connect(
            self.clear_all
        )

        footer.addWidget(
            self.clear_button
        )

        layout.addLayout(footer)


        self.setLayout(layout)


        self.setStyleSheet(
            f"""
            QWidget {{
                background-color:{t['window_bg']};
                color:{t['bubble_in_text']};
            }}

            QLineEdit {{
                background-color:{t['input_bg']};
                border:1px solid {
                    t['input_border']
                };
                border-radius:8px;
                padding:8px 12px;
                font-size:14px;
                color:{t['input_text']};
            }}

            QLineEdit:focus {{
                border:1px solid {
                    t['input_focus_border']
                };
            }}

            QScrollArea {{
                border:none;
                background:transparent;
            }}

            QPushButton {{
                background-color:{t['send_bg']};
                color:{t['send_text']};
                border:none;
                border-radius:8px;
                padding:8px 18px;
                font-size:14px;
                font-weight:bold;
            }}

            QPushButton:hover {{
                background-color:{t['send_hover']};
            }}

            QPushButton#rowDelete {{
                background-color:transparent;
                color:{t['status_color']};
                border:1px solid {
                    t['input_border']
                };
                padding:4px 10px;
                font-size:12px;
                font-weight:normal;
            }}

            QPushButton#rowDelete:hover {{
                background-color:{t['settings_hover']};
                color:{t['bubble_out_bg']};
            }}
            """
        )


    # =========================
    # 载入
    # =========================

    def _ensure_vector(self):

        if self.vector is None:

            from memory.vector_memory import (
                VectorMemory
            )

            self.vector = VectorMemory()

        return self.vector


    def reload(self, _keyword=None):

        # _keyword 是搜索框 textChanged
        # 顺手带来的，用不上

        try:

            vector = self._ensure_vector()

            records = vector.all_records()

        except Exception as e:

            self.rows = []

            self._render_placeholder(
                f"记忆读取失败：{e}"
            )

            self.count_label.setText("")

            return


        keyword = (
            self.search_box.text().strip()
        )

        rows = []

        for i, record in enumerate(
            records
        ):

            if keyword and keyword not in (

                (record.get("text") or "")
                + (record.get("summary") or "")

            ):

                continue

            rows.append((i, record))


        # 最新的排在最上面

        rows.reverse()

        self.rows = rows

        self._render_list()


    def _clear_list(self):

        while self.list_layout.count():

            item = self.list_layout.takeAt(
                0
            )

            widget = item.widget()

            if widget:

                widget.deleteLater()


    def _render_placeholder(self, text):

        self._clear_list()

        label = QLabel(text)

        label.setWordWrap(True)

        label.setAlignment(
            Qt.AlignCenter
        )

        label.setStyleSheet(
            f"""
            QLabel {{
                color:{self.theme['status_color']};
                font-size:14px;
                font-weight:normal;
                padding:40px 20px;
                background:transparent;
            }}
            """
        )

        self.list_layout.addWidget(label)


    def _render_list(self):

        self._clear_list()

        self.count_label.setText(
            f"共 {len(self.rows)} 条"
        )

        if not self.rows:

            if self.search_box.text().strip():

                self._render_placeholder(
                    "没有匹配的记忆"
                )

            else:

                self._render_placeholder(

                    "她还没有记住什么。\n"
                    "多聊几句就有了。"

                )

            return


        for index, record in self.rows:

            row = MemoryRow(
                index, record, self.theme
            )

            row.delete_requested.connect(
                self.delete_one
            )

            self.list_layout.addWidget(row)


    # =========================
    # 删除
    # =========================

    def delete_one(self, index):

        try:

            self._ensure_vector().delete(
                [index]
            )

        except Exception as e:

            QMessageBox.warning(

                self,
                "删除失败",
                str(e)

            )

            return


        self.reload()


    def clear_all(self):

        # 用的是总数，不是当前筛选后的条数——
        # 清空会把所有记忆都删掉

        try:

            count = len(
                self._ensure_vector()
                .all_records()
            )

        except Exception:

            count = 0

        if not count:

            return


        answer = QMessageBox.question(

            self,

            tr("全部忘掉"),

            tr("会把她记住的 %d 条全部删掉，\n她就真的什么都不记得了。\n\n确定吗？")
            % count,

            QMessageBox.Yes
            | QMessageBox.No,

            QMessageBox.No,

        )

        if answer != QMessageBox.Yes:

            return


        try:

            self._ensure_vector().clear()

        except Exception as e:

            QMessageBox.warning(
                self,
                "清空失败",
                str(e)
            )

            return


        self.reload()


    # =========================
    # 每次打开都重新读一遍，
    # 聊天过程中新增的记忆也能看到
    # =========================

    def showEvent(self, event):

        super().showEvent(event)

        self.reload()
