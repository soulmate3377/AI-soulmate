# ui/i18n.py
#
# 语言与多语言文案。
#
# ==================================================
# 设计
# ==================================================
#
# 中文是「原文」：代码里直接写中文，
# tr("中文") 在中文下原样返回，
# 英文下查 EN_MAP，查不到回落中文——
# 所以新增一句界面文案永远不需要
# 先来登记 key，写完就能跑。
#
# 语言存 config.json 的 "language"。
# 没设置过 = 还没选过语言，
# 启动时先弹语言选择 +
# 设置向导，完成后才进主界面。
#
# 语言在窗口创建时生效：
# 主界面是启动时就建好的控件树，
# 切换语言后重启 Soulmate 才会
# 全部换过来。

from core import storage


ZH = "zh"

EN = "en"


# 下拉框里给用户看的叫法

LANG_LABELS = {

    ZH: "中文",

    EN: "English",

}


_current = None



def current_language():

    global _current

    if _current is None:

        lang = (
            storage.load_config()
            .get("language")
        )

        _current = (
            lang
            if lang in (ZH, EN)
            else ZH
        )

    return _current



def set_language(lang):

    """
    保存语言选择。
    立即对本进程后续创建的
    窗口生效；已经在屏幕上的
    窗口要重启才换。
    """

    global _current

    if lang not in (ZH, EN):

        return


    _current = lang

    cfg = (
        storage.load_config()
    )

    cfg["language"] = lang

    storage.save_config(cfg)



def needs_language_setup():

    return (
        storage.load_config()
        .get("language")
        not in (ZH, EN)
    )



def tr(text):

    if current_language() == EN:

        return EN_MAP.get(
            text, text
        )

    return text



def her_name():

    """
    她的显示名：
    档案里起过的名字优先，
    没有就用 Soulmate。
    """

    try:

        from core.identity import (
            Identity,
        )

        return (
            Identity().get("echo_name")
            or "Soulmate"
        )

    except Exception:

        return "Soulmate"



# ==================================================
# 英文映射表
# --------------------------------------------------
# 键 = 界面里的中文原文（一字不差）。
# 带参数的文案键进整个格式串，
# 比如 "找到 %d 条"。
# ==================================================

EN_MAP = {

    # ---- 通用 ----

    "发送": "Send",
    "复制": "Copy",
    "重新生成": "Regenerate",
    "设置": "Settings",
    "保存": "Save",
    "下一步": "Next",
    "完成": "Done",
    "开始": "Start",
    "家乡": "Hometown",
    "现居城市": "City",
    "她的身份": "Occupation",
    "配色": "Theme",
    "我": "Me",

    # ---- 职业选项 ----

    "学生": "Student",
    "设计师": "Designer",
    "程序员": "Programmer",
    "教师": "Teacher",
    "自由职业": "Freelancer",

    # ---- 托盘 / 记忆窗 ----

    "打开 Soulmate": "Open Soulmate",
    "退出": "Quit",
    "她记错了就删掉这条":
        "Delete if she misremembers",
    "全部忘掉": "Forget everything",
    "会把她记住的 %d 条全部删掉，\n她就真的什么都不记得了。\n\n确定吗？":
        "This erases all %d memories.\n"
        "She will truly remember nothing.\n\n"
        "Are you sure?",
    "语言已保存": "Language saved",
    "重启 Soulmate 后整个界面"
    "就会切换成新语言。\n"
    "现在就重启吗？":
        "Soulmate will restart with the "
        "new language.\nRestart now?",

    # ---- 主窗口 / 托盘 ----

    "Soulmate 设置": "Soulmate Settings",
    "⚙ 设置": "⚙ Settings",
    "⇩ 导出": "⇩ Export",
    "我没有离开，"
    "双击托盘图标就能找到我":
        "I'm still here — "
        "double-click the tray icon to find me",
    "打开": "Open",
    "退出": "Quit",

    # ---- 聊天 ----

    "和她说点什么...": "Say something to her...",
    "你好，我是%s。": "Hi, I'm %s.",
    "很高兴认识你": "Nice to meet you",
    "（先去右上角「⚙ 设置」"
    "里填一下 API Key，"
    "我才能真正开口说话）":
        "(Add your API Key in ⚙ Settings "
        "at the top right, then I can "
        "really talk)",
    "（启动出了点问题：%s）":
        "(Something went wrong on startup: %s)",
    "还没有设置 API Key。\n"
    "点右上角「⚙ 设置」选好服务商，"
    "粘贴你的 API Key，"
    "保存后再发一次消息。":
        "No API Key yet.\n"
        "Open ⚙ Settings (top right), "
        "pick a provider and paste your "
        "API Key, save, then send again.",
    "还没有设置 API Key。\n"
    "点右上角「⚙ 设置」粘贴你的 "
    "API Key，"
    "保存后再发一次消息。":
        "No API Key yet.\n"
        "Open ⚙ Settings (top right), "
        "paste your API Key, save, "
        "then send again.",
    "启动时出了点问题：\n%s\n详细日志在 %s":
        "Startup problem:\n%s\nSee %s for details",
    "出错了：%s": "Error: %s",
    "聊天记录已导出到：%s":
        "Chat exported to: %s",
    "导出失败：%s": "Export failed: %s",

    # ---- 搜索 / 导出 ----

    "搜索聊天记录": "Search chats",
    "搜点什么……": "Search…",
    "输入关键词开始搜索":
        "Type a keyword to search",
    "找到 %d 条": "%d matches",
    "没有找到": "No matches",
    "这条不在当前显示的范围里"
    "（更早或已重新生成），"
    "用「导出」能看全文":
        "Not in the currently loaded "
        "history (older or regenerated). "
        "Use Export to read everything.",
    "导出聊天记录": "Export chat",
    "文本文件 (*.txt)": "Text files (*.txt)",
    "# Soulmate 聊天记录":
        "# Soulmate chat history",
    "# 共 %d 条 · 导出于 %s":
        "# %d messages · exported %s",

    # ---- 设置页 ----

    "模型服务（OpenAI 兼容接口）":
        "Model service (OpenAI-compatible)",
    "服务商": "Provider",
    "接口地址（Base URL）":
        "API base URL",
    "理解模型（每句话前读心）":
        "Understanding model (reads every message)",
    "回看模型（说完后复盘，慢点没关系）":
        "Review model (reflects after replying; slow is fine)",
    "说话模型（她开口，要快）":
        "Speaking model (her voice; keep it fast)",
    "三个都可以填同一个模型。"
    "理解/回看建议开思考的型号，"
    "说话选快的。":
        "All three can be the same model. "
        "Understanding/Review work best with "
        "thinking models; Speaking with fast ones.",
    "API Key": "API Key",
    "粘贴服务商的 API Key，只需设置一次":
        "Paste your provider's API Key — set once",
    "测试连接": "Test connection",
    "正在测试连接...": "Testing…",
    "✓ 连接成功，Key 有效":
        "✓ Connected — Key works",
    "✗ 连接失败：": "✗ Failed: ",
    "先粘贴 API Key 再测试":
        "Paste an API Key first",
    "先填接口地址再测试":
        "Enter the API base URL first",
    "开机自动启动": "Start with Windows",
    "打包后的 Echo.exe 支持":
        "Available in the packaged app",
    "语言": "Language",
    "切换语言后重启 Soulmate "
    "才会全部生效":
        "Restart Soulmate to fully apply "
        "the language change",
    "保存失败": "Save failed",
    "已保存": "Saved",
    "设置已保存，立即生效。":
        "Settings saved. Applied immediately.",

    # ---- 首次引导 ----

    "欢迎使用 Soulmate": "Welcome to Soulmate",
    "你好，我是 Echo": "Hi, I'm Soulmate",
    "先让我能开口说话":
        "First, let me find my voice",
    "我通过大模型思考，"
    "需要一个 API Key。\n"
    "默认走 DeepSeek"
    "（platform.deepseek.com "
    "免费注册就能拿到），"
    "想用 Kimi、智谱这些别家，"
    "之后在右上角设置里换。":
        "I think through a large language "
        "model and need an API Key.\n"
        "DeepSeek works out of the box "
        "(free sign-up at "
        "platform.deepseek.com); "
        "you can switch to Kimi, GLM or "
        "others later in Settings.",
    "粘贴到这里，只需设置一次。":
        "Paste it here — set once.",
    "还没有 Key": "No Key yet",
    "没有 Key 我暂时没法回应你。\n"
    "也可以点「暂不设置」，"
    "之后在右上角设置里再填。":
        "I can't reply without a Key.\n"
        "You can also skip for now and "
        "add one later in Settings.",
    "认识一下": "Nice to meet you",
    "我该怎么称呼你？": "What should I call you?",
    "给我起个名字吧": "Give me a name",
    "她从哪里来": "Where she's from",
    "比如：上海": "e.g. Shanghai",
    "学生": "Student",
    "暂时想不好，先跳过": "Skip for now",

    # ---- 记忆窗口 ----

    "她记得的事": "What she remembers",

    # ---- 主题 ----

    "雾米": "Mist",
    "雾夜": "Night",

    # ---- 设置页补充 ----

    "保存设置": "Save settings",
    "更换头像": "Change avatar",
    "恢复出厂性格": "Reset personality",
    "她的名字": "Her name",
    "她的性格": "Her personality",
    "她的家乡": "Her hometown",
    "现居城市（选填）": "City (optional)",
    "她的身份": "Occupation",
    "你的名字或昵称": "Your name or nickname",
    "比如：成都": "e.g. Chengdu",

    "一个住在你电脑里的伙伴。\n"
    "她会记得你说过的话，\n"
    "也会在你忙碌时安静陪着你。\n\n"
    "开始之前，先做两件小事。":
        "A companion living in your computer.\n"
        "She remembers what you tell her\n"
        "and quietly keeps you company "
        "while you're busy.\n\n"
        "Two small things before we start.",

    "这些会变成她生活的一部分：\n"
    "填了现居城市她会聊天气，"
    "填了家乡她会记得家乡的事。"
    "都可以留空，由你决定。":
        "These become part of her life:\n"
        "with a city she'll chat about "
        "the weather; with a hometown "
        "she'll remember it.\n"
        "Both optional — up to you.",
}
