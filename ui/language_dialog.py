# ui/language_dialog.py
# First-run language pick. Pops up before the main window: language first,
# then the setup wizard, then the main UI.
# 首次启动的语言选择。主界面之前弹：先选语言，再走设置向导，最后才是主界面。
# The dialog itself is bilingual because the user's language is unknown yet,
# so both labels are hardcoded on the buttons.
# 窗口本身中英双语：还不知道用户语言，所以两种文案都写死在按钮上。

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
            "Soulmate"
        )

        self.setModal(True)

        self.setFixedWidth(360)


        layout = QVBoxLayout()

        layout.setSpacing(16)


        title = QLabel("Soulmate")

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
