# companion.py
# Headless entry point — same brain as the GUI (python main.py).
# Soulmate 的无界面入口，和 GUI（python main.py）是同一个大脑。
#
# when to use it
# 什么时候用这个
#   python companion.py                 interactive chat in the terminal
#   python companion.py "..."           single shot: one line in, reply, exit
#   python companion.py --apply-persona write config/persona.yaml into her profile
# 用法：直接跑就是终端聊天；带一句话是单条模式（回完就退出）；
# --apply-persona 把 config/persona.yaml 写进她的档案。
#
# Memory, personality and proactive messages are shared, and both take the
# same run lock — only one at a time, or they overwrite each other's chat log.
# 记忆、人格、主动消息全部共用；两边共用同一把运行锁，同一时刻只能开一个，
# 同时开会互相覆盖聊天记录。
#
# Usable as a library too: grab a Brain(), then think_stream() is her.
# 这个文件也是给别的项目当库用的样板：
# Brain() 拿到手，think_stream() 就是她。

import sys
import time
import threading

from datetime import datetime


# ==================================================
# persona.yaml -> her profile
# 把 persona.yaml 写进她的档案

def _load_persona():

    """
    读 config/persona.yaml。
    没有文件 / 解析失败都返回空 dict。
    """

    try:

        import yaml

        from pathlib import Path

        p = (
            Path(__file__)
            .resolve().parent
            / "config"
            / "persona.yaml"
        )

        if not p.exists():

            return {}

        return (
            yaml.safe_load(
                p.read_text(
                    encoding="utf-8"
                )
            )
            or {}
        )

    except Exception:

        return {}


def apply_persona():

    """
    把 persona.yaml 里的基础设定
    写进她的档案。
    只覆盖这几个字段，
    运行时自己学会的东西不动。
    """

    persona = _load_persona()

    if not persona:

        print(
            "没找到 config/persona.yaml"
            "（或文件格式不对）"
        )

        return 1


    from core.identity import (
        Identity,
    )

    ident = Identity()


    meta = (
        persona.get("meta") or {}
    )

    ident_part = (
        persona.get("identity") or {}
    )


    # yaml key -> profile key
    # 字段映射：yaml 键 → 档案键

    plan = []


    if str(
        meta.get("name") or ""
    ).strip():

        plan.append((
            "echo_name",
            str(meta["name"]).strip(),
        ))


    if str(
        meta.get("occupation") or ""
    ).strip():

        plan.append((
            "occupation",
            str(meta["occupation"]).strip(),
        ))


    for key in (

        "hometown",
        "current_city",
        "personality",
        "backstory",
        "speaking_style",
        "emotional_pattern",
        "values",
        "quirks",
        "boundaries",

    ):

        value = str(
            ident_part.get(key) or ""
        ).strip()

        if value:

            plan.append((key, value))


    if not plan:

        print(
            "persona.yaml 里没有可写的字段"
            "（都是空的），档案未改动。"
        )

        return 0


    for key, value in plan:

        ident.update(key, value)

        print(f"  {key} = {value}")


    print(
        f"完成：{len(plan)} 项写入了她的档案。"
    )


    return 0



# ==================================================
# chat
# 聊天

def _stream_reply(brain, text):

    """
    流式打印她的回复，
    返回完整回复文本。
    """

    parts = []

    for delta in brain.think_stream(
        text
    ):

        parts.append(delta)

        print(
            delta,
            end="",
            flush=True,
        )


    print()

    return "".join(parts)



def chat_loop(brain, cm):

    """
    交互聊天：
    每句话走和 GUI 完全相同的
    思考管线（理解→说话→回看→记忆）。
    """

    from core.identity import (
        Identity,
    )

    from core.proactive_guard import (
        ProactiveGuard,
    )

    her = (
        Identity().get("echo_name")
        or "Soulmate"
    )

    guard = ProactiveGuard()


    print()
    print(f"—— {her} ——")
    print(
        "在终端里和她聊天。"
        "她会自己主动开口"
        "（出现〔她主动〕标记）。\n"
        "输入 /exit 结束。"
    )
    print()


    # Proactive messages: a background thread asks the guard once a minute.
    # If she speaks up, print it and log it, then reflect on it as usual.
    # 主动消息：后台线程每分钟问一次守门人；开口了就打出来、落进聊天记录，
    # 事后照常走回看。

    def proactive_loop():

        while True:

            time.sleep(60)

            try:

                result = (
                    brain.scheduler
                    .run_once()
                )

            except Exception:

                continue


            text = (
                (result or {}).get("text")
                or ""
            ).strip()


            if not text:

                continue


            stamp = datetime.now().strftime(
                "%H:%M"
            )

            print(
                f"\n〔{her} 主动 {stamp}〕\n"
                f"{text}\n"
            )

            cm.add_message(
                "echo", text
            )


            try:

                brain.reflect_proactive(
                    text
                )

            except Exception:

                pass



    threading.Thread(

        target=proactive_loop,

        daemon=True,

    ).start()



    while True:

        try:

            text = input("你 > ").strip()

        except (EOFError, KeyboardInterrupt):

            print()

            break


        if not text:

            continue


        if text in ("/exit", "/quit"):

            break


        try:

            guard.note_user_message(
                text
            )

        except Exception:

            pass


        cm.add_message(
            "user", text
        )


        print(
            f"{her} > ",
            end="",
            flush=True,
        )


        try:

            reply = _stream_reply(
                brain, text
            )

        except Exception as e:

            print(
                f"\n（出了点问题：{e}）"
            )

            continue


        cm.add_message(
            "echo", reply
        )


    print(
        "她还在，下次见。"
        "（聊天记录已保存）"
    )



def main():


    args = sys.argv[1:]


    if "--apply-persona" in args:

        sys.exit(
            apply_persona()
        )


    # Run lock — the same one the desktop app takes.
    # Two at once would overwrite each other's chat log.
    # 运行锁：和桌面版共用同一把，
    # 同时开会互相覆盖聊天记录。
    # ==================================================

    from core.runlock import (
        acquire,
    )

    ok, running = acquire(
        "desktop"
    )

    if not ok:

        print(
            f"另一个 Soulmate（{running}）"
            "正在运行，先关掉再开。"
        )

        sys.exit(1)


    from memory.conversation import (
        ConversationManager,
    )

    cm = ConversationManager()


    # Single-shot mode: non-flag command-line text is what we send her.
    # 单条模式：命令行参数里带的话就是要说的

    single = " ".join(
        a for a in args
        if not a.startswith("--")
    ).strip()


    from core.brain import Brain


    try:

        brain = Brain()

    except Exception as e:

        print(
            f"她没能醒来：{e}"
        )

        sys.exit(1)


    if single:

        cm.add_message(
            "user", single
        )


        try:

            reply = _stream_reply(
                brain, single
            )

        except Exception as e:

            print(
                f"（出了点问题：{e}）"
            )

            sys.exit(1)


        cm.add_message(
            "echo", reply
        )


        return


    chat_loop(brain, cm)



if __name__ == "__main__":

    main()
