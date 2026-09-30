# theme.py
#
# Echo 界面主题系统
# 内置两个方向：
#   paper —— 雾米 × 苔绿（浅色，安静、干净）
#   lamp  —— 雾夜（深色，同一套绿压暗）
#
# 在设置里把 user_profile.json 的
# "theme" 字段改成 "paper" 或 "lamp" 即可切换
#
# 两个主题是同一套色相的明度反转，
# 不是两套互不相干的风格。
# 底色都比气泡深一档 —— 微信的 #EDEDED
# 和纯白气泡只差 7% 亮度，气泡靠间距才浮起来，
# 这里让气泡自己站起来。

from core.identity import Identity


THEMES = {

    # =========================
    # 雾米 × 苔绿
    # =========================

    "paper": {

        # 窗口与顶栏

        "window_bg": "#F1F3EE",
        "topbar_bg": "#FAFBF8",
        "topbar_border": "#E4E8DE",
        "name_color": "#2C332B",
        "status_color": "#8C968A",
        "settings_color": "#7C867A",
        "settings_hover": "#E9EDE4",

        # 聊天区

        "chat_bg": "#F1F3EE",

        # Echo 气泡（左）

        "bubble_in_bg": "#FFFFFF",
        "bubble_in_text": "#2C332B",
        "bubble_in_border": "#E2E7DC",

        # 我的气泡（右）

        "bubble_out_bg": "#93C9A8",
        "bubble_out_text": "#1F3A2A",

        # 时间与系统提示

        "time_color": "#A9B0A2",
        "system_color": "#A9B0A2",

        # 输入栏

        "inputbar_bg": "#FAFBF8",
        "inputbar_border": "#E4E8DE",
        "input_bg": "#FFFFFF",
        "input_border": "#DFE4D9",
        "input_text": "#2C332B",
        "input_focus_border": "#6FB48C",

        # 发送按钮

        "send_bg": "#6FB48C",
        "send_hover": "#5EA47C",
        "send_disabled": "#BFDCCB",
        "send_text": "#FFFFFF",

        # 兜底头像底色

        "avatar_in_bg": "#93C9A8",
        "avatar_out_bg": "#5A6B5E",
        "avatar_out_text": "#F1F3EE",

        # 头像圆角半径（19 = 圆形）
        # 原来是 8px 方角，
        # 比气泡的 14px 小一半，
        # 两个圆角对不上

        "avatar_radius": 19,

        # 强调色：
        # 光标、状态圆点、选中态

        "accent": "#6FB48C",

        # 设置页的反馈色：
        # 连接成功 / 失败 / 灰提示

        "ok_color": "#3A7D44",
        "error_color": "#B3261E",
        "hint_color": "#8A7B63",

        # 顶栏名字的字体
        # 楷体带一点手写信的感觉

        "name_font": "KaiTi",

    },

    # =========================
    # 雾夜
    # =========================

    "lamp": {

        # 窗口与顶栏

        "window_bg": "#1A1F1C",
        "topbar_bg": "#202623",
        "topbar_border": "#2E3630",
        "name_color": "#E6EBE4",
        "status_color": "#8A968C",
        "settings_color": "#8A968C",
        "settings_hover": "#2A322C",

        # 聊天区

        "chat_bg": "#1A1F1C",

        # Echo 气泡（左）

        "bubble_in_bg": "#242B26",
        "bubble_in_text": "#E6EBE4",
        "bubble_in_border": "#303830",

        # 我的气泡（右）

        "bubble_out_bg": "#4E8F6B",
        "bubble_out_text": "#EAF5EE",

        # 时间与系统提示

        "time_color": "#6B756C",
        "system_color": "#6B756C",

        # 输入栏

        "inputbar_bg": "#202623",
        "inputbar_border": "#2E3630",
        "input_bg": "#242B26",
        "input_border": "#333B34",
        "input_text": "#E6EBE4",
        "input_focus_border": "#6FB48C",

        # 发送按钮

        "send_bg": "#4E8F6B",
        "send_hover": "#5CA278",
        "send_disabled": "#33453A",
        "send_text": "#EAF5EE",

        # 兜底头像底色

        "avatar_in_bg": "#4E8F6B",
        "avatar_out_bg": "#E6EBE4",
        "avatar_out_text": "#1A1F1C",

        "avatar_radius": 19,

        "accent": "#6FB48C",

        "ok_color": "#7FC4A0",
        "error_color": "#E8908A",
        "hint_color": "#8A968C",

        # 暗色下名字用常规黑体更清晰

        "name_font": "Microsoft YaHei",

    },

}


DEFAULT_THEME = "paper"


# 设置里的显示名

THEME_LABELS = {
    "paper": "雾米",
    "lamp": "雾夜",
}


def current_theme_name():


    name = Identity().get("theme")


    if name in THEMES:

        return name


    return DEFAULT_THEME


def get_theme():

    return THEMES[current_theme_name()]


def theme_names():

    return list(THEMES.keys())


def set_theme(name):

    """
    只负责把选择写进档案，
    不负责让界面立刻变。

    各窗口在构造时就读了一次主题并生成样式表，
    已经建好的气泡不会自己换色。
    调用方写完应该提示重启，
    别让界面停在半新半旧的状态。
    """

    if name not in THEMES:

        return False

    Identity().update("theme", name)

    return True
