from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from ui.main_window import MainWindow

from core.runlock import acquire as lock_acquire

from ui.i18n import tr

import sys




def main():


    # =========================
    # 防双开：
    # 桌面版和手机端服务共用
    # 同一份 EchoData，
    # 同时开聊天记录会互相
    # 覆盖丢消息。
    # 第二个来的直接拒绝启动。
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
            "EchoLover",
            tr("%s 已经在运行了。\n\n"
            "EchoLover 同时只能开一个"
            "（同时开会互相覆盖聊天记录）。\n"
            "先把正在用的那个关掉，"
            "再重新打开。") % running,
        )

        sys.exit(1)


    # =========================
    # 创建应用
    # =========================

    app = QApplication(
        sys.argv
    )



    # =========================
    # 全局字体设置
    # =========================

    font = QFont()


    # 中文字体

    font.setFamily(
        "Microsoft YaHei"
    )


    # 字号

    font.setPointSize(
        10
    )


    # 常规字重，微信风格不用全局加粗

    font.setBold(
        False
    )


    app.setFont(
        font
    )



    # =========================
    # 创建EchoLover窗口
    # =========================

    window = MainWindow()



    # =========================
    # 启动顺序：
    # 第一次用（没选过语言/没引导完）
    # 先语言选择 + 设置向导，
    # 全部完成后主界面才出现；
    # 日常启动直接进主界面。
    # =========================

    window.start()



    # =========================
    # 进入事件循环
    # =========================

    sys.exit(
        app.exec()
    )





if __name__ == "__main__":

    main()