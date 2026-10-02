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



        self._apply_window_style()



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

        self.top_bar = top_bar


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
            self._top_bar_style()
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


        # 设置页换配色：
        # 整个界面当场重新上色

        self.settings_window.theme_changed.connect(

            self._apply_theme

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

        # 托盘菜单要自己持有，否则被回收就弹不出来。
        # 在这里初始化，免得 _setup_tray 提前 return 时它是未定义属性。
        # Keep a reference to the tray menu or it gets collected and stops
        # popping up. Initialised here so it is never an undefined attribute
        # when _setup_tray returns early.
        self._tray_menu = None

        # 托盘是否真的能用（建起来了 **且** 图标不是空的）。
        # 只看 self.tray 是不够的：图标加载失败时它照样不是 None，
        # 而用户眼前什么都没有——关掉窗口就等于程序失踪，还退不掉。
        # Whether the tray is genuinely usable: created **and** carrying a
        # non-null icon. self.tray alone is not enough -- with a failed icon
        # load it is still not None while the user sees nothing, and closing
        # the window would hide the app with no way back and no way out.
        self._tray_usable = False

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

            print(
                "托盘不可用，关闭窗口将直接退出"
            )

            return


        # 图标是托盘的全部可见内容；空图标等于没有托盘。
        # The icon is the tray entry's entire visible presence; a null icon
        # means no usable tray.

        icon = QIcon(

            resource_path(
                "assets/echo.ico"
            )

        )

        if icon.isNull():

            print(
                "托盘图标加载失败"
                "（assets/echo.ico 没找到），"
                "关闭窗口将直接退出"
            )

            return


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


        self._tray_usable = True


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


        self._rebuild_settings_deferred()


    # =========================
    # 换主题即时生效：
    # 主窗/顶栏重新上样式，
    # 聊天区与顶栏各自 retheme，
    # 设置窗口整个重建
    # =========================

    def _apply_theme(self):

        self._apply_window_style()


        if (
            getattr(self, "top_bar", None)
            is not None
        ):

            self.top_bar.setStyleSheet(
                self._top_bar_style()
            )


        if self.chat is not None:

            self.chat.retheme()


        if (
            self.profile_bar is not None
        ):

            self.profile_bar.retheme()


        self._rebuild_settings_deferred()


    def _apply_window_style(self):

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


    def _top_bar_style(self):

        t = get_theme()

        return f"""
        QWidget {{
            background-color:{t['topbar_bg']};
            border-bottom:1px solid {t['topbar_border']};
        }}
        QLabel {{
            border:none;
        }}
        """


    def _rebuild_settings_deferred(self):

        # 自己重建自己要缓一拍：
        # 等信号槽走完再拆旧窗口

        def _rebuild():

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

            self.settings_window.theme_changed.connect(

                self._apply_theme

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


        QTimer.singleShot(
            0,
            _rebuild,
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

        # 关闭按钮最小化到托盘，真正退出走托盘菜单。
        # 但只在托盘**真的能用**时才藏：图标没加载出来、或被系统折叠得
        # 用户找不到时，藏起来等于程序失踪——那时老实退出，别把它变成
        # 一个只能靠任务管理器杀掉的幽灵进程。
        # The close button hides to the tray; real exit goes through the tray
        # menu. But only hide when the tray is genuinely usable: with a failed
        # icon the user cannot find it, and hiding would turn the app into a
        # ghost that only Task Manager can kill. In that case quit honestly.

        if (
            self._tray_usable
            and self.tray is not None
            and not self._really_quit
        ):

            event.ignore()

            self.hide()

            if not self._tray_hint_shown:

                self._tray_hint_shown = True

                self.tray.showMessage(

                    "Soulmate",

                    tr("我没有离开，"
                    "双击托盘图标就能找到我。"
                    "Windows 11 上图标可能被折叠"
                    "在隐藏区，点任务栏的 ^ 就能看到"),

                    QSystemTrayIcon.Information,

                    4000

                )

        else:

            event.accept()


    # =========================
    # 主动消息的系统通知
    # =========================

    def _notify_proactive(self, message):

        if not self._tray_usable:

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