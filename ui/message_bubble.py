import os

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QSizePolicy,
    QGraphicsOpacityEffect
)

from PySide6.QtCore import (
    Qt,
    QPropertyAnimation
)

from PySide6.QtGui import QPixmap

from core.identity import Identity

from core.paths import resolve_asset

from ui.theme import get_theme
from ui.i18n import tr


# ==================================================
# 消息气泡
# Echo：左侧气泡 + 头像
# 我：  右侧气泡 + 头像
# 系统： 居中淡色小字
# 颜色全部来自 ui/theme.py 的当前主题
#
# 连续消息（同一个人、3 分钟内、中间没人插话）
# 共用一个头像：
# 后续气泡不画头像、
# 缩进到头像列右侧、
# 间距收紧。
# 不这么做的话，她连发的四句
# 在界面上就是四个一模一样的方块。
# ==================================================

# 头像 38px + 间距 10px，
# 后续气泡缩进这么多才能对齐

GROUP_INDENT = 48


class MessageBubble(QWidget):


    # Echo头像缓存：
    # 按 路径+修改时间 做签名，
    # 设置里换过头像后
    # 新气泡立即用新头像

    _echo_avatar = None

    _echo_avatar_sig = None


    def __init__(
        self,
        message,
        sender="Echo",
        grouped=False
    ):

        super().__init__()


        self.message = message

        self.sender = sender

        self.theme = get_theme()

        # 右键菜单回调，
        # 由 chat_widget 接管具体菜单

        self.on_context_menu = None

        # 这一条是不是
        # 上一同一人的续句

        self.grouped = grouped

        # 靠头像那一侧的下圆角：
        # 组内中间的气泡要抹平，
        # 组里最后一条才收圆。
        # 建的时候先乐观当成最后一条，
        # 后面真接了续句再抹平。

        self._tail_bottom = "14px"

        self._top_margin = 2 if grouped else 5

        self._bottom_margin = 5

        self.init_ui()


    # =========================
    # 加载Echo头像
    # =========================

    @classmethod
    def _load_echo_avatar(cls):

        path = Identity().get(
            "avatar"
        )


        resolved = (
            resolve_asset(path)
            if path else None
        )


        sig = None

        if resolved and os.path.exists(
            resolved
        ):

            try:

                sig = (
                    resolved,
                    os.path.getmtime(resolved)
                )

            except OSError:

                sig = (resolved, 0)


        if sig == cls._echo_avatar_sig:

            return cls._echo_avatar


        cls._echo_avatar_sig = sig

        cls._echo_avatar = None


        if resolved:

            pixmap = QPixmap(resolved)

            if not pixmap.isNull():

                cls._echo_avatar = pixmap


        return cls._echo_avatar



    # =========================
    # 生成头像控件
    # =========================

    def _make_avatar(self):


        t = self.theme

        radius = t["avatar_radius"]


        avatar = QLabel()

        avatar.setFixedSize(38, 38)

        avatar.setAlignment(Qt.AlignCenter)


        if self.sender == "我":

            avatar.setText(tr("我"))

            avatar.setStyleSheet(
                f"""
                QLabel {{
                    background-color:{t['avatar_out_bg']};
                    color:{t['avatar_out_text']};
                    border-radius:{radius}px;
                    font-size:15px;
                }}
                """
            )


        else:

            pixmap = (
                self._load_echo_avatar()
            )

            if pixmap:

                avatar.setPixmap(

                    pixmap.scaled(

                        38,

                        38,

                        Qt.KeepAspectRatio,

                        Qt.SmoothTransformation

                    )

                )

                avatar.setStyleSheet(
                    f"QLabel {{ "
                    f"border-radius:{radius}px; }}"
                )

            else:

                avatar.setText("Echo")

                avatar.setStyleSheet(
                    f"""
                    QLabel {{
                        background-color:{t['avatar_in_bg']};
                        color:{t['bubble_out_text']};
                        border-radius:{radius}px;
                        font-size:12px;
                    }}
                    """
                )


        return avatar



    def init_ui(self):


        t = self.theme


        # 气泡标签引用，
        # 流式输出时要更新文字

        self.bubble_label = None


        # ---------------------
        # 系统消息：居中淡色小字
        # ---------------------

        if self.sender == "系统":

            layout = QHBoxLayout()

            label = QLabel(self.message)

            self.bubble_label = label

            label.setAlignment(Qt.AlignCenter)

            label.setWordWrap(True)

            label.setStyleSheet(
                f"""
                QLabel {{
                    color:{t['system_color']};
                    font-size:12px;
                    padding:4px;
                    background:transparent;
                }}
                """
            )

            layout.addWidget(label)

            self.setLayout(layout)

            return



        main_layout = QHBoxLayout()

        main_layout.setContentsMargins(

            14,

            self._top_margin,

            14,

            self._bottom_margin

        )

        main_layout.setSpacing(10)


        # ---------------------
        # 气泡本体
        # 不对称圆角：
        # 靠近头像的角收小，
        # 是聊天气泡的经典细节
        # ---------------------

        bubble = QLabel(self.message)

        self.bubble_label = bubble

        bubble.setWordWrap(True)

        bubble.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )


        font = bubble.font()

        font.setPointSize(11)

        font.setBold(False)

        bubble.setFont(font)


        bubble.setMaximumWidth(520)

        bubble.setSizePolicy(
            QSizePolicy.Maximum,
            QSizePolicy.Minimum
        )


        bubble.setStyleSheet(
            self._bubble_style()
        )


        # ---------------------
        # 我的消息：右侧
        # ---------------------

        if self.sender == "我":

            main_layout.addStretch()

            main_layout.addWidget(
                bubble
            )

            if self.grouped:

                main_layout.addSpacing(
                    GROUP_INDENT
                )

            else:

                main_layout.addWidget(

                    self._make_avatar(),

                    0,

                    Qt.AlignTop

                )


        # ---------------------
        # Echo消息：左侧
        # ---------------------

        else:

            if self.grouped:

                main_layout.addSpacing(
                    GROUP_INDENT
                )

            else:

                main_layout.addWidget(

                    self._make_avatar(),

                    0,

                    Qt.AlignTop

                )

            main_layout.addWidget(
                bubble
            )

            main_layout.addStretch()



        self.setLayout(
            main_layout
        )


    # =========================
    # 气泡配色与圆角
    # =========================

    def _bubble_style(self):

        t = self.theme

        r = "14px"

        # 靠头像那一侧的角：
        # 我的是右上角，Echo 的是左上角

        tail = "4px"


        if self.sender == "我":

            bg = t["bubble_out_bg"]

            fg = t["bubble_out_text"]

            border = ""

            corners = (
                f"border-top-left-radius:{r};"
                f"border-top-right-radius:{tail};"
                f"border-bottom-right-radius:"
                f"{self._tail_bottom};"
                f"border-bottom-left-radius:{r};"
            )

        else:

            bg = t["bubble_in_bg"]

            fg = t["bubble_in_text"]

            border = (
                f"border:1px solid "
                f"{t['bubble_in_border']};"
            )

            corners = (
                f"border-top-right-radius:{r};"
                f"border-top-left-radius:{tail};"
                f"border-bottom-left-radius:"
                f"{self._tail_bottom};"
                f"border-bottom-right-radius:{r};"
            )


        return (
            f"""
            QLabel {{
                background-color:{bg};
                color:{fg};
                {border}
                {corners}
                padding:10px 14px;
            }}
            """
        )


    # =========================
    # 组的边界：
    # is_last=True  这条是连发的最后一句，
    #               下圆角收回 14px、下边距恢复正常
    # is_last=False 后面还跟着同一人的话，
    #               下圆角抹平、下边距归零
    #
    # 只有在气泡建好之后才知道后面还有没有，
    # 所以由 ChatWidget 回头来改
    # =========================

    def set_group_edge(self, is_last):

        if self.sender == "系统":

            return

        if is_last:

            self._tail_bottom = "14px"

            self._bottom_margin = 5

        else:

            self._tail_bottom = "4px"

            self._bottom_margin = 0


        layout = self.layout()

        if layout is not None:

            layout.setContentsMargins(

                14,

                self._top_margin,

                14,

                self._bottom_margin

            )


        if self.bubble_label is not None:

            self.bubble_label.setStyleSheet(
                self._bubble_style()
            )


    # =========================
    # 入场动效：
    # 淡入 140ms
    #
    # 动画对象必须挂在 self 上，
    # 否则函数一返回就被回收，
    # 动画放一半就没了
    # =========================

    def fade_in(self, duration=140):

        effect = QGraphicsOpacityEffect(self)

        self.setGraphicsEffect(effect)

        anim = QPropertyAnimation(
            effect, b"opacity", self
        )

        anim.setStartValue(0.0)

        anim.setEndValue(1.0)

        anim.setDuration(duration)

        anim.finished.connect(
            self._clear_fade
        )

        # 引用留住
        self._fade_effect = effect
        self._fade_anim = anim

        anim.start()


    def _clear_fade(self):

        # 放完就拆掉特效层：
        # 八十条历史气泡各挂一个
        # QGraphicsOpacityEffect 不划算

        self.setGraphicsEffect(None)

        self._fade_effect = None

        self._fade_anim = None


    # =========================
    # 流式输出时更新气泡文字
    # =========================

    def update_text(self, text):

        self.message = text

        if self.bubble_label is not None:

            self.bubble_label.setText(text)


    # =========================
    # 右键：交给 chat_widget
    # 弹菜单（复制/重新生成）
    # =========================

    def contextMenuEvent(self, event):

        if self.on_context_menu is not None:

            self.on_context_menu(
                self,
                event.globalPos(),
            )
