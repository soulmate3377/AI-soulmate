from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSystemTrayIcon,
    QMenu
)

from PySide6.QtGui import QIcon

from PySide6.QtCore import QTimer


from ui.chat_widget import ChatWidget

from ui.profile_bar import ProfileBar

from ui.settings_window import SettingsWindow

from ui.onboarding import (
    OnboardingDialog,
    needs_onboarding
)

from ui.language_dialog import (
    LanguageDialog,
)

from ui import i18n

from ui.theme import get_theme

from ui.i18n import tr, her_name

from core.paths import resource_path





class MainWindow(QMainWindow):


    def __init__(self):

        super().__init__()



        # =========================
        # 窗口基础设置
        # =========================

        self.setWindowTitle(
            "Soulmate"
        )


        self.resize(
            960,
            540
        )


        # 当前主题

        t = get_theme()



        self.setStyleSheet(
            f"""

            QMainWindow {{

                background-color:{t['window_bg']};

            }}


            QPushButton#settingsButton, QPushButton#topBarButton {{

                background-color:transparent;

                color:{t['settings_color']};

                border:none;

                border-radius:6px;

                padding:8px 14px;

                font-size:14px;

            }}


            QPushButton#settingsButton:hover, QPushButton#topBarButton:hover {{

                background-color:{t['settings_hover']};

            }}

            """
        )



        # =========================
        # 主窗口容器
        # =========================

        central_widget = QWidget()



        main_layout = QVBoxLayout()



        main_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )


        main_layout.setSpacing(
            0
        )



        # =========================
        # 顶部区域
        # =========================

        top_bar = QWidget()


        top_layout = QHBoxLayout()


        top_layout.setContentsMargins(
            15,
            5,
            15,
            5
        )



        # Echo身份栏

        self.profile_bar = ProfileBar()



        top_layout.addWidget(
            self.profile_bar
        )



        top_layout.addStretch()



        # 设置按钮

        self.settings_button = QPushButton(
            "⚙ 设置"
        )

        self.settings_button.setObjectName(
            "settingsButton"
        )


        top_layout.addWidget(
            self.settings_button
        )


        # 导出聊天记录按钮

        self.export_button = QPushButton(
            "⇩ 导出"
        )

        self.export_button.setObjectName(
            "topBarButton"
        )


        top_layout.addWidget(
            self.export_button
        )



        top_bar.setLayout(
            top_layout
        )


        top_bar.setFixedHeight(
            70
        )


        # 顶栏：主题底色 + 底部细分割线

        top_bar.setStyleSheet(
            f"""
            QWidget {{
                background-color:{t['topbar_bg']};
                border-bottom:1px solid {t['topbar_border']};
            }}
            QLabel {{
                border:none;
            }}
            """
        )



        main_layout.addWidget(
            top_bar
        )



        # =========================
        # 聊天区域
        # =========================

        self.chat = ChatWidget()



        main_layout.addWidget(
            self.chat
        )



        # =========================
        # 设置窗口
        # =========================

        self.settings_window = SettingsWindow()



        # 点击打开设置

        self.settings_button.clicked.connect(
            self.open_settings
        )


        # 点击导出聊天记录

        self.export_button.clicked.connect(

            self.chat.export_chat

        )



        # 保存后刷新头像和名字，
        # 并让聊天区立即重试初始化大脑，
        # 填完 Key 不用再重启

        self.settings_window.settings_saved.connect(

            self.profile_bar.refresh

        )


        self.settings_window.settings_saved.connect(

            self.chat.retry_brain

        )


        # 设置页切语言：
        # 整个界面当场换文字

        self.settings_window.language_changed.connect(

            self._apply_language

        )



        # =========================
        # 设置中心组件
        # =========================

        central_widget.setLayout(
            main_layout
        )


        self.setCentralWidget(
            central_widget
        )


        # =========================
        # 她主动说话时，
        # 窗口不在前台就弹系统通知
        # =========================

        self.chat.proactive_received.connect(

            self._notify_proactive

        )


        # =========================
        # 系统托盘
        # =========================

        self._really_quit = False

        self._tray_hint_shown = False

        self.tray = None

        self._setup_tray()


        # =========================
        # 首次启动引导挪进 start()：
        # 主界面出现之前先完成
        # 语言选择和设置向导
        # =========================


        # =========================
        # 她的状态随时间变化，
        # 每 5 分钟刷新一次顶栏
        # =========================

        self.presence_timer = QTimer(self)

        self.presence_timer.setInterval(
            5 * 60 * 1000
        )

        self.presence_timer.timeout.connect(

            self.profile_bar.refresh

        )

        self.presence_timer.start()




    # =========================
    # 打开设置页面
    # =========================

    def open_settings(self):


        self.settings_window.show()


    # =========================
    # 系统托盘：
    # 关窗不等于离开，
    # 她在后台继续陪着
    # =========================

    def _setup_tray(self):

        if not QSystemTrayIcon.isSystemTrayAvailable():

            return


        icon = QIcon(
            resource_path("assets/echo.ico")
        )

        self.setWindowIcon(icon)


        self.tray = QSystemTrayIcon(
            icon, self
        )

        self.tray.setToolTip("Soulmate")


        self._rebuild_tray_menu()


        self.tray.show()


        self.tray.activated.connect(
            self._on_tray_activated
        )


    def _rebuild_tray_menu(self):

        """
        托盘菜单按当前语言重建。
        语言切换时整个换一遍。
        """

        if self.tray is None:

            return


        menu = QMenu()

        show_action = menu.addAction(
            tr("打开 Soulmate")
        )

        show_action.triggered.connect(
            self._show_from_tray
        )

        quit_action = menu.addAction(
            tr("退出")
        )

        quit_action.triggered.connect(
            self._quit_app
        )

        self.tray.setContextMenu(menu)

        # 菜单对象要自己持有，
        # 不然被回收就弹不出来了

        self._tray_menu = menu


    # =========================
    # 语言整体即时切换
    # --------------------------------------------------
    # 设置页切语言 → 发 language_changed →
    # 这里把界面上所有文字当场换掉：
    # 标题、按钮、托盘、聊天输入区，
    # 设置窗口整个重建（它没有状态），
    # 记忆窗跟着旧设置实例一起丢弃，
    # 顶栏状态按新语言重新生成。
    # 不用重启。
    # =========================

    def _apply_language(self):

        self.setWindowTitle(
            "Soulmate"
        )

        self.settings_button.setText(
            tr("⚙ 设置")
        )

        self.export_button.setText(
            tr("⇩ 导出")
        )

        self._rebuild_tray_menu()


        if self.chat is not None:

            self.chat.retranslate()


        if self.profile_bar is not None:

            self.profile_bar.refresh()


        def _rebuild_settings():

            old = (
                self.settings_window
            )

            was_visible = (
                old is not None
                and old.isVisible()
            )


            self.settings_window = (
                SettingsWindow()
            )


            self.settings_window.settings_saved.connect(

                self.profile_bar.refresh

            )

            self.settings_window.settings_saved.connect(

                self.chat.retry_brain

            )

            self.settings_window.language_changed.connect(

                self._apply_language

            )


            if was_visible:

                self.settings_window.show()


            if old is not None:

                if (
                    old.memory_window
                    is not None
                ):

                    old.memory_window.close()

                old.deleteLater()


        # 自己重建自己要缓一拍：
        # 等信号槽走完再拆旧窗口

        QTimer.singleShot(
            0,
            _rebuild_settings,
        )


    def _on_tray_activated(self, reason):

        if reason == (
            QSystemTrayIcon.DoubleClick
        ):

            self._show_from_tray()


    def _show_from_tray(self):

        self.showNormal()

        self.raise_()

        self.activateWindow()


    def _quit_app(self):

        self._really_quit = True

        # 顶栏可能还在查天气，
        # 先给它两秒收尾

        self.profile_bar.shutdown()

        self.close()


    def closeEvent(self, event):

        # 有关闭按钮时最小化到托盘，
        # 真正退出走托盘菜单

        if (

            self.tray is not None
            and not self._really_quit

        ):

            event.ignore()

            self.hide()

            if not self._tray_hint_shown:

                self._tray_hint_shown = True

                self.tray.showMessage(

                    "Soulmate",

                    tr("我没有离开，"
                    "双击托盘图标就能找到我"),

                    QSystemTrayIcon.Information,

                    4000

                )

        else:

            event.accept()


    # =========================
    # 主动消息的系统通知
    # =========================

    def _notify_proactive(self, message):

        if self.tray is None:

            return

        # 窗口就在前台时不打扰

        if (
            self.isVisible()
            and self.isActiveWindow()
        ):

            return


        name = (
            self.settings_window
            .identity.get("echo_name")
            or her_name()
        )


        preview = message.replace(
            "\n", " "
        )[:80]


        self.tray.showMessage(

            name,
            preview,
            QSystemTrayIcon.Information,
            5000

        )


    # =========================
    # 启动入口
    # --------------------------------------------------
    # 第一次用：先语言选择，
    # 再设置向导，都走完才显示主界面。
    # 日常启动：直接进主界面。
    # ==================================================

    def start(self):

        if (
            i18n
            .needs_language_setup()
        ):

            picker = LanguageDialog()

            picker.exec()


        self._maybe_onboarding()


        if not self.isVisible():

            self.show()


    # =========================
    # 首次启动引导
    # =========================

    def _maybe_onboarding(self):

        if not needs_onboarding():

            return


        dialog = OnboardingDialog(self)

        dialog.finished.connect(

            self._on_onboarding_done

        )

        dialog.exec()


    def _on_onboarding_done(self):

        # 刚填的 Key 立即生效，
        # 名字头像同步刷新

        self.profile_bar.refresh()

        self.chat.retry_brain()