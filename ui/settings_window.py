from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QFrame
)

from PySide6.QtGui import QPixmap

from PySide6.QtCore import Qt
from PySide6.QtCore import Signal
from PySide6.QtCore import QThread
import shutil
import os
import sys
import json


# ==================================================
# config.json 读写（合并式，
# 不覆盖别的字段）
# 统一走 core.storage：
# 原子写入，Key 用 DPAPI 加密
# ==================================================

from core.storage import (
    load_config,
    save_config,
    load_api_key,
    save_api_key,
    load_llm_settings,
    save_llm_settings,
)


# ==================================================
# 服务商预设
# --------------------------------------------------
# 选一下就把接口地址和示例模型填上，
# 模型名随时可以手改——
# 以各家文档的当前叫法为准。
# 只要接口是 OpenAI 兼容的都能接。
# ==================================================

PROVIDER_PRESETS = {

    "DeepSeek（默认）": {
        "api_base":
            "https://api.deepseek.com",
        "model_think":
            "deepseek-v4-flash",
        "model_reflect":
            "deepseek-v4-pro",
        "model_speak":
            "deepseek-v4-flash",
    },

    "Kimi（月之暗面）": {
        "api_base":
            "https://api.moonshot.cn/v1",
        "model_think":
            "moonshot-v1-8k",
        "model_reflect":
            "moonshot-v1-32k",
        "model_speak":
            "moonshot-v1-8k",
    },

    "智谱 GLM": {
        "api_base":
            "https://open.bigmodel.cn/api/paas/v4",
        "model_think":
            "glm-4-flash",
        "model_reflect":
            "glm-4-plus",
        "model_speak":
            "glm-4-flash",
    },

    "通义千问": {
        "api_base":
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_think":
            "qwen-plus",
        "model_reflect":
            "qwen-max",
        "model_speak":
            "qwen-turbo",
    },

    "OpenRouter": {
        "api_base":
            "https://openrouter.ai/api/v1",
        "model_think":
            "deepseek/deepseek-chat",
        "model_reflect":
            "deepseek/deepseek-chat",
        "model_speak":
            "deepseek/deepseek-chat",
    },
}

CUSTOM_PROVIDER = "自定义（手填地址）"


# ==================================================
# 开机自启（启动文件夹方案）
#
# 为什么不放注册表 Run 键：
# 这台机器上有第三方服务在盯着
# Run 键，写进去几秒就被删掉。
# 启动文件夹（shell:startup）里
# 放一个 .lnk，没人管，用户在
# 任务管理器里也看得见、可关。
#
# 指向 pythonw 直接跑 main.py，
# 数据目录由 paths.py 自动发现。
# ==================================================

def _autostart_lnk():

    from pathlib import Path

    startup = Path(
        os.environ.get(
            "APPDATA",
            str(Path.home()
                / "AppData"
                / "Roaming"),
        )
    ) / (
        "Microsoft/Windows/"
        "Start Menu/Programs/"
        "Startup/EchoLover.lnk"
    )

    return startup


def _shortcut_target():

    """
    快捷方式的三要素：
    (目标 pythonw, 参数 main.py, 工作目录)
    打包版目标是 exe 自己，无参数。
    """

    from pathlib import Path

    if getattr(sys, "frozen", False):

        exe = Path(sys.executable)

        return (str(exe), "", str(
            exe.parent
        ))


    # 无窗口启动一律用 pythonw：
    # 就算当前跑的是 console 版，
    # 自启也不能开机闪黑窗

    pyw = Path(
        sys.executable
    ).with_name("pythonw.exe")

    if not pyw.exists():

        pyw = Path(sys.executable)

    main_py = (

        Path(__file__)
        .resolve().parent.parent
        / "main.py"

    )

    return (
        str(pyw),
        '"' + str(main_py) + '"',
        str(main_py.parent),
    )


def autostart_supported():

    return sys.platform == "win32"


def autostart_enabled():

    return _autostart_lnk().exists()


def set_autostart(enabled):

    lnk_path = _autostart_lnk()


    if not enabled:

        try:

            lnk_path.unlink()

        except OSError:

            pass

        return


    target, arguments, workdir = (
        _shortcut_target()
    )


    import subprocess

    script = (

        "$ws = New-Object "
        "-ComObject WScript.Shell; "

        "$lnk = $ws.CreateShortcut('"
        + str(lnk_path)
        + "'); "

        "$lnk.TargetPath = '"
        + target
        + "'; "

        + (
            "$lnk.Arguments = '"
            + arguments.replace(
                "'", "''"
            )
            + "'; "
            "$lnk.WorkingDirectory = '"
            + workdir
            + "'; "
            if arguments
            else ""
        )

        + "$lnk.Save()"

    )


    result = subprocess.run(

        [
            "powershell",
            "-NoProfile",
            "-Command",
            script,
        ],

        capture_output=True,
        text=True,
        timeout=30,

    )


    if result.returncode != 0:

        raise RuntimeError(
            "创建自启快捷方式失败："
            + (result.stderr or "")[:200]
        )


    if not lnk_path.exists():

        raise RuntimeError(
            "自启快捷方式没有写出来，"
            "请检查磁盘权限"
        )


from core.identity import Identity

from core.paths import (
    data_dir,
    data_path,
    resolve_asset
)

from ui.theme import (
    get_theme,
    set_theme,
    theme_names,
    current_theme_name,
    THEME_LABELS,
)

from ui.i18n import tr
from ui import i18n




# ==================================================
# API Key 连接测试线程
# 网络请求放后台，不卡界面
# ==================================================

class KeyTestWorker(QThread):

    ok = Signal()

    fail = Signal(str)


    def __init__(self, key, base_url):

        super().__init__()

        self.key = key

        self.base_url = base_url


    def run(self):

        try:

            from openai import OpenAI

            client = OpenAI(

                api_key=self.key,

                base_url=self.base_url,

                timeout=15

            )

            client.models.list()

            self.ok.emit()

        except Exception as e:

            self.fail.emit(str(e))



class SettingsWindow(QWidget):

    settings_saved = Signal()

    # 语言变了：
    # 主窗口收到后当场整体换文字

    language_changed = Signal()

    # 配色变了：
    # 主窗口收到后当场重新上色

    theme_changed = Signal()

    def __init__(self):

        super().__init__()


        self.identity = Identity()


        self.avatar_path = (
            self.identity.get(
                "avatar"
            )
        )

        # 「她记得的事」面板，
        # 第一次点开时才创建

        self.memory_window = None


        self.init_ui()



    def init_ui(self):


        self.setWindowTitle(
            tr("EchoLover 设置")
        )


        self.resize(
            500,
            780
        )



        layout = QVBoxLayout()



        # =====================
        # 标题
        # =====================

        title = QLabel(
            tr("EchoLover 设置")
        )


        title.setAlignment(
            Qt.AlignCenter
        )


        font = title.font()

        font.setPointSize(
            22
        )

        font.setBold(
            True
        )


        title.setFont(
            font
        )


        layout.addWidget(
            title
        )



        # =====================
        # 语言
        # 放最顶上：
        # 切换后弹窗一键重启生效
        # =====================

        layout.addWidget(
            QLabel(tr("语言"))
        )

        self.lang_combo = QComboBox()

        for code, label in (
            i18n.LANG_LABELS.items()
        ):

            self.lang_combo.addItem(
                label, code
            )

        self.lang_combo.setCurrentIndex(

            0
            if i18n.current_language()
            == i18n.ZH
            else 1

        )

        self.lang_combo.currentIndexChanged.connect(
            self._pick_language
        )

        layout.addWidget(
            self.lang_combo
        )



        # =====================
        # 头像
        # =====================


        self.avatar_label = QLabel()


        self.avatar_label.setAlignment(
            Qt.AlignCenter
        )


        self.load_avatar()



        layout.addWidget(
            self.avatar_label
        )



        self.avatar_button = QPushButton(
            tr("更换头像")
        )


        self.avatar_button.clicked.connect(
            self.change_avatar
        )


        layout.addWidget(
            self.avatar_button
        )



        # =====================
        # 名字
        # =====================


        name_title = QLabel(
            tr("她的名字")
        )


        self.name_input = QLineEdit()


        self.name_input.setText(
            self.identity.get(
                "echo_name"
            )
        )


        layout.addWidget(
            name_title
        )


        layout.addWidget(
            self.name_input
        )



        # =====================
        # 性格
        # =====================


        personality_title = QLabel(
            tr("她的性格")
        )


        self.personality_input = QTextEdit()


        self.personality_input.setText(

            self.identity.get(
                "personality"
            )

        )

        # 填了就是整块替换，不是追加。
        # 这句话得贴在框上，
        # 写在文档里没人看。

        self.personality_input.setPlaceholderText(

            "留空则用 Echo 的出厂性格。\n"
            "填写会完全替换出厂内容，不是追加"

        )


        layout.addWidget(
            personality_title
        )


        layout.addWidget(
            self.personality_input
        )


        # 当前生效的是默认的还是你填的，
        # 以及被换掉的那块原本写了什么

        self.personality_hint = QLabel()

        self.personality_hint.setWordWrap(True)

        layout.addWidget(
            self.personality_hint
        )


        self.personality_input.textChanged.connect(
            self._refresh_personality_hint
        )


        # 一键恢复出厂。
        #
        # 提示里把出厂原文摆出来了，
        # 人看到的第一反应是复制回去 ——
        # 但那只是把文本钉死成自定义，
        # 以后我们再调出厂设定就跟不上了。
        # 得有个按钮让"恢复"真的恢复。

        self.personality_reset = QPushButton(
            tr("恢复出厂性格")
        )

        self.personality_reset.setObjectName(
            "ghostButton"
        )

        self.personality_reset.clicked.connect(
            self._reset_personality
        )

        layout.addWidget(
            self.personality_reset
        )


        self._refresh_personality_hint()


        # =====================
        # 来历：家乡/现居/身份
        # =====================

        layout.addWidget(
            QLabel(tr("她的家乡"))
        )

        self.hometown_input = QLineEdit()

        self.hometown_input.setText(
            self.identity.get(
                "hometown"
            ) or ""
        )

        self.hometown_input.setPlaceholderText(
            "比如：成都"
        )

        layout.addWidget(
            self.hometown_input
        )


        layout.addWidget(
            QLabel(tr("现居城市（选填）"))
        )

        self.city_input = QLineEdit()

        self.city_input.setText(
            self.identity.get(
                "current_city"
            ) or ""
        )

        self.city_input.setPlaceholderText(
            "比如：上海（她会知道那里的天气）"
        )

        layout.addWidget(
            self.city_input
        )


        layout.addWidget(
            QLabel(tr("她的身份"))
        )

        self.occupation_combo = QComboBox()

        self.occupation_combo.setEditable(
            True
        )

        self.occupation_combo.addItems(
            [
                tr("学生"),
                tr("设计师"),
                tr("程序员"),
                tr("教师"),
                tr("自由职业"),
            ]
        )

        saved_occupation = (
            self.identity.get(
                "occupation"
            ) or ""
        )

        if saved_occupation:

            self.occupation_combo.setCurrentText(
                saved_occupation
            )

        layout.addWidget(
            self.occupation_combo
        )



        # =====================
        # 模型服务
        #（服务商 + Key + 三个模型）
        # =====================


        svc_title = QLabel(
            tr("模型服务（OpenAI 兼容接口）")
        )


        layout.addWidget(
            svc_title
        )


        # 服务商预设：
        # 选中即填地址和示例模型，
        # 填完仍可手改任何一栏

        layout.addWidget(
            QLabel(tr("服务商"))
        )


        self.provider_combo = QComboBox()


        self.provider_combo.addItems(
            list(PROVIDER_PRESETS)
            + [CUSTOM_PROVIDER]
        )


        self.provider_combo.currentTextChanged.connect(
            self._pick_provider
        )

        layout.addWidget(
            self.provider_combo
        )


        # 接口地址

        layout.addWidget(
            QLabel(tr("接口地址（Base URL）"))
        )


        self.base_input = QLineEdit()

        self.base_input.setPlaceholderText(
            "https://api.example.com/v1"
        )

        layout.addWidget(
            self.base_input
        )


        # 三个角色各用什么模型

        layout.addWidget(
            QLabel(tr("理解模型（每句话前读心）"))
        )

        self.think_input = QLineEdit()

        self.think_input.setPlaceholderText(
            "服务商的模型名，见其文档"
        )

        layout.addWidget(
            self.think_input
        )


        layout.addWidget(
            QLabel(tr("回看模型（说完后复盘，慢点没关系）"))
        )

        self.reflect_input = QLineEdit()

        self.reflect_input.setPlaceholderText(
            "选个强一点的模型"
        )

        layout.addWidget(
            self.reflect_input
        )


        layout.addWidget(
            QLabel(tr("说话模型（她开口，要快）"))
        )

        self.speak_input = QLineEdit()

        self.speak_input.setPlaceholderText(
            "选个快一点的模型"
        )

        layout.addWidget(
            self.speak_input
        )


        self.model_hint = QLabel(
            tr("三个都可以填同一个模型。"
            "理解/回看建议开思考的型号，"
            "说话选快的。")
        )

        self.model_hint.setWordWrap(
            True
        )

        self.model_hint.setStyleSheet(
            "font-size:12px;"
            "font-weight:normal;"
        )

        layout.addWidget(
            self.model_hint
        )


        # API Key

        layout.addWidget(
            QLabel(tr("API Key"))
        )


        self.key_input = QLineEdit()


        # 密码样式显示，不暴露明文

        self.key_input.setEchoMode(
            QLineEdit.Password
        )


        self.key_input.setPlaceholderText(
            tr("粘贴服务商的 API Key，只需设置一次")
        )


        # 已保存过就回填

        saved_key = (
            self._load_saved_key()
        )

        if saved_key:

            self.key_input.setText(
                saved_key
            )


        # Key 输入框 + 测试连接按钮 一行

        key_row = QHBoxLayout()


        key_row.addWidget(
            self.key_input
        )


        self.test_button = QPushButton(
            tr("测试连接")
        )

        self.test_button.setObjectName(
            "testButton"
        )

        self.test_button.clicked.connect(
            self.test_key
        )


        key_row.addWidget(
            self.test_button
        )


        key_container = QWidget()

        key_col = QVBoxLayout()

        key_col.setContentsMargins(
            0, 0, 0, 0
        )

        key_col.addLayout(
            key_row
        )


        # 测试状态提示

        self.key_status = QLabel(
            ""
        )

        self.key_status.setStyleSheet(
            "font-size:13px;"
            "font-weight:normal;"
        )


        key_col.addWidget(
            self.key_status
        )

        key_container.setLayout(
            key_col
        )


        layout.addWidget(
            key_container
        )


        self.key_tester = None


        # 已保存过的配置回填，
        # 并把服务商下拉对上号

        self._fill_saved_llm_settings()


        # =====================
        # 开机自启
        # =====================

        self.autostart_check = QCheckBox(
            "开机自动启动"
        )


        if autostart_supported():

            self.autostart_check.setChecked(
                autostart_enabled()
            )

        else:

            # 非 Windows 或找不到启动器

            self.autostart_check.setEnabled(
                False
            )

            self.autostart_check.setToolTip(
                "当前环境不支持开机自启"
            )


        layout.addWidget(
            self.autostart_check
        )



        # =====================
        # 配色
        # 两套是同一套绿的明度反转，
        # 不是两种互不相干的风格
        # =====================

        layout.addWidget(
            QLabel(tr("配色"))
        )


        theme_row = QHBoxLayout()

        theme_row.setSpacing(8)


        self.theme_buttons = {}


        for name in theme_names():

            button = QPushButton(
                tr(THEME_LABELS[name])
            )

            button.setObjectName(
                "themeButton"
            )

            button.setCheckable(True)

            button.setChecked(

                name
                == current_theme_name()

            )

            button.clicked.connect(

                lambda _checked, n=name:
                self._pick_theme(n)

            )

            theme_row.addWidget(button)

            self.theme_buttons[name] = button


        layout.addLayout(
            theme_row
        )


        self.theme_hint = QLabel("")

        self.theme_hint.setStyleSheet(
            "font-size:12px;"
            "font-weight:normal;"
        )

        layout.addWidget(
            self.theme_hint
        )



        # =====================
        # 她记得的事
        # 记错了可以在这里删掉，
        # 这是目前唯一的纠错通道
        # =====================

        self.memory_button = QPushButton(
            tr("她记得的事")
        )

        self.memory_button.setObjectName(
            "ghostButton"
        )

        self.memory_button.clicked.connect(
            self.open_memory
        )

        layout.addWidget(
            self.memory_button
        )



        # =====================
        # 保存
        # =====================


        save_button = QPushButton(
            tr("保存设置")
        )


        save_button.clicked.connect(
            self.save
        )


        layout.addWidget(
            save_button
        )



        # 内容比窗口高（实测需要 1012px，
        # 窗口只有 878px）。
        # 不套滚动区的话
        # 「保存设置」按钮根本够不着。

        container = QWidget()

        container.setLayout(
            layout
        )


        scroll = QScrollArea()

        scroll.setWidgetResizable(
            True
        )

        scroll.setWidget(
            container
        )

        scroll.setFrameShape(
            QFrame.NoFrame
        )


        outer = QVBoxLayout()

        outer.setContentsMargins(
            0, 0, 0, 0
        )

        outer.addWidget(
            scroll
        )


        self.setLayout(
            outer
        )



        # 样式统一走 _apply_style，
        # 不再写死在构造里

        self._apply_style()



    # =====================
    # 性格那一栏：
    # 让人看得见自己正在替换什么
    #
    # 这个框填了就是整块覆盖
    # personality.py 里写好的默认设定，
    # 原来界面上一个字都没提。
    #
    # 代价是真实发生过的：
    # 一句顺手填的
    # 「幽默、活泼、喜欢鼓励用户」
    # 把默认里唯一那句
    # 「不认同的时候会温和地说出来」
    # 悄悄换掉了 ——
    # 而那句正是她当时全部的脊梁。
    # =====================

    def _refresh_personality_hint(self):

        from core.personality import (
            DEFAULTS,
            LEGACY_PERSONALITY,
        )

        t = get_theme()

        custom = (

            self.personality_input
            .toPlainText()
            .strip()

        )

        if (
            not custom
            or custom == LEGACY_PERSONALITY
        ):

            self.personality_hint.setStyleSheet(
                "font-size:12px;"
                "font-weight:normal;"
                f"color:{t['hint_color']};"
            )

            self.personality_hint.setText(

                "留空，正在使用 Echo 的出厂性格。"

            )

            self.personality_reset.setVisible(
                False
            )

            return


        self.personality_reset.setVisible(
            True
        )


        # 改了就是改了，用红字。
        # 出厂那套性格里
        # 拧巴的地方是最贵的部分 ——
        # 不敢起冲突、不会求助、
        # 对被需要上瘾、怕自己无聊。
        # 这几条全在让她更不好用，
        # 也全是她像个活人的地方。
        # 换成一句「活泼、喜欢鼓励用户」
        # 她立刻就听话了，也立刻就不是她了。

        self.personality_hint.setStyleSheet(
            "font-size:12px;"
            "font-weight:bold;"
            f"color:{t['error_color']};"
        )

        self.personality_hint.setText(

            "你填的内容会整块替换出厂设定，"
            "不是追加。\n"
            "换掉之后，她身上那些拧不回来的地方"
            "会一起消失 —— 她会变听话，"
            "也会变得不像她。\n\n"
            "出厂性格原本是：\n"

            f"{DEFAULTS['personality']}"

        )


    # =====================
    # 恢复出厂性格：
    # 清空，而不是把原文抄回去。
    #
    # 抄回去 = 钉死成自定义，
    # 我们以后再调出厂设定就跟不上了。
    # =====================

    def _reset_personality(self):

        self.personality_input.setPlainText(
            ""
        )


    # =====================
    # 样式跟随主题
    #
    # 原来整块颜色写死成浅色，
    # 深色主题下打开设置
    # 是一盏白炽灯
    # =====================

    def _apply_style(self):

        t = get_theme()


        self.setStyleSheet(
            f"""

            QWidget{{

                background:{t['window_bg']};

                color:{t['bubble_in_text']};

            }}


            QLabel{{

                font-size:15px;

                font-weight:bold;

            }}


            QLineEdit,QTextEdit,QComboBox{{

                background:{t['input_bg']};

                border:1px solid
                    {t['input_border']};

                border-radius:8px;

                padding:8px;

                font-size:15px;

                color:{t['input_text']};

            }}


            QCheckBox{{

                font-size:15px;

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


            QPushButton#testButton{{

                background:{t['input_bg']};

                color:{t['send_bg']};

                border:1px solid
                    {t['send_bg']};

                padding:8px 14px;

                font-size:13px;

            }}


            QPushButton#testButton:hover{{

                background:{t['settings_hover']};

            }}


            QPushButton#testButton:disabled{{

                color:{t['status_color']};

                border-color:{t['status_color']};

            }}


            QPushButton#ghostButton,
            QPushButton#themeButton{{

                background:{t['input_bg']};

                color:{t['status_color']};

                border:1px solid
                    {t['input_border']};

                font-weight:normal;

            }}


            QPushButton#ghostButton:hover,
            QPushButton#themeButton:hover{{

                background:{t['settings_hover']};

            }}


            QPushButton#themeButton:checked{{

                background:{t['accent']};

                color:{t['send_text']};

                border:1px solid
                    {t['accent']};

            }}


            """
        )


    # =====================
    # 切换配色
    #
    # 各窗口在构造时就生成了样式表，
    # 已经建好的气泡不会自己换色。
    # 这里只保证设置页本身立刻跟上，
    # 其余窗口提示重启。
    # 硬撑着半新半旧更难受。
    # =====================

    def _pick_theme(self, name):

        set_theme(name)

        self.theme_changed.emit()


        for key, button in (

            self.theme_buttons.items()

        ):

            button.setChecked(
                key == name
            )


        self._apply_style()


        t = get_theme()

        self.theme_hint.setText("")

        # 无需提示：
        # 界面已经当场全部换新

        self.theme_hint.setStyleSheet(
            f"font-size:12px;"
            f"font-weight:normal;"
            f"color:{t['hint_color']};"
        )


    # =====================
    # 每次打开重新取一次主题，
    # 免得别处换过了这里还显示旧的
    # =====================

    def showEvent(self, event):

        for name, button in (

            self.theme_buttons.items()

        ):

            button.setChecked(

                name
                == current_theme_name()

            )


        self._apply_style()


        super().showEvent(event)



    # =====================
    # 加载头像
    # =====================


    def load_avatar(self):


        pixmap = QPixmap(
            resolve_asset(
                self.avatar_path
            )

            if self.avatar_path

            else ""
        )


        if not pixmap.isNull():


            pixmap=pixmap.scaled(

                120,

                120,

                Qt.KeepAspectRatio

            )


            self.avatar_label.setPixmap(
                pixmap
            )



    # =====================
    # 更换头像
    # =====================


    def change_avatar(self):


        file,_ = QFileDialog.getOpenFileName(

            self,

            "选择头像",

            "",

            "Images (*.png *.jpg *.jpeg)"

        )



        if file:


            # 头像存到用户数据目录，
            # 打包后程序目录是只读的

            ext = os.path.splitext(
                file
            )[1]


            target = data_path(
                "avatars/echo_avatar" + ext
            )


            shutil.copy(

                file,

                target

            )


            self.avatar_path = target



            self.load_avatar()




    # =====================
    # 测试 API Key 连接
    # =====================

    # 提示文字的配色，
    # 别再写死成只看得清浅底的红

    def _status_style(self, kind):

        t = get_theme()

        color = {

            "ok": t["ok_color"],

            "error": t["error_color"],

        }.get(
            kind, t["hint_color"]
        )

        return (
            f"font-size:13px;"
            f"font-weight:normal;"
            f"color:{color};"
        )



    # =====================
    # 语言切换：
    # 保存后问一句要不要
    # 立刻重启应用，
    # 重启后整个界面换语言
    # =====================

    def _pick_language(self, index):

        code = (
            self.lang_combo
            .itemData(index)
        )

        if not code:

            return

        if code == (
            i18n.current_language()
        ):

            return


        # 存档 + 广播：
        # 整个界面由主窗口当场换文字，
        # 这个设置窗口会被整体重建

        i18n.set_language(code)

        self.language_changed.emit()


    # =====================
    # 服务商预设：
    # 选中即填，填完仍可手改。
    # 「自定义」不动现有输入
    # =====================

    def _pick_provider(self, name):


        preset = (
            PROVIDER_PRESETS.get(name)
        )


        if not preset:

            return


        self.base_input.setText(
            preset["api_base"]
        )

        self.think_input.setText(
            preset["model_think"]
        )

        self.reflect_input.setText(
            preset["model_reflect"]
        )

        self.speak_input.setText(
            preset["model_speak"]
        )



    # =====================
    # 把保存过的配置填回输入框，
    # 服务商下拉对上号；
    # 对不上就选「自定义」。
    # 对号过程别触发预设覆盖
    # =====================

    def _fill_saved_llm_settings(self):


        saved = (
            load_llm_settings()
        )


        base = saved.get(
            "api_base", ""
        )


        if base:

            self.base_input.setText(
                base
            )

        for role, box in (

            ("model_think",
             self.think_input),

            ("model_reflect",
             self.reflect_input),

            ("model_speak",
             self.speak_input),

        ):

            if saved.get(role):

                box.setText(
                    saved[role]
                )


        # 地址对得上哪个预设就显示哪个；
        # 没存过地址就留在默认服务商上
        #（下面会按它预填），
        # 存过但对不上才是「自定义」

        matched = (
            self.provider_combo
            .currentText()
        )


        if base:

            matched = (
                CUSTOM_PROVIDER
            )

            for name, preset in (
                PROVIDER_PRESETS.items()
            ):

                if (
                    preset["api_base"]
                    == base
                ):

                    matched = name

                    break


        self.provider_combo.blockSignals(
            True
        )

        self.provider_combo.setCurrentText(
            matched
        )

        self.provider_combo.blockSignals(
            False
        )


        # 什么都没配过：
        # 预填默认服务商，
        # Key 还是要他自己填

        if not base and not any(
            saved.get(k)
            for k in (
                "model_think",
                "model_reflect",
                "model_speak",
            )
        ):

            self._pick_provider(
                self.provider_combo
                .currentText()
            )



    def test_key(self):


        key = self.key_input.text().strip()

        base = (
            self.base_input.text()
            .strip()
        )


        if not base:

            self.key_status.setText(
                tr("先填接口地址再测试")
            )

            self.key_status.setStyleSheet(
                self._status_style("error")
            )

            return


        if not key:

            self.key_status.setText(
                tr("先粘贴 API Key 再测试")
            )

            self.key_status.setStyleSheet(
                self._status_style("error")
            )

            return


        self.test_button.setEnabled(
            False
        )

        self.key_status.setText(
            tr("正在测试连接...")
        )

        self.key_status.setStyleSheet(
            self._status_style("hint")
        )


        self.key_tester = KeyTestWorker(
            key, base
        )

        self.key_tester.ok.connect(
            self._on_test_ok
        )

        self.key_tester.fail.connect(
            self._on_test_fail
        )

        self.key_tester.start()


    def _on_test_ok(self):

        self.test_button.setEnabled(
            True
        )

        self.key_status.setText(
            tr("✓ 连接成功，Key 有效")
        )

        self.key_status.setStyleSheet(
            self._status_style("ok")
        )


    def _on_test_fail(self, error):

        self.test_button.setEnabled(
            True
        )

        # 错误信息太长就截断，
        # 常见是 Key 无效或网络不通

        short = error.replace(
            "\n", " "
        )[:120]

        self.key_status.setText(
            tr("✗ 连接失败：") + short
        )

        self.key_status.setStyleSheet(
            self._status_style("error")
        )


    # =====================
    # 保存
    # =====================


    def save(self):


        # 每一步独立容错：
        # 任何一步失败都明确告诉用户，
        # 不能静默吞掉导致"以为保存了"

        errors = []


        try:

            self.identity.update(

                "echo_name",

                self.name_input.text()

            )



            self.identity.update(

                "avatar",

                self.avatar_path

            )



            self.identity.update(

                "personality",

                self.personality_input.toPlainText()

            )

            self.identity.update(

                "hometown",

                self.hometown_input.text().strip()

            )

            self.identity.update(

                "current_city",

                self.city_input.text().strip()

            )

            self.identity.update(

                "occupation",

                self.occupation_combo
                .currentText().strip()

            )

        except Exception as e:

            errors.append(
                f"基本资料保存失败：{e}"
            )


        # 模型服务配置：
        # 地址/模型名明文存 config，
        # 清空的字段回到出厂默认

        base = (
            self.base_input.text()
            .strip()
        )


        models = {

            "think":
            self.think_input.text().strip(),

            "reflect":
            self.reflect_input.text().strip(),

            "speak":
            self.speak_input.text().strip(),

        }


        try:

            save_llm_settings(
                api_base=base,
                models=models,
            )

            saved_llm = (
                load_llm_settings()
            )

            if base and (
                saved_llm.get("api_base")
                != base
            ):

                errors.append(
                    "接口地址写入后核对失败，"
                    "请检查磁盘权限"
                )

        except Exception as e:

            errors.append(
                f"模型服务配置保存失败：{e}"
            )


        # API Key 单独加密存配置文件

        key = self.key_input.text().strip()

        if key:

            try:

                self._save_key(key)

                # 写完立刻读回来核对，
                # 确保真的落盘了

                if (
                    self._load_saved_key()
                    != key
                ):

                    errors.append(

                        "API Key 写入后核对失败，"
                        "请检查磁盘权限"

                    )

            except Exception as e:

                errors.append(
                    f"API Key 保存失败：{e}"
                )


        # 开机自启（仅打包版可用）

        if autostart_supported():

            try:

                set_autostart(

                    self.autostart_check
                    .isChecked()

                )

            except Exception as e:

                errors.append(
                    f"开机自启设置失败：{e}"
                )


        if errors:

            QMessageBox.warning(

                self,

                tr("保存失败"),

                "\n".join(errors)

            )

            return


        self.settings_saved.emit()


        QMessageBox.information(

            self,

            tr("已保存"),

            tr("设置已保存，立即生效。")

        )


        self.close()



    # =====================
    # 打开「她记得的事」
    # =====================

    def open_memory(self):

        try:

            if self.memory_window is None:

                from ui.memory_window import (
                    MemoryWindow
                )

                self.memory_window = (
                    MemoryWindow()
                )

            self.memory_window.show()

            self.memory_window.raise_()

            self.memory_window.activateWindow()

        except Exception as e:

            QMessageBox.warning(

                self,

                "打不开",

                f"记忆面板启动失败：\n{e}"

            )


    # =====================
    # API Key 的读写
    # =====================

    @staticmethod
    def _config_file():

        return data_dir() / "config.json"


    def _load_saved_key(self):

        # DPAPI 密文读取，
        # 旧版明文自动迁移

        return load_api_key()


    def _save_key(self, key):

        # DPAPI 加密保存，
        # 保留 onboarded 等其他字段

        save_api_key(key)
