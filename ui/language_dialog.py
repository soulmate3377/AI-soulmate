# ui/language_dialog.py
#
# 首次启动的语言选择。
#
# 在主界面出现之前弹：
# 选完语言才进设置向导，
# 向导走完才见主界面。
#
# 这个窗口本身中英双语标注——
# 还不知道用户语言，
# 所以两种都写死在按钮上。

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QPushButton,
)

from PySide6.QtCore import Qt

from ui import i18n



class LanguageDialog(QDialog):


    def __init__(self):

        super().__init__()


        self.setWindowTitle(
            "EchoLover"
        )

        self.setModal(True)

        self.setFixedWidth(360)


        layout = QVBoxLayout()

        layout.setSpacing(16)


        title = QLabel("EchoLover")

        title.setAlignment(
            Qt.AlignCenter
        )

        f = title.font()

        f.setPointSize(20)

        f.setBold(True)

        title.setFont(f)

        layout.addWidget(title)


        desc = QLabel(
            "请选择语言  /  "
            "Choose your language"
        )

        desc.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(desc)


        row = QHBoxLayout()


        for code, label in (

            (i18n.ZH, "中文"),

            (i18n.EN, "English"),

        ):

            btn = QPushButton(label)

            btn.setMinimumHeight(44)

            btn.clicked.connect(

                lambda _=False,
                c=code:
                self._pick(c)

            )

            row.addWidget(btn)


        layout.addLayout(row)


        hint = QLabel(
            "之后可以在设置里更改\n"
            "You can change this "
            "later in Settings"
        )

        hint.setAlignment(
            Qt.AlignCenter
        )

        hint.setStyleSheet(
            "color:#999;font-size:12px;"
        )

        layout.addWidget(hint)


        self.setLayout(layout)



    def _pick(self, code):

        i18n.set_language(code)

        self.accept()
