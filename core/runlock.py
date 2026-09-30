# runlock.py
#
# 防双开锁。
#
# ==================================================
# 为什么需要
# --------------------------------------------------
# 桌面版和网页端服务共用同一个
# SoulmateData 目录，两边同时开的话
# conversations.json 会互相覆盖，
# 中间那条消息就丢了。
#
# 所以：谁先启动谁拿锁，
# 第二个来的直接拒绝启动。
# ==================================================
# 锁的形态
# --------------------------------------------------
# SoulmateData/run.lock，一行文本：
#     <pid>|<kind>
# kind 是 desktop / web，
# 用于提示「现在开的是哪个」。
#
# 锁文件不删除也不可怕：
# 下次启动会读出 pid，
# 探测那个进程还活着没有——
# 死了（崩溃 / 被强杀）就接管。
# ==================================================

import atexit
import os
import sys

from core.paths import data_dir


LOCK_NAME = "run.lock"

# Windows 进程还在运行的退出码
_STILL_ACTIVE = 259


def _lock_path():
    return data_dir() / LOCK_NAME


def _pid_alive(pid):
    """
    探测 pid 对应的进程是否还活着。
    """

    if not pid or pid <= 0:
        return False

    if sys.platform == "win32":

        try:
            import ctypes

            # 只查询，不干扰
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

            handle = (
                ctypes.windll
                .kernel32
                .OpenProcess(
                    0x1000,
                    False,
                    pid,
                )
            )

            if not handle:
                return False

            try:
                code = (
                    ctypes.c_ulong()
                )

                ok = (
                    ctypes.windll
                    .kernel32
                    .GetExitCodeProcess(
                        handle,
                        ctypes.byref(
                            code
                        ),
                    )
                )

                return bool(
                    ok
                    and code.value
                    == _STILL_ACTIVE
                )

            finally:
                ctypes.windll \
                    .kernel32 \
                    .CloseHandle(
                        handle
                    )

        except Exception:
            # 探测不了就当活着，
            # 宁可误拒也不冒险
            return True

    else:

        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _read_lock():
    """
    读出锁里的 (pid, kind)。
    没有锁或格式坏了返回 None。
    """

    try:
        with open(
            _lock_path(),
            "r",
            encoding="utf-8",
        ) as f:
            parts = (
                f.read()
                .strip()
                .split("|")
            )

        pid = int(parts[0])
        kind = parts[1] if len(
            parts
        ) > 1 else "?"

        return pid, kind

    except (
        OSError,
        ValueError,
        IndexError,
    ):
        return None


_KIND_LABEL = {
    "desktop": "桌面版 Soulmate",
    "web": "网页端服务",
}


def kind_label(kind):
    return _KIND_LABEL.get(
        kind, kind or "另一个 Soulmate"
    )


def acquire(kind):
    """
    尝试拿锁。

    返回 (True, None) 拿到；
    (False, 正在运行的描述) 没拿到。

    自己重入（同 pid）视为拿到，
    正常重启流程不受影响。
    """

    mine = os.getpid()

    held = _read_lock()

    if held is not None:

        pid, old_kind = held

        if pid != mine and _pid_alive(
            pid
        ):
            return False, (
                kind_label(old_kind)
            )

    # 没锁 / 持有者已死 / 是自己：
    # 写入自己的锁

    try:
        with open(
            _lock_path(),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(
                f"{mine}|{kind}"
            )
    except OSError:
        # 数据目录不可写：
        # 拿不到锁就没法防双开，
        # 但也不能因此不让用
        return True, None

    atexit.register(release)

    return True, None


def release():
    """
    退出时删掉自己的锁。
    是别人的锁就不动。
    """

    try:
        held = _read_lock()

        if held is None:
            return

        pid, _ = held

        if pid == os.getpid():
            os.remove(_lock_path())

    except OSError:
        pass
