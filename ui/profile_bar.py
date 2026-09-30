from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout
)

from PySide6.QtGui import QPixmap

from PySide6.QtCore import (
    Qt,
    QThread,
    Signal
)

from core.identity import Identity

from core.paths import resolve_asset

from core import presence

from core import inclination

from ui.theme import get_theme


# ==================================================
# 顶栏：她的名字 + 她的当下
#
# 原来第二行写死「在线 · 正在陪伴你」。
# 这句话永远不变，
# 等于占着 70px 的高度说一句谎：
# 她其实在上课、在赶稿、在图书馆发呆。
#
# 现在换成 ActivityEngine 给的当下，
# 每半小时自然换一件事，
# 和她嘴里说的是同一件事。
# ==================================================

class PresenceWorker(QThread):

    # 天气要联网，
    # 不能堵住界面线程

    text_ready = Signal(str)


    def run(self):

        try:

            self.text_ready.emit(
                presence.full_text()
            )

        except Exception:

            # 网络不通就退回
            # 只用活动那一半，
            # 顶栏不能空着

            self.text_ready.emit(
                presence.activity_text()
            )


class ProfileBar(QWidget):


    def __init__(self):


        super().__init__()


        # 身份管理

        self.identity = Identity()

        self.theme = get_theme()

        self._presence_worker = None


        self.init_ui()





    def init_ui(self):


        t = self.theme


        layout = QHBoxLayout()


        layout.setContentsMargins(
            15,
            5,
            15,
            5
        )


        layout.setSpacing(
            12
        )


        # =========================
        # Echo头像
        # =========================

        self.avatar_label = QLabel()


        self.avatar_label.setFixedSize(
            44,
            44
        )


        self.avatar_label.setAlignment(
            Qt.AlignCenter
        )


        self.avatar_label.setStyleSheet(
            f"QLabel {{ "
            f"border-radius:22px; }}"
        )


        layout.addWidget(
            self.avatar_label
        )


        # =========================
        # 名字
        # 状态（上下两行，
        # 挤在一行读不出重点）
        # =========================

        info_layout = QVBoxLayout()


        info_layout.setSpacing(
            3
        )


        self.name_label = QLabel()


        name_font = (
            self.name_label.font()
        )


        name_font.setFamily(
            t["name_font"]
        )


        name_font.setPointSize(
            15
        )


        name_font.setBold(
            True
        )


        self.name_label.setFont(
            name_font
        )


        self.name_label.setStyleSheet(
            f"color:{t['name_color']};"
        )


        info_layout.addWidget(
            self.name_label
        )


        # 状态：一个圆点 + 一句话

        status_row = QHBoxLayout()

        status_row.setSpacing(
            6
        )


        self.status_dot = QLabel()

        self.status_dot.setFixedSize(
            6,
            6
        )


        self.status_label = QLabel()


        status_font = (
            self.status_label.font()
        )


        status_font.setPointSize(
            11
        )


        status_font.setBold(
            False
        )


        self.status_label.setFont(
            status_font
        )


        status_row.addWidget(
            self.status_dot
        )

        status_row.addWidget(
            self.status_label
        )

        status_row.addStretch()


        info_layout.addLayout(
            status_row
        )


        layout.addLayout(
            info_layout
        )

        layout.addStretch()


        self.setLayout(
            layout
        )


        self.setFixedHeight(
            64
        )


        self.setStyleSheet(
            f"""
            QWidget {{

                background:{t['topbar_bg']};

            }}

            """
        )


        self.refresh()


    # =========================
    # 状态文字
    # =========================

    def _set_status(self, text):

        t = self.theme

        self.status_label.setText(
            text
        )

        self.status_label.setStyleSheet(
            f"color:{t['status_color']};"
        )

        self.status_dot.setStyleSheet(
            f"""
            QLabel {{
                background:{t['accent']};
                border-radius:3px;
            }}
            """
        )



    # =========================
    # 刷新Echo身份信息与当下状态
    # =========================

    def refresh(self):


        name = self.identity.get(
            "echo_name"
        )


        if name is None:

            name = "Soulmate"


        self.name_label.setText(
            name
        )


        # 更新头像

        avatar_path = self.identity.get(
            "avatar"
        )


        if avatar_path:


            pixmap = QPixmap(
                resolve_asset(avatar_path)
            )


            if not pixmap.isNull():


                pixmap = pixmap.scaled(

                    44,

                    44,

                    Qt.KeepAspectRatio,

                    Qt.SmoothTransformation

                )


                self.avatar_label.setPixmap(
                    pixmap
                )


            else:


                self._avatar_fallback()


        else:


            self._avatar_fallback()


        # 当下先立刻显示她在做什么：
        # 这个不联网，秒出

        text = presence.activity_text()

        # 她不在状态的时候才说出来。
        # 想聊的日子什么都不加 ——
        # 真人也是这样，
        # 你只会注意到他哪天不对劲，
        # 不会注意到他哪天正常。
        #
        # 这条还有个副作用：
        # 她"话少"和"她失声了"
        # 现在长得不一样了。

        state = inclination.current()

        if state.get("level") != "open":

            text = (
                f"{text} · "
                f"{state['label']}"
            )

        self._set_status(text)


        # 天气慢慢补，
        # 上一轮还没跑完就不重复起线程

        if self._presence_worker is None:

            self._presence_worker = (
                PresenceWorker()
            )

            self._presence_worker \
                .text_ready \
                .connect(
                    self._on_presence
                )

            self._presence_worker \
                .finished \
                .connect(

                    self._presence_worker
                    .deleteLater

                )

            self._presence_worker \
                .finished \
                .connect(
                    self._presence_done
                )

            self._presence_worker.start()


    def _on_presence(self, text):

        self._set_status(text)


    def _presence_done(self):

        self._presence_worker = None


    # =========================
    # 退出前收一下天气线程
    #
    # 网络慢的时候它能跑十几秒。
    # 不收的话进程退出时会甩一条
    # "QThread: Destroyed while
    #  thread is still running"。
    #
    # quit() 打断不了阻塞中的网络请求，
    # 这里的 wait 只是给它一个
    # 体面收场的机会，
    # 超时也照样退出。
    # =========================

    def shutdown(self):

        worker = self._presence_worker

        if worker is None:

            return

        worker.quit()

        worker.wait(2000)


    def _avatar_fallback(self):

        t = self.theme

        self.avatar_label.setText(
            "Soulmate"
        )

        self.avatar_label.setStyleSheet(
            f"""
            QLabel {{
                background:{t['avatar_in_bg']};
                color:{t['send_text']};
                border-radius:22px;
                font-size:12px;
            }}
            """
        )
