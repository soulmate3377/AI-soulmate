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

        # 托盘相关的诊断都写进 echo_error.log：
        # 打包后没有控制台，print() 用户看不到，托盘又不显示的话
        # 根本无从判断是哪一步挂了。
        # Tray diagnostics go to echo_error.log: the packaged app has no
        # console, so a print() is invisible, and with no tray icon there is
        # otherwise no way to tell which step failed.

        available = QSystemTrayIcon.isSystemTrayAvailable()

        icon_rel = "assets/echo.ico"

        icon_path = resource_path(icon_rel)

        icon_exists = False

        try:

            from pathlib import Path as _P

            icon_exists = _P(icon_path).exists()

        except Exception:

            pass

        self._log_tray(
            f"setup: isSystemTrayAvailable={available} "
            f"icon_path={icon_path!r} icon_exists={icon_exists}"
        )

        # 底层再查一遍，好和 Qt 的判断对照。
        # "Qt 说不可用"和"系统里根本没有通知区域"是两回事：
        # 前者可能是安全软件拦的，后者是 Shell 没跑。
        # Probe the layer underneath so it can be compared against Qt's
        # answer. "Qt says unavailable" and "there is no notification area at
        # all" are different problems: the first may be security software, the
        # second means the shell is not running.
        self._log_tray(
            "system: " + self._tray_system_probe()
        )

        if not available:

            self._log_tray(
                "托盘不可用，关闭窗口将直接退出"
            )

            print(
                "托盘不可用，关闭窗口将直接退出"
            )

            return


        # 图标是托盘的全部可见内容；空图标等于没有托盘。
        # The icon is the tray entry's entire visible presence; a null icon
        # means no usable tray.

        icon = QIcon(icon_path)

        if icon.isNull():

            self._log_tray(
                "托盘图标加载失败"
                "（assets/echo.ico 没找到），"
                "关闭窗口将直接退出"
            )

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

        self._log_tray(
            "tray created and show() called; "
            f"visible={self.tray.isVisible()}"
        )

        # 第一次运行时主动说一句她住在托盘里。
        # Windows 11 默认把新托盘图标折叠进隐藏区，用户看不到，
        # 于是"关掉窗口"之后会觉得程序消失了。与其等他踩，不如先说。
        # Say once, on first run, that she lives in the tray. Windows 11
        # tucks new tray icons into the hidden area by default, so after
        # closing the window the app looks like it vanished. Better to say so
        # than to let the user find out the hard way.
        QTimer.singleShot(2500, self._announce_tray)


    @staticmethod
    def _tray_system_probe():

        """
        记录几个和托盘有关的事实，供排查用。

        Record a few tray-related facts, for troubleshooting.

        注意：这里**不**用 FindWindowW 去找 Shell_TrayWnd。那个调用在
        Python 里会把 "Shell_TrayWnd"（str）按 ANSI 传进去，64 位系统上
        查不到对方的窗口，结果永远是 absent —— 我们已经实测到一次假阴性
        （Qt 说托盘可用，探测却说窗口不存在）。宁可少报，不报错的。

        Note: this deliberately does NOT use FindWindowW to look for
        Shell_TrayWnd. Python hands FindWindowW a str, which ctypes converts
        as ANSI, so on 64-bit Windows the lookup misses cross-process windows
        and always reports "absent". We already produced one false negative
        that way (Qt said the tray was fine, the probe said the window did not
        exist). Better to report less than to report something wrong.

        写日志用。查不到就返回说明文字，绝不抛异常。
        For the log only; never raises.
        """

        try:

            import ctypes
            import platform

            user32 = ctypes.windll.user32

            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)

            return (
                f"exe={platform.architecture()[0]} "
                f"screen={screen_w}x{screen_h} "
                f"foreground={user32.GetForegroundWindow()}"
            )

        except Exception as exc:

            return f"(probe failed: {type(exc).__name__})"


    def _announce_tray(self):

        """
        首次启动时提示：她住在托盘里，以及怎么找到那个图标。

        On first launch, say that she lives in the tray and how to find the
        icon there.

        只提示一次，记在 config.json 的 tray_announced 字段里。
        托盘真的不可用时什么都不做。
        Runs once; the flag lives in config.json as tray_announced. Does
        nothing when the tray is unusable.
        """

        if not self._tray_usable:

            return

        try:

            from core.storage import (
                load_config,
                save_config,
            )

            cfg = load_config()

            if cfg.get("tray_announced"):

                return

            self.tray.showMessage(

                "Soulmate",

                tr("我在托盘里。"
                "Windows 11 可能把图标折叠着——"
                "点任务栏的 ^ 箭头，"
                "或者到「设置 → 个性化 → 任务栏 → "
                "其他系统托盘图标」里把我打开。"
                "关掉窗口我就在这里，右键可以退出。"),

                QSystemTrayIcon.Information,

                9000

            )

            cfg["tray_announced"] = True

            save_config(cfg)

        except Exception:

            # 提示失败不能影响启动
            # A failed announcement must not disturb startup.
            pass


    @staticmethod
    def _log_tray(message):

        """
        托盘诊断写日志，失败也不能影响启动。
        永远不抛异常。

        Tray diagnostics go to the log; a failure here must never disturb
        startup.
        """

        try:

            from core.observe import log_line

            log_line(f"tray: {message}")

        except Exception:

            pass


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