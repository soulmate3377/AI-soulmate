from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QWidget,
    QMessageBox
)

from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from core.identity import Identity
from core.paths import resolve_asset
from memory.long_memory import LongMemory

from ui.settings_window import (
    KeyTestWorker,
    PROVIDER_PRESETS,
    load_api_key,
    save_api_key,
)

from ui.theme import get_theme
from ui.i18n import tr, her_name
from ui import i18n

from core.storage import load_config


# ==================================================
# 首次启动引导
#
# 三步：欢迎 → API Key → 互相认识
# 完成后在 config.json 写入
# onboarded=True，不再出现
# ==================================================

class OnboardingDialog(QDialog):


    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle(tr("欢迎使用 EchoLover"))

        self.setModal(True)

        self.resize(440, 420)


        self.key_tester = None


        self.stack = QStackedWidget()

        self.stack.addWidget(
            self._build_welcome()
        )

        self.stack.addWidget(
            self._build_key_page()
        )

        self.stack.addWidget(
            self._build_name_page()
        )

        self.stack.addWidget(
            self._build_life_page()
        )


        layout = QVBoxLayout()

        layout.addWidget(self.stack)

        self.setLayout(layout)


        t = get_theme()


        self.setStyleSheet(
            f"""
            QWidget{{
                background:{t['window_bg']};
                color:{t['bubble_in_text']};
            }}
            QLabel{{
                font-size:15px;
            }}
            QLabel#title{{
                font-size:22px;
                font-weight:bold;
            }}
            QLabel#desc{{
                font-size:14px;
                color:{t['status_color']};
            }}
            QLineEdit,QComboBox{{
                background:{t['input_bg']};
                border:1px solid {t['input_border']};
                border-radius:8px;
                padding:8px;
                font-size:15px;
                color:{t['input_text']};
            }}
            QPushButton{{
                background:{t['send_bg']};
                color:{t['send_text']};
                border:none;
                border-radius:8px;
                padding:10px;
                font-size:15px;
                font-weight:bold;
            }}
            QPushButton:hover{{
                background:{t['send_hover']};
            }}
            QPushButton#secondary{{
                background:transparent;
                color:{t['hint_color']};
                font-weight:normal;
            }}
            QPushButton#secondary:hover{{
                color:{t['send_bg']};
            }}
            QPushButton#testButton{{
                background:{t['input_bg']};
                color:{t['send_bg']};
                border:1px solid {t['send_bg']};
                padding:8px 14px;
                font-size:13px;
            }}
            """
        )


    # =====================
    # 第 1 页：欢迎
    # =====================

    def _build_welcome(self):

        page = QWidget()

        layout = QVBoxLayout()

        layout.setContentsMargins(
            36, 30, 36, 30
        )

        layout.setSpacing(14)


        avatar = QLabel()

        avatar.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(
            resolve_asset(
                "assets/avatar/echo_avatar.png"
            )
        )

        if not pixmap.isNull():

            avatar.setPixmap(

                pixmap.scaled(
                    110, 110,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

            )

        layout.addWidget(avatar)


        title = QLabel(tr("你好，我是 Echo"))

        title.setObjectName("title")

        title.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)


        desc = QLabel(

            tr("一个住在你电脑里的伙伴。\n"
            "她会记得你说过的话，\n"
            "也会在你忙碌时安静陪着你。\n\n"
            "开始之前，先做两件小事。")

        )

        desc.setObjectName("desc")

        desc.setAlignment(Qt.AlignCenter)

        layout.addWidget(desc)


        layout.addStretch()


        start = QPushButton(tr("开始"))

        start.clicked.connect(

            lambda: self.stack.setCurrentIndex(1)

        )

        layout.addWidget(start)


        page.setLayout(layout)

        return page


    # =====================
    # 第 2 页：API Key
    # =====================

    def _build_key_page(self):

        page = QWidget()

        layout = QVBoxLayout()

        layout.setContentsMargins(
            36, 30, 36, 30
        )

        layout.setSpacing(12)


        title = QLabel(tr("先让我能开口说话"))

        title.setObjectName("title")

        layout.addWidget(title)


        desc = QLabel(

            tr("我通过大模型思考，"
            "需要一个 API Key。\n"
            "默认走 DeepSeek"
            "（platform.deepseek.com "
            "免费注册就能拿到），"
            "想用 Kimi、智谱这些别家，"
            "之后在右上角设置里换。")

        )

        desc.setObjectName("desc")

        desc.setWordWrap(True)

        layout.addWidget(desc)


        # 已保存过就回填

        saved = load_api_key()


        row = QHBoxLayout()

        self.key_input = QLineEdit()

        self.key_input.setEchoMode(
            QLineEdit.Password
        )

        self.key_input.setPlaceholderText(
            "sk-..."
        )

        if saved:

            self.key_input.setText(saved)

        row.addWidget(self.key_input)


        self.test_button = QPushButton(
            tr("测试连接")
        )

        self.test_button.setObjectName(
            "testButton"
        )

        self.test_button.clicked.connect(
            self._test_key
        )

        row.addWidget(self.test_button)

        layout.addLayout(row)


        self.key_status = QLabel("")

        self.key_status.setWordWrap(True)

        layout.addWidget(self.key_status)


        layout.addStretch()


        next_button = QPushButton(tr("下一步"))

        next_button.clicked.connect(
            self._key_next
        )

        layout.addWidget(next_button)


        skip = QPushButton(tr("暂不设置"))

        skip.setObjectName("secondary")

        skip.clicked.connect(

            lambda: self.stack.setCurrentIndex(2)

        )

        layout.addWidget(skip)


        page.setLayout(layout)

        return page


    def _key_next(self):

        if not self.key_input.text().strip():

            QMessageBox.information(

                self,
                tr("还没有 Key"),

                tr("没有 Key 我暂时没法回应你。\n"
                "也可以点「暂不设置」，"
                "之后在右上角设置里再填。")

            )

            return

        self.stack.setCurrentIndex(2)


    def _test_key(self):

        key = self.key_input.text().strip()

        if not key:

            self.key_status.setText(
                "先粘贴 API Key 再测试"
            )

            self.key_status.setStyleSheet(

                f"color:"
                f"{get_theme()['error_color']};"
                f"font-size:13px;"

            )

            return


        self.test_button.setEnabled(False)

        self.key_status.setText(
            "正在测试连接..."
        )

        self.key_status.setStyleSheet(

            f"color:"
            f"{get_theme()['hint_color']};"
            f"font-size:13px;"

        )


        self.key_tester = KeyTestWorker(

            key,

            # 引导页只做默认服务商的检查，
            # 换服务商在设置页里测

            PROVIDER_PRESETS[
                "DeepSeek（默认）"
            ]["api_base"],

        )

        self.key_tester.ok.connect(
            self._on_test_ok
        )

        self.key_tester.fail.connect(
            self._on_test_fail
        )

        self.key_tester.start()


    def _on_test_ok(self):

        self.test_button.setEnabled(True)

        self.key_status.setText(
            "✓ 连接成功，Key 有效"
        )

        self.key_status.setStyleSheet(

            f"color:"
            f"{get_theme()['ok_color']};"
            f"font-size:13px;"

        )


    def _on_test_fail(self, error):

        self.test_button.setEnabled(True)

        short = error.replace(
            "\n", " "
        )[:120]

        self.key_status.setText(
            "✗ 连接失败：" + short
        )

        self.key_status.setStyleSheet(

            f"color:"
            f"{get_theme()['error_color']};"
            f"font-size:13px;"

        )


    # =====================
    # 第 3 页：认识一下
    # =====================

    def _build_name_page(self):

        page = QWidget()

        layout = QVBoxLayout()

        layout.setContentsMargins(
            36, 30, 36, 30
        )

        layout.setSpacing(12)


        title = QLabel(tr("认识一下"))

        title.setObjectName("title")

        layout.addWidget(title)


        layout.addWidget(
            QLabel(tr("我该怎么称呼你？"))
        )

        self.user_name_input = QLineEdit()

        self.user_name_input.setPlaceholderText(
            tr("你的名字或昵称")
        )

        layout.addWidget(
            self.user_name_input
        )


        layout.addSpacing(8)


        layout.addWidget(
            QLabel(tr("给我起个名字吧"))
        )

        self.echo_name_input = QLineEdit()

        self.echo_name_input.setText(
                i18n.her_name()
            )

        layout.addWidget(
            self.echo_name_input
        )


        layout.addStretch()


        finish = QPushButton("下一步")

        finish.clicked.connect(

            lambda: self.stack.setCurrentIndex(3)

        )

        layout.addWidget(finish)


        page.setLayout(layout)

        return page


    # =====================
    # 第 4 页：她的来历
    # =====================

    def _build_life_page(self):

        page = QWidget()

        layout = QVBoxLayout()

        layout.setContentsMargins(
            36, 30, 36, 30
        )

        layout.setSpacing(12)


        title = QLabel(tr("她从哪里来"))

        title.setObjectName("title")

        layout.addWidget(title)


        desc = QLabel(

            tr("这些会变成她生活的一部分：\n"
            "填了现居城市她会聊天气，"
            "填了家乡她会记得家乡的事。"
            "都可以留空，由你决定。")

        )

        desc.setObjectName("desc")

        desc.setWordWrap(True)

        layout.addWidget(desc)


        layout.addWidget(QLabel(tr("家乡")))

        self.hometown_input = QLineEdit()

        self.hometown_input.setPlaceholderText(
            tr("比如：成都")
        )

        layout.addWidget(self.hometown_input)


        layout.addWidget(QLabel(tr("现居城市（选填）")))

        self.city_input = QLineEdit()

        self.city_input.setPlaceholderText(
            tr("比如：上海")
        )

        layout.addWidget(self.city_input)


        layout.addWidget(QLabel(tr("她的身份")))

        self.occupation_combo = QComboBox()

        self.occupation_combo.addItems([
            "学生",
            "设计师",
            "程序员",
            "教师",
            "自由职业",
        ])

        layout.addWidget(self.occupation_combo)


        layout.addStretch()


        finish = QPushButton("完成")

        finish.clicked.connect(
            self._finish
        )

        layout.addWidget(finish)


        page.setLayout(layout)

        return page


    # =====================
    # 完成：落盘所有设置
    # =====================

    def _finish(self):

        errors = []


        # API Key 加密保存 +
        # 引导完成标记

        try:

            key = (
                self.key_input.text()
                .strip()
            )

            if key:

                save_api_key(key)

            from core.storage import (
                load_config,
                save_config,
            )

            config = load_config()

            config["onboarded"] = True

            save_config(config)

        except Exception as e:

            errors.append(
                f"API Key 保存失败：{e}"
            )


        # 我的名字

        echo_name = (
            self.echo_name_input.text().strip()
        )

        if echo_name:

            try:

                Identity().update(
                    "echo_name",
                    echo_name
                )

            except Exception as e:

                errors.append(
                    f"名字保存失败：{e}"
                )


        # 她的来历：
        # 家乡 / 现居地 / 身份

        life_fields = {

            "hometown":
                self.hometown_input
                .text().strip(),

            "current_city":
                self.city_input
                .text().strip(),

            "occupation":
                self.occupation_combo
                .currentText(),

        }

        for field, value in (
            life_fields.items()
        ):

            if not value:

                continue

            try:

                Identity().update(
                    field, value
                )

            except Exception as e:

                errors.append(
                    f"来历保存失败：{e}"
                )


        # 用户的称呼，
        # 写进长期记忆画像

        user_name = (
            self.user_name_input.text().strip()
        )

        if user_name:

            try:

                LongMemory().update_profile(
                    "basic",
                    "name",
                    user_name
                )

            except Exception as e:

                errors.append(
                    f"称呼保存失败：{e}"
                )


        if errors:

            QMessageBox.warning(

                self,
                "部分设置保存失败",
                "\n".join(errors)

            )

            return


        self.accept()



# ==================================================
# 是否需要显示引导
# ==================================================

def needs_onboarding():

    return not load_config().get(
        "onboarded"
    )
