from datetime import (
    datetime,
    timedelta,
)

import random

import re

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QMenu,
    QFileDialog
)

from PySide6.QtCore import Qt, QThread, QTimer, Signal

from PySide6.QtGui import (
    QGuiApplication,
    QShortcut,
    QKeySequence
)

from core.brain import Brain
from core.reply import split_reply

from core.proactive_guard import ProactiveGuard

from memory.conversation import ConversationManager

from ui.theme import get_theme
from ui.i18n import tr, her_name
from ui.message_bubble import MessageBubble
from ui.search_dialog import ChatSearchDialog


# ==================================================
# 后台思考线程
# ==================================================

class ThinkWorker(QThread):

    result = Signal(str)

    error = Signal(str)

    # 流式片段

    chunk = Signal(str)


    def __init__(
        self,
        brain,
        message,
        regenerate=False
    ):

        super().__init__()

        self.brain = brain

        self.message = message

        # 重新生成：大脑复用
        # 上一轮的 prompt，
        # 不再重算用户侧的副作用

        self.regenerate = regenerate


    def run(self):

        try:

            parts = []

            for delta in self.brain.think_stream(
                self.message,

                regenerate=(
                    self.regenerate
                ),
            ):

                parts.append(delta)

                self.chunk.emit(delta)

            self.result.emit(
                "".join(parts)
            )

        except Exception as e:

            self.error.emit(str(e))


# ==================================================
# 主动消息检查线程
# ==================================================

class ProactiveWorker(QThread):

    # 带上话茬原文，
    # 守门人要拿它核对
    # 她有没有乱引用过去的约定

    message_ready = Signal(dict)


    def __init__(
        self,
        brain,
        avoid_imagery=None
    ):

        super().__init__()

        self.brain = brain

        self.avoid_imagery = avoid_imagery


    def run(self):

        try:

            result = (
                self.brain
                .scheduler
                .run_once(

                    avoid_imagery=(
                        self.avoid_imagery
                    )

                )
            )

            if (
                result
                and result.get("text")
            ):

                self.message_ready.emit(
                    result
                )

        except Exception as e:

            print("主动消息检查失败:", e)


# ==================================================
# 主动消息回看线程
#
# 主动开口最容易编，
# 发出去之后后台过一遍回看，
# 说错了留便签，
# 他回这句话时她自然找补
# ==================================================

class ReflectionWorker(QThread):


    def __init__(
        self, brain, message, follow_ups=None
    ):

        super().__init__()

        self.brain = brain

        self.message = message

        self.follow_ups = follow_ups


    def run(self):

        try:

            self.brain.reflect_proactive(

                self.message,

                follow_ups=self.follow_ups,

            )

        except Exception as e:

            print("主动消息回看失败:", e)


# ==================================================
# 时间分隔条
# 两条消息间隔超过5分钟时插入
# ==================================================

class TimeDivider(QWidget):


    def __init__(self, time_text):

        super().__init__()


        t = get_theme()


        layout = QHBoxLayout()

        label = QLabel(time_text)

        self.time_label = label

        label.setAlignment(Qt.AlignCenter)

        self._style_label(label)


        layout.addWidget(label)

        self.setLayout(layout)


    def _style_label(self, label):

        t = get_theme()

        label.setStyleSheet(
            f"""
            QLabel {{
                color:{t['time_color']};
                font-size:11px;
                padding:6px;
                background:transparent;
            }}
            """
        )


    def retheme(self):

        self._style_label(
            self.time_label
        )


# ==================================================
# “正在输入”气泡
# 三个点循环跳动
# ==================================================

class TypingBubble(QWidget):


    def __init__(self):

        super().__init__()


        t = get_theme()

        self.dots = 0


        layout = QHBoxLayout()

        layout.setContentsMargins(
            62, 5, 14, 5
        )


        self.label = QLabel()

        self.label.setFixedWidth(64)

        self.label.setAlignment(Qt.AlignCenter)

        self._style_label(self.label)


        layout.addWidget(self.label)


    def _style_label(self, label):

        t = get_theme()

        label.setStyleSheet(
            f"""
            QLabel {{
                background-color:{t['bubble_in_bg']};
                border:1px solid {t['bubble_in_border']};
                color:{t['time_color']};
                border-radius:14px;
                border-top-left-radius:4px;
                padding:8px 0px;
                font-size:15px;
                letter-spacing:2px;
            }}
            """
        )


    def retheme(self):

        self._style_label(
            self.label
        )

        layout.addStretch()

        self.setLayout(layout)


        # 圆点动画

        self.timer = QTimer(self)

        self.timer.setInterval(400)

        self.timer.timeout.connect(
            self._tick
        )

        self.timer.start()

        self._tick()


    def _tick(self):

        self.dots = (self.dots + 1) % 4

        self.label.setText(
            "·" * max(1, self.dots)
        )


    def stop(self):

        self.timer.stop()


