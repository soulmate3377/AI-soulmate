from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from ui.main_window import MainWindow

from core.runlock import acquire as lock_acquire

from ui.i18n import tr

import sys




def main():


    # =========================
    # No double launch: desktop and the phone service share one
    # SoulmateData, and two instances at once overwrite each other's
    # chat log and swallow messages, so the second one is refused.
    # 防双开：桌面版和手机端服务共用同一份 SoulmateData，
    # 同时开会互相覆盖聊天记录、把消息弄丢，所以第二个来的
    # 直接拒绝启动。
    # =========================

    ok, running = lock_acquire(
        "desktop"
    )

    if not ok:

        app = QApplication(
            sys.argv
        )

        from PySide6.QtWidgets import (
            QMessageBox
        )

        QMessageBox.critical(
            None,
            "Soulmate",
            tr("%s 已经在运行了。\n\n"
            "Soulmate 同时只能开一个"
            "（同时开会互相覆盖聊天记录）。\n"
            "先把正在用的那个关掉，"
            "再重新打开。") % running,
        )

        sys.exit(1)


    # =========================
    # create the app
    # 创建应用

    app = QApplication(
        sys.argv
    )



    # =========================
    # global font setup
    # 全局字体设置

    font = QFont()


    # Chinese font / 中文字体

    font.setFamily(
        "Microsoft YaHei"
    )


    # font size / 字号

    font.setPointSize(
        10
    )


    # normal weight; WeChat look, no global bold / 常规字重，微信风格不用全局加粗

    font.setBold(
        False
    )


    app.setFont(
        font
    )



    # =========================
    # create the Soulmate window
    # 创建 Soulmate 窗口

    window = MainWindow()



    # =========================
    # Startup order: a first run (no language picked yet or
    # onboarding unfinished) goes through the language picker and
    # the setup wizard first; only then does the main window show.
    # 启动顺序：第一次用（没选过语言或没引导完）先走语言选择和
    # 设置向导，全部完成后主界面才出现；日常启动直接进主界面。
    # =========================

    window.start()



    # =========================
    # enter the event loop
    # 进入事件循环

    sys.exit(
        app.exec()
    )





if __name__ == "__main__":

    main()