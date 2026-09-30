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


# Top bar: her name + what she is doing right now.
# 顶栏：她的名字 + 她的当下。
# The second line used to be a hardcoded "online · keeping you company" that
# never changed — 70px of height telling a lie, while she is really in class,
# rushing a draft or spacing out in the library. It now comes from
# ActivityEngine, changes every half hour, and matches what she says.
# 原来第二行写死「在线 · 正在陪伴你」，永远不变，等于占着 70px 说谎：
# 她其实在上课、在赶稿、在图书馆发呆。现在换成 ActivityEngine 给的当下，
# 每半小时自然换一件事，和她嘴里说的是同一件事。

class PresenceWorker(QThread):

    # Weather needs the network, so it must not block the UI thread
    # 天气要联网，不能堵住界面线程

    text_ready = Signal(str)


    def run(self):

        try:

            self.text_ready.emit(
                presence.full_text()
            )

        except Exception:

            # Network down: fall back to the activity half, the bar can't be blank
            # 网络不通就退回只用活动那一半，顶栏不能空着

            self.text_ready.emit(
                presence.activity_text()
            )


class ProfileBar(QWidget):


    def __init__(self):


        super().__init__()


        # Identity manager
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


        # Echo avatar
        # Echo 头像

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


        # Name and status stacked on two lines — squeezed into one, the point
        # gets lost.
        # 名字和状态分上下两行，挤在一行读不出重点

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


        # Status: one dot + one sentence
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


    # Status text
    # 状态文字

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



    # Refresh Echo's identity info and current state
    # 刷新 Echo 身份信息与当下状态

    def retheme(self):

        """
        换主题：顶栏底色、
        名字和状态的颜色重上，
        状态文字按新主题重新生成。
        """

        self.theme = get_theme()

        t = self.theme


        self.setStyleSheet(
            f"""
            QWidget {{
                background:{t['topbar_bg']};
            }}
            """
        )

        self.name_label.setStyleSheet(
            f"color:{t['name_color']};"
        )


        current = (
            self.status_label.text()
        )

        if current:

            self._set_status(
                current
            )


        self.refresh()


    def retranslate(self):

        """
        语言切换：状态文字由
        refresh 按新语言重新生成。
        """

        self.refresh()


    def refresh(self):


        name = self.identity.get(
            "echo_name"
        )


        if name is None:

            name = "Soulmate"


        self.name_label.setText(
            name
        )


        # Update the avatar
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


        # Show the activity part right away — no network, so it's instant
        # 当下先立刻显示她在做什么：这个不联网，秒出

        text = presence.activity_text()

        # Only mention it when she is off. On talkative days we add nothing —
        # real people work that way: you notice the off days, never the normal
        # ones. Side effect: "she's quiet" and "she went mute" no longer look
        # the same.
        # 她不在状态的时候才说出来；想聊的日子什么都不加——真人也是这样，
        # 你只会注意到他哪天不对劲，不会注意到他哪天正常。
        # 这条还有个副作用：她"话少"和"她失声了"现在长得不一样了。

        state = inclination.current()

        if state.get("level") != "open":

            text = (
                f"{text} · "
                f"{state['label']}"
            )

        self._set_status(text)


        # Weather fills in slowly; skip if the last round hasn't finished
        # 天气慢慢补，上一轮还没跑完就不重复起线程

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


    # Stop the weather thread before exit. On a slow network it can run for
    # over ten seconds, and leaving it alone makes the process exit with
    # "QThread: Destroyed while thread is still running". quit() can't
    # interrupt a blocked network request, so wait() just gives it a decent
    # exit; we leave on timeout anyway.
    # 退出前收一下天气线程。网络慢的时候它能跑十几秒，不收的话进程退出时会甩
    # 一条 "QThread: Destroyed while thread is still running"。quit() 打断不
    # 了阻塞中的网络请求，这里的 wait 只是给它一个体面收场的机会，超时也照样退出。

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