class ChatWidget(QWidget):


    # 她主动说话时发出，
    # 主窗口用来弹托盘通知

    proactive_received = Signal(str)


    # 两条消息间隔超过这个秒数
    # 就插入时间分隔条

    TIME_GAP = 300

    # 同一个人连着说、
    # 间隔没超过这个秒数、
    # 中间没人插话，
    # 就共用一个头像

    GROUP_WINDOW = 180


    def __init__(self):

        super().__init__()


        self.theme = get_theme()

        t = self.theme


        # =========================
        # 整体样式（跟随主题）
        # =========================

        self.setStyleSheet(
            self._chat_style()
        )


        # =========================
        # Echo大脑
        # 首次运行可能还没填API Key，
        # 不能让整个界面崩掉
        # =========================

        self.brain = None

        self.brain_error = None

        self._init_brain()


        self.think_worker = None

        self.proactive_worker = None


        # “正在输入”气泡

        self.typing_bubble = None


        # 待逐条显示的消息队列

        self.pending_parts = []


        # 流式回复的进行状态

        self._stream_buffer = ""

        self._stream_bubble = None

        # 一条消息发完后的
        # “打下一条”停顿中

        self._stream_paused = False

        # 思考线程是否已给完
        # 全部内容

        self._stream_finished = False

        # 本轮完整回复
        # （收尾兜底切分用）

        self._stream_response = None

        # 本轮已创建的气泡

        self._stream_bubbles = []


        # 上一条消息的时间

        self.last_message_time = None

        # 连续消息的归组状态：
        # 上一条是谁发的、是哪个气泡。
        # 系统消息打断归组。

        self._last_sender = None

        self._last_bubble = None



        # =========================
        # 主布局
        # =========================

        self.main_layout = QVBoxLayout()

        self.main_layout.setContentsMargins(
            0, 0, 0, 0
        )

        self.main_layout.setSpacing(0)


        # =========================
        # 聊天滚动区域
        # =========================

        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(
            True
        )


        self.message_widget = QWidget()

        self.message_widget.setStyleSheet(
            f"background-color:{t['chat_bg']};"
        )


        self.message_layout = QVBoxLayout()

        self.message_layout.setContentsMargins(
            0, 8, 0, 8
        )

        self.message_layout.setSpacing(2)

        self.message_layout.setAlignment(
            Qt.AlignTop
        )


        self.message_widget.setLayout(
            self.message_layout
        )


        self.scroll_area.setWidget(
            self.message_widget
        )


        self.main_layout.addWidget(
            self.scroll_area
        )


        # =========================
        # 底部输入栏
        # =========================

        bottom_bar = QWidget()

        bottom_bar.setObjectName("bottomBar")

        self.bottom_bar = bottom_bar

        bottom_bar.setStyleSheet(
            self._bottom_bar_style()
        )


        bottom_layout = QHBoxLayout()

        bottom_layout.setContentsMargins(
            14, 10, 14, 10
        )

        bottom_layout.setSpacing(10)


        self.input_box = QLineEdit()

        self.input_box.setPlaceholderText(
            "和她说点什么..."
        )


        self.input_box.returnPressed.connect(
            self.send_message
        )


        self.send_button = QPushButton(tr("发送"))

        self.send_button.setObjectName(
            "sendButton"
        )

        self.send_button.clicked.connect(
            self.send_message
        )


        bottom_layout.addWidget(
            self.input_box
        )

        bottom_layout.addWidget(
            self.send_button
        )


        bottom_bar.setLayout(bottom_layout)

        self.main_layout.addWidget(bottom_bar)


        self.setLayout(
            self.main_layout
        )


        # =========================
        # 聊天记录持久化：
        # 启动时恢复历史，
        # 她不是每次都"初见"你
        # =========================

        self.conversations = (
            ConversationManager()
        )


        if not self._load_history():

            her = her_name()

            self.add_message(
                tr("你好，我是%s。") % her,
                "Echo"
            )

            self.add_message(
                tr("很高兴认识你"),
                "Echo"
            )


        # 大脑没起来时给出明确指引

        if self.brain is None:

            error = self.brain_error or ""

            if "API Key" in error:

                hint = (
                    tr("（先去右上角「⚙ 设置」"
                    "里填一下 API Key，"
                    "我才能真正开口说话）")
                )

            else:

                hint = (
                    f"（启动出了点问题：{error}）"
                )


            self.add_message(

                hint,

                "系统"

            )


        # =========================
        # 主动消息守门人
        #
        # 她不再固定 30 分钟说一句。
        # 心跳每 60 秒问一次守门人，
        # 什么时候开口、说的内容合不合格，
        # 都由守门人决定。
        # =========================

        self.guard = ProactiveGuard()

        self.proactive_timer = QTimer(self)

        self.proactive_timer.setInterval(
            60 * 1000
        )

        self.proactive_timer.timeout.connect(
            self.check_proactive
        )

        self.proactive_timer.start()


        # =========================
        # 聊天记录搜索（Ctrl+F）
        # =========================

        self._search_dialog = None

        QShortcut(
            QKeySequence.Find,
            self,
            self._open_search,
        )



    # =========================
    # 初始化大脑
    # =========================

    def _init_brain(self):

        try:

            self.brain = Brain()

            self.brain_error = None

        except Exception as e:

            import traceback

            self.brain = None

            self.brain_error = str(e)


            # 把完整错误写进日志文件，
            # 方便排查

            try:

                from core.paths import data_dir

                log = (
                    data_dir()
                    / "echo_error.log"
                )

                with open(

                    log,
                    "a",
                    encoding="utf-8"

                ) as f:

                    f.write(

                        traceback
                        .format_exc()

                        + "\n\n"

                    )

            except Exception:

                pass


    # =========================
    # 设置保存后重试初始化大脑
    # 填完 Key 立即生效，不用重启
    # =========================

    def retry_brain(self):

        if self.brain is None:

            self._init_brain()


        if self.brain is not None:

            self.add_message(

                "设置好了，现在可以和我聊天了",

                "系统"

            )


    # =========================
    # 时间分隔条
    # =========================

    def _maybe_add_time_divider(self, at=None):

        now = at or datetime.now()

        prev = self.last_message_time

        added = False


        if (

            prev is None

            or (now - prev).total_seconds()
               > self.TIME_GAP

        ):

            # 跨天就把日期带上，
            # 同一天只给时间

            if (
                prev is None
                or prev.date() != now.date()
            ):

                text = now.strftime(
                    "%m月%d日 %H:%M"
                )

            else:

                text = now.strftime("%H:%M")


            self.message_layout.addWidget(

                TimeDivider(text)

            )

            added = True


        self.last_message_time = now

        return added



    # =========================
    # 添加消息气泡
    # =========================

    def add_message(
        self,
        message,
        sender,
        at=None,
        animate=True
    ):

        """
        at        这条消息自己的时间。
                  恢复历史时传记录的原文时间，
                  归组判断才准。
        animate   历史消息不淡入，
                  八十条一起淡入是在炫技，
                  不是在帮忙。
        """

        now = at or datetime.now()


        # 归组判断要用上一条的状态，
        # 得在分隔条改写 last_message_time 之前取

        prev_time = self.last_message_time

        prev_sender = self._last_sender

        prev_bubble = self._last_bubble


        divider_added = (
            self._maybe_add_time_divider(now)
        )


        grouped = (

            sender != "系统"

            and not divider_added

            and prev_bubble is not None

            and prev_sender == sender

            and prev_time is not None

            and (now - prev_time)
                .total_seconds()
                <= self.GROUP_WINDOW

        )


        # 是续句就把上一条的下圆角抹平、
        # 下边距归零；
        # 换人了就把它收圆

        if prev_bubble is not None:

            prev_bubble.set_group_edge(
                not grouped
            )


        bubble = MessageBubble(

            message,

            sender,

            grouped=grouped

        )


        # 右键菜单（复制/重新生成）
        # 由这里统一接管

        bubble.on_context_menu = (
            self._bubble_context_menu
        )


        self.message_layout.addWidget(
            bubble
        )


        if animate:

            bubble.fade_in()


        if sender == "系统":

            self._last_sender = None

            self._last_bubble = None

        else:

            self._last_sender = sender

            self._last_bubble = bubble


        QTimer.singleShot(

            0,

            self._scroll_to_bottom

        )


        return bubble


    def _scroll_to_bottom(self):

        bar = (
            self.scroll_area
            .verticalScrollBar()
        )

        bar.setValue(bar.maximum())


    # =========================
    # 恢复历史聊天记录
    # =========================

    def _load_history(self, limit=80):

        try:

            history = (
                self.conversations
                .get_recent(limit)
            )

        except Exception:

            return False

        if not history:

            return False


        sender_map = {
            "user": "我",
            "echo": "Echo",
            "assistant": "Echo",
        }


        shown = 0


        for item in history:

            content = item.get(
                "content", ""
            )

            sender = sender_map.get(
                item.get("role")
            )

            if not content or not sender:

                continue

            t = self._parse_time(
                item.get("time")
            )

            if t is None:

                # 时间读不出来就往后推十分钟：
                # 宁可时间线错开，
                # 也别让几十条历史挤成一组

                base = (
                    self.last_message_time
                    or datetime.now()
                )

                t = base + timedelta(
                    minutes=10
                )


            # 分隔条、归组、时间线
            # 全走 add_message 那套逻辑，
            # 历史和实时不再是两套规则

            self.add_message(

                content,

                sender,

                at=t,

                animate=False

            )

            shown += 1


        if not shown:

            return False

        QTimer.singleShot(
            0,
            self._scroll_to_bottom
        )

        return True


    @staticmethod
    def _parse_time(text):

        if not text:

            return None

        try:

            return datetime.strptime(

                text,
                "%Y-%m-%d %H:%M:%S"

            )

        except ValueError:

            return None




    # =========================
    # “正在输入”指示
    # =========================

    def _show_typing(self):

        self._hide_typing()

        self.typing_bubble = TypingBubble()

        self.message_layout.addWidget(
            self.typing_bubble
        )

        self._scroll_to_bottom()


    def _hide_typing(self):

        if self.typing_bubble:

            self.typing_bubble.stop()

            self.message_layout.removeWidget(
                self.typing_bubble
            )

            self.typing_bubble.deleteLater()

            self.typing_bubble = None



    # =========================
    # 逐条发送回复
    # =========================

    def _deliver_reply(self, text):


        parts = split_reply(text)

        if not parts:

            parts = [text]


        self.pending_parts = list(parts)

        self._deliver_next()


    def _deliver_next(self):


        if not self.pending_parts:

            return


        part = self.pending_parts.pop(0)

        self.add_message(part, "Echo")


        if self.pending_parts:

            self._show_typing()


            # 输入时长按字数走，
            # 像真人在打字

            delay = min(

                2500,

                400 + len(
                    self.pending_parts[0]
                ) * 55

            )


            # 15% 概率出现
            # “打了一半删掉重打”

            if random.random() < 0.15:

                QTimer.singleShot(

                    delay,

                    self._retype_pause

                )

            else:

                QTimer.singleShot(

                    delay,

                    self._deliver_next_part

                )


    def _deliver_next_part(self):

        self._hide_typing()

        self._deliver_next()


    # =========================
    # 打了一半，删掉重打
    # =========================

    def _retype_pause(self):

        self._hide_typing()


        QTimer.singleShot(

            400,

            self._retype_resume

        )


    def _retype_resume(self):

        self._show_typing()


        QTimer.singleShot(

            900,

            self._deliver_next_part

        )



    # =========================
    # 发送消息
    # =========================

    def send_message(self):


        message = (
            self.input_box.text()
        )


        if not message.strip():

            return


        # 大脑还没就绪（通常是没填Key）
        # 先尝试重新初始化，
        # 用户可能刚在设置里填了

        if self.brain is None:

            self._init_brain()


        if self.brain is None:

            error = self.brain_error or ""

            if "API Key" in error:

                hint = (
                    tr("还没有设置 API Key。\n"
                    "点右上角「⚙ 设置」选好服务商，"
                    "粘贴你的 API Key，"
                    "保存后再发一次消息。")
                )

            else:

                # 别把所有错误都误报成缺Key，
                # 显示真实原因

                hint = (
                    tr("启动时出了点问题：\n%s\n详细日志在 %s")
                    % (
                        error,
                        "%APPDATA%\\EchoLover\\"
                        "echo_error.log",
                    )
                )


            self.add_message(

                hint,

                "系统"

            )

            return


        if (

            self.think_worker is not None

            and self.think_worker.isRunning()

        ):

            return


        self.add_message(

            message,

            "我"

        )


        # 落盘，下次启动还在

        self.conversations.add_message(
            "user",
            message
        )


        # 他开口了。
        # 认真回的才把冷却清零，
        # 敷衍一句不算回应

        try:

            self.guard.note_user_message(
                message
            )

        except Exception as e:

            print(
                "守门人记录失败（跳过）:",
                e
            )


        self.input_box.clear()


        self.input_box.setEnabled(False)

        self.send_button.setEnabled(False)


        # 真人读完消息要一小会儿，
        # 延迟一点再显示“正在输入”

        QTimer.singleShot(

            600,

            self._maybe_show_typing

        )


        # 流式状态清零

        self._stream_buffer = ""

        self._stream_bubble = None

        self._stream_paused = False

        self._stream_finished = False

        self._stream_response = None

        self._stream_bubbles = []


        self.think_worker = ThinkWorker(

            self.brain,

            message

        )

        self.think_worker.chunk.connect(
            self._on_chunk
        )

        self.think_worker.result.connect(
            self.on_think_result
        )

        self.think_worker.error.connect(
            self.on_think_error
        )

        self.think_worker.start()


    # 思考线程还在跑才显示“正在输入”

    def _maybe_show_typing(self):

        if (

            self.think_worker is not None

            and self.think_worker.isRunning()

        ):

            self._show_typing()



    # =========================
    # 流式片段到达：
    # 即时写进当前气泡；
    # 遇到 --- 分隔符说明这一条
    # 发完了，停一停再发下一条
    # =========================

    # 分隔符的各种写法，
    # 模型不一定乖乖只用 ---

    _STREAM_SEP_RE = re.compile(
        r"\n\s*"
        r"(?:-{3,}|—{2,}|–{3,}|\*{3,})"
        r"\s*\n"
    )

    # 缓冲末尾可能压着
    # 不完整的分隔符

    _STREAM_TAIL_RE = re.compile(
        r"(?:\n\s*[-—–*]{0,2}"
        r"|[-—–*]{1,2})$"
    )


    def _on_chunk(self, delta):

        self._stream_buffer += delta

        # 上一条刚发完，
        # 她在“打下一条”，
        # 这期间来的内容先攒着

        if self._stream_paused:

            return

        self._pump_stream()


    def _pump_stream(self):

        # 完整分隔符到达：
        # 结束当前气泡，
        # 进入发下一条前的停顿

        m = self._STREAM_SEP_RE.search(
            self._stream_buffer
        )

        if m:

            head = self._stream_buffer[
                :m.start()
            ]

            self._stream_buffer = (
                self._stream_buffer[
                    m.end():
                ]
            )

            self._set_stream_text(head)

            self._stream_bubble = None

            self._pause_between_messages()

            return


        # 末尾可能是不完整的分隔符，
        # 先压着不显示

        text = self._stream_buffer

        tail = self._STREAM_TAIL_RE.search(
            text
        )

        if tail:

            text = text[:tail.start()]


        if text.strip():

            self._hide_typing()

            if self._stream_bubble is None:

                self._stream_bubble = (
                    self._new_stream_bubble()
                )

            self._set_stream_text(text)

            self._scroll_to_bottom()

        elif self._stream_bubble is None:

            # 两条消息之间的"正在输入"

            self._show_typing()


    # =========================
    # 一条发完了：
    # “正在输入”一会儿，
    # 再发下一条，
    # 像真人连发微信
    # =========================

    def _pause_between_messages(self):

        self._stream_paused = True

        self._show_typing()


        delay = random.randint(700, 1500)


        # 15% 概率
        # “打了一半删掉重打”

        if random.random() < 0.15:

            QTimer.singleShot(

                delay,

                self._retype_then_resume

            )

        else:

            QTimer.singleShot(

                delay,

                self._resume_stream

            )


    def _retype_then_resume(self):

        if not self._stream_paused:

            return

        self._hide_typing()

        QTimer.singleShot(

            400,

            self._retype_resume_stream

        )


    def _retype_resume_stream(self):

        if not self._stream_paused:

            return

        self._show_typing()

        QTimer.singleShot(

            700,

            self._resume_stream

        )


    def _resume_stream(self):

        if not self._stream_paused:

            return

        self._stream_paused = False

        # 停顿期间攒下的内容
        # 继续写进气泡

        self._pump_stream()

        self._scroll_to_bottom()


        # 思考线程已经给完全部内容，
        # 且缓冲也发完了，才收尾

        if (

            self._stream_finished

            and not self._stream_paused

        ):

            self._finish_stream()


    def _set_stream_text(self, text):

        text = text.strip()

        if not text:

            return

        if self._stream_bubble is None:

            self._stream_bubble = (
                self._new_stream_bubble()
            )

        self._stream_bubble.update_text(
            text
        )


    def _new_stream_bubble(self):

        bubble = self.add_message(
            "…", "Echo"
        )

        self._stream_bubbles.append(
            bubble
        )

        return bubble


    # =========================
    # Echo回复到达
    # =========================

    def on_think_result(self, response):

        # 完整回复落盘一次，
        # 不按气泡拆分

        self.conversations.add_message(
            "echo",
            response
        )


        self._stream_response = response

        self._stream_finished = True


        if self._stream_paused:

            # 还在两条消息之间的停顿里，
            # 让停顿自然走完，
            # 剩下的由 _resume_stream 收尾

            return


        if (

            self._stream_bubble is None

            and not self._stream_buffer.strip()

        ):

            # 流式没产出任何内容
            # （兼容意外情况），走老路

            self._deliver_reply(response)

            self._restore_input()

        else:

            self._finish_stream()


    def _finish_stream(self):

        # 收尾：缓冲里剩余的内容
        # 统一按分隔符/句子切开，
        # 第一段并入当前气泡，
        # 其余按打字节奏逐条补发，
        # 不会一股脑全弹出来

        parts = []

        if self._stream_buffer.strip():

            parts = split_reply(
                self._stream_buffer
            )


        if parts:

            if self._stream_bubble is not None:

                self._stream_bubble.update_text(
                    parts[0]
                )

            else:

                self._set_stream_text(
                    parts[0]
                )


            if len(parts) > 1:

                self.pending_parts = (
                    parts[1:]
                )

                QTimer.singleShot(

                    600,

                    self._deliver_next

                )


        self._hide_typing()

        self._stream_buffer = ""

        self._stream_bubble = None

        self._stream_finished = False

        self._stream_response = None

        self._stream_bubbles = []


        self._restore_input()


    def on_think_error(self, error):

        self._hide_typing()

        self._stream_buffer = ""

        self._stream_bubble = None

        self._stream_paused = False

        self._stream_finished = False

        self._stream_response = None

        self._stream_bubbles = []

        self.add_message(

            tr("出错了：%s") % error,

            "系统"

        )

        self._restore_input()


    def _restore_input(self):

        self.input_box.setEnabled(True)

        self.send_button.setEnabled(True)

        self.input_box.setFocus()


    # =========================
    # 气泡右键菜单
    # =========================

    def _bubble_context_menu(
        self,
        bubble,
        global_pos
    ):


        menu = QMenu(self)


        act_copy = menu.addAction(
            tr("复制")
        )


        # 重新生成只对她
        # 刚说完的这组回复开放：
        # 之前的回复后面已经有
        # 新对话了，撤不得

        act_regen = None

        if (

            bubble.sender == "Echo"

            and bubble in (
                self._trailing_echo_bubbles()
            )

        ):

            act_regen = menu.addAction(
                tr("重新生成")
            )


        chosen = menu.exec(global_pos)


        if chosen is act_copy:

            QGuiApplication.clipboard(
            ).setText(
                bubble.message or ""
            )


        elif chosen is act_regen:

            self.regenerate_last_reply()



    # =========================
    # 结尾那组她的回复气泡
    #
    # 从布局末尾往前收，
    # 碰到非 Echo 气泡或分隔条就停——
    # 一条回复可能拆成好几个气泡
    # （连发/流式），要一组的才算数
    # =========================

    def _trailing_echo_bubbles(self):


        found = []

        layout = (
            self.message_layout
        )


        for i in range(

            layout.count() - 1,
            -1,
            -1,

        ):

            item = layout.itemAt(i)

            w = (
                item.widget()
                if item else None
            )


            if not isinstance(
                w, MessageBubble
            ):

                break


            if w.sender != "Echo":

                break


            found.append(w)


        found.reverse()

        return found



    # =========================
    # 删掉末尾气泡后，
    # 把归组状态指回
    # 真正的最后一条
    # =========================

    def _recompute_last_bubble(self):


        self._last_bubble = None

        self._last_sender = None

        layout = (
            self.message_layout
        )


        for i in range(

            layout.count() - 1,
            -1,
            -1,

        ):

            item = layout.itemAt(i)

            w = (
                item.widget()
                if item else None
            )


            if not isinstance(
                w, MessageBubble
            ):

                continue


            if w.sender == "系统":

                # 系统消息打断归组

                break


            self._last_bubble = w

            self._last_sender = (
                w.sender
            )

            break



    # =========================
    # 重新生成她刚说的这句
    #
    # 聊天记录里删掉旧回复、
    # 界面上撤掉旧气泡，
    # 然后拿同一句话重想。
    # 大脑侧复用上一轮的 prompt，
    # 关系计数和记忆入库
    # 不会多算一遍。
    #
    # 已知取舍：被丢弃的那句回复
    # 在说话后已经做过一次回看和
    # 自述入库，那边不做撤销——
    # 回看系统本来就会盯编造。
    # =========================

    def regenerate_last_reply(self):


        # 她正在说话/还有气泡
        # 在排队时不接客

        if self._echo_busy():

            return


        if self.brain is None:

            self._init_brain()


        if self.brain is None:

            return


        recent = (
            self.conversations
            .get_recent(2)
        )


        # 记录里最后一条是她说的、
        # 前一条是他说的，
        # 才有"重说"这回事

        if (

            len(recent) < 2

            or recent[-1].get("role")
                != "echo"

            or recent[-2].get("role")
                != "user"

        ):

            return


        user_message = (
            recent[-2].get("content")
        )


        if not user_message:

            return


        if (
            self.conversations
            .remove_last_echo()
            is None
        ):

            return


        for old in (
            self._trailing_echo_bubbles()
        ):

            self.message_layout.removeWidget(
                old
            )

            old.deleteLater()


        self._recompute_last_bubble()



        # 流式状态清零，
        # 和 send_message 一致

        self._stream_buffer = ""

        self._stream_bubble = None

        self._stream_paused = False

        self._stream_finished = False

        self._stream_response = None

        self._stream_bubbles = []


        self.input_box.setEnabled(
            False
        )

        self.send_button.setEnabled(
            False
        )


        QTimer.singleShot(

            400,

            self._maybe_show_typing

        )


        self.think_worker = ThinkWorker(

            self.brain,

            user_message,

            regenerate=True,

        )


        self.think_worker.chunk.connect(
            self._on_chunk
        )

        self.think_worker.result.connect(
            self.on_think_result
        )

        self.think_worker.error.connect(
            self.on_think_error
        )

        self.think_worker.start()


    # =========================
    # 聊天记录搜索（Ctrl+F）
    # =========================

    def retranslate(self):

        """
        语言切换时被调：
        把自己身上的文字当场换掉。
        已在屏幕上的消息内容不动
        （那是聊天内容，不是界面文字）。
        """

        self.send_button.setText(
            tr("发送")
        )

        self.input_box.setPlaceholderText(
            tr("和她说点什么...")
        )

        if (
            self._search_dialog
            is not None
        ):

            self._search_dialog.close()

            self._search_dialog = None


    # =========================
    # 换主题：
    # 样式全部从 _chat_style /
    # _bottom_bar_style 出，
    # 这里重上一遍；
    # 消息区里每个气泡、分隔条、
    # 正在输入气泡各自有 retheme
    # =========================

    def _chat_style(self):

        t = self.theme

        return f"""
        QWidget {{
            background-color:{t['window_bg']};
            color:{t['bubble_in_text']};
        }}

        QLineEdit {{
            background-color:{t['input_bg']};
            border:1px solid {t['input_border']};
            border-radius:8px;
            padding:10px 14px;
            font-size:15px;
            color:{t['input_text']};
        }}

        QLineEdit:focus {{
            border:1px solid {t['input_focus_border']};
        }}

        QPushButton#sendButton {{
            background:{t['send_bg']};
            color:{t['send_text']};
            border:none;
            border-radius:8px;
            padding:10px 24px;
            font-size:15px;
        }}

        QPushButton#sendButton:disabled {{
            background:{t['send_disabled']};
        }}

        QPushButton#sendButton:hover {{
            background:{t['send_hover']};
        }}

        QScrollArea {{
            border:none;
        }}
        """


    def _bottom_bar_style(self):

        t = self.theme

        return f"""
        QWidget#bottomBar {{
            background-color:{t['inputbar_bg']};
            border-top:1px solid {t['inputbar_border']};
        }}
        """


    def retheme(self):

        self.theme = get_theme()

        self.setStyleSheet(
            self._chat_style()
        )

        self.message_widget.setStyleSheet(
            f"background-color:"
            f"{self.theme['chat_bg']};"
        )

        self.bottom_bar.setStyleSheet(
            self._bottom_bar_style()
        )


        layout = (
            self.message_layout
        )

        for i in range(
            layout.count()
        ):

            item = layout.itemAt(i)

            w = (
                item.widget()
                if item else None
            )

            if w is None:

                continue

            retheme = getattr(
                w, "retheme", None
            )

            if retheme:

                retheme()


    def _open_search(self):


        if self._search_dialog is None:

            self._search_dialog = (
                ChatSearchDialog(

                    fetch_records=(
                        self.conversations
                        .get_all
                    ),

                    on_jump=(
                        self
                        ._jump_to_record
                    ),

                    parent=self,

                )
            )


        self._search_dialog.show()

        self._search_dialog.raise_()

        self._search_dialog.activateWindow()

        self._search_dialog.search_box.setFocus()

        self._search_dialog.search_box.selectAll()


    # =========================
    # 双击搜索结果：
    # 聊天里滚到那条气泡
    # =========================

    def _jump_to_record(self, record):


        sender = {

            "user": "我",

            "echo": "Echo",

        }.get(record.get("role"))


        content = str(
            record.get("content") or ""
        )


        layout = self.message_layout


        for i in range(

            layout.count() - 1,
            -1,
            -1,

        ):

            w = (
                layout.itemAt(i)
                .widget()
            )


            if (

                isinstance(
                    w, MessageBubble
                )

                and w.sender == sender

                and (
                    w.message or ""
                ) == content

            ):

                self.scroll_area.ensureWidgetVisible(
                    w
                )

                # 闪一下，
                # 不然滚过去也找不到是哪条

                w.fade_in()

                return


        # 找不到：比界面加载的
        # 历史更早，或已被撤掉

        if self._search_dialog:

            self._search_dialog.set_hint(
                tr("这条不在当前显示的范围里"
                "（更早或已重新生成），"
                "用「导出」能看全文")
            )


    # =========================
    # 导出聊天记录（顶栏按钮）
    # =========================

    def export_chat(self):


        records = (
            self.conversations
            .get_all()
        )


        default_name = (

            "Echo聊天记录-"

            + datetime.now().strftime(
                "%Y%m%d"
            )

            + ".txt"
        )


        path, _ = QFileDialog.getSaveFileName(

            self,

            tr("导出聊天记录"),

            default_name,

            tr("文本文件 (*.txt)"),

        )


        if not path:

            return


        sender_of = {

            "user": "我",

            "echo": "Echo",

        }


        lines = [

            "# EchoLover 聊天记录",

            "# 共 %d 条 · 导出于 %s"
            % (
                len(records),
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            ),

            "",

        ]


        for r in records:

            lines.append(

                "[%s] %s"
                % (
                    r.get("time", ""),
                    sender_of.get(
                        r.get("role"),
                        r.get("role"),
                    ),
                )

            )

            lines.append(
                str(
                    r.get("content")
                    or ""
                )
            )

            lines.append("")


        try:

            with open(
                path,
                "w",
                encoding="utf-8",
            ) as f:

                f.write(
                    "\n".join(lines)
                )

        except OSError as e:

            self.add_message(
                tr("导出失败：%s") % e,
                "系统",
            )

            return


        self.add_message(
            tr("聊天记录已导出到：%s")
            % path,
            "系统",
        )



    # =========================
    # 当前场景：
    # 他是不是正在打字？
    # 她是不是正在说话？
    # =========================

    def _echo_busy(self, include_proactive=True):

        """
        include_proactive=False 用在
        主动消息回到的那一刻：
        信号是那个 worker 自己发的，
        它还没退出，
        把自己算成"她在说话"
        会把每一条主动消息都误杀。
        """

        if (

            self.think_worker is not None

            and self.think_worker.isRunning()

        ):

            return True

        if (

            include_proactive

            and self.proactive_worker
            is not None

            and self.proactive_worker
            .isRunning()

        ):

            return True

        # 还有气泡排队等着往外发

        if self.pending_parts:

            return True

        # “正在输入”还亮着

        if self.typing_bubble is not None:

            return True

        return False


    def _ui_state(self):

        return {

            # 输入框里有没发出去的内容，
            # 说明他正打算说话

            "user_typing": bool(

                self.input_box.text().strip()

            ),

            "echo_busy": self._echo_busy(),

        }


    # =========================
    # 主动消息检查
    # =========================

    def check_proactive(self):

        if self.brain is None:

            return


        # 这一轮到底该不该开口，
        # 守门人说了算：
        # 深夜、他在打字、她正在说话、
        # 冷却没走完，都会直接否掉

        try:

            allowed, reason = (
                self.guard.should_attempt(
                    self._ui_state()
                )
            )

        except Exception as e:

            print(
                "守门人判断失败（跳过）:",
                e
            )

            return

        if not allowed:

            print(
                "主动消息：",
                reason
            )

            return


        self.proactive_worker = (
            ProactiveWorker(

                self.brain,

                # 把最近用旧的画面告诉她，
                # 让她避开

                avoid_imagery=list(

                    self.guard
                    .fresh_imagery()
                    .keys()

                ),

            )
        )

        self.proactive_worker.message_ready.connect(
            self.on_proactive_message
        )

        self.proactive_worker.start()


    def on_proactive_message(self, payload):

        payload = payload or {}

        message = (
            payload.get("text") or ""
        ).strip()

        follow_ups = (
            payload.get("follow_ups") or []
        )

        if not message:

            return


        # =========================
        # 想一句话要十几秒，
        # 这期间他可能已经开始打字了。
        # 场景要重新确认一次。
        # =========================

        allowed, reason = (
            self.guard.should_attempt(
                {

                    "user_typing": bool(

                        self.input_box
                        .text()
                        .strip()

                    ),

                    "echo_busy":
                        self._echo_busy(

                            include_proactive=(
                                False
                            )

                        ),

                }
            )
        )

        if not allowed:

            print(
                "主动消息已丢弃：",
                reason
            )

            return


        # =========================
        # 内容审核：
        # 意象是不是刚用过、
        # 有没有乱引用过去的约定
        # =========================

        passed, reason = (
            self.guard.screen(
                message, follow_ups
            )
        )

        if not passed:

            print(
                "主动消息未通过审核，"
                "已丢弃（" + reason + "）：",
                message
            )

            return


        # 真的要发出去了，
        # 才记下冷却和用过的意象

        self.guard.note_proactive_sent(
            message
        )


        # 话茬问过了就不再问。
        # 只标这句话实际问到的那几条，
        # 没问到的留着下次再问

        try:

            used = (

                self.brain.scheduler
                .used_follow_ups(
                    message, follow_ups
                )

            )

            (
                self.brain.scheduler
                .mark_follow_ups_asked(
                    used
                )
            )

        except Exception:

            pass


        # 她主动开口前，
        # 也是先“正在输入”一会儿

        self._show_typing()

        QTimer.singleShot(

            1200,

            lambda: self._deliver_proactive(
                message, follow_ups
            )

        )


    def _deliver_proactive(
        self, message, follow_ups=None
    ):

        self._hide_typing()

        # 主动消息同样落盘，
        # 并通知主窗口（托盘提醒）

        self.conversations.add_message(
            "echo",
            message
        )

        self.proactive_received.emit(
            message
        )

        # 主动消息没人递话，
        # 最容易凭空编 —
        # 发出去后照样过一遍回看，
        # 错了留便签给下一句找补

        try:

            self._reflection_worker = (
                ReflectionWorker(

                    self.brain,
                    message,
                    follow_ups,

                )
            )

            self._reflection_worker.start()

        except Exception as e:

            print(
                "回看线程启动失败（跳过）:",
                e
            )

        self._deliver_reply(message)
