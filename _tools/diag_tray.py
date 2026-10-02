"""
直接问 Windows：系统托盘到底能不能用。

Ask Windows directly whether the notification area is available, instead of
trusting Qt's isSystemTrayAvailable().

Qt 在 Windows 上判断托盘可用性，依赖 Shell_NotifyIcon 相关的能力。
如果 Shell（explorer.exe）没在跑、或者被安全软件/组策略拦了，
Qt 会返回 False —— 而程序那边只看到"托盘不可用"，看不出是系统层面的问题。

This matters because Qt's check goes through the shell. If explorer.exe is
not running, or something is blocking the shell's IPC, Qt reports the tray
as unavailable -- and the app can only say "no tray", not why.

用法 / Usage
    python _tools/diag_tray.py
"""

import ctypes
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def section(title):
    print()
    print("-" * 62)
    print(title)
    print("-" * 62)


def shell_running():
    """
    Is Explorer (the shell that owns the notification area) running?

    拥有通知区域的 Shell（explorer.exe）在跑吗？
    """

    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq explorer.exe", "/NH"],
            capture_output=True, text=True, timeout=15,
        ).stdout
        return "explorer.exe" in out.lower()
    except Exception as exc:
        return f"(查不了: {exc})"


def find_window_class(class_name):
    """
    Does a top-level window of this class exist?

    存在这个类名的顶层窗口吗？

    The notification area lives in a window called Shell_TrayWnd. If that
    window is missing, there is literally nowhere for a tray icon to go.
    通知区域住在 Shell_TrayWnd 这个窗口里。这个窗口不在，托盘图标就没有容身之处。
    """

    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(class_name, None)
        return hwnd, bool(hwnd)
    except Exception as exc:
        return None, f"(查不了: {exc})"


def main():
    print("=" * 62)
    print("托盘诊断 / Tray diagnostics")
    print("=" * 62)

    section("1. 进程与 Shell")
    print("explorer.exe 在跑:", shell_running())

    section("2. 通知区域的窗口（托盘图标的容身之处）")
    for cls in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd", "NotifyIconOverflowWindow"):
        hwnd, ok = find_window_class(cls)
        print(f"  {cls:<28} hwnd={hwnd}  存在={ok}")

    section("3. Qt 怎么说")
    try:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QSystemTrayIcon
        app = QApplication([])
        print("  isSystemTrayAvailable :", QSystemTrayIcon.isSystemTrayAvailable())
        print("  supportsMessages      :", QSystemTrayIcon.supportsMessages())
    except Exception as exc:
        print("  查不了:", exc)

    section("4. 图标文件")
    try:
        from core.paths import resource_path
        p = resource_path("assets/echo.ico")
        print("  resource_path :", p)
        print("  绝对路径      :", Path(p).is_absolute())
        print("  存在          :", Path(p).exists())
        if Path(p).exists():
            print("  大小          :", Path(p).stat().st_size, "bytes")
            try:
                from PySide6.QtGui import QIcon
                ic = QIcon(p)
                print("  QIcon 为空    :", ic.isNull())
                print("  可用尺寸      :", [(s.width(), s.height()) for s in ic.availableSizes()])
            except Exception as exc:
                print("  QIcon 查不了:", exc)
    except Exception as exc:
        print("  查不了:", exc)

    section("5. 结论怎么看")
    print("""
  - explorer.exe 没在跑 / Shell_TrayWnd 不存在
        -> 系统层面就没有通知区域，任何托盘程序都出不来。
           这不是 Soulmate 的问题。重启 explorer 或重启系统。

  - Shell_TrayWnd 存在，但 Qt 的 isSystemTrayAvailable 是 False
        -> Shell 在跑但 Qt 拿不到托盘。常见原因：安全软件拦了、
           远程桌面会话、或 Shell 正在重启。换个会话/加白名单试试。

  - Qt 返回 True，QIcon 不为空
        -> 托盘应该能建起来。那问题在"图标被 Windows 折叠进隐藏区"：
           点任务栏的 ^ 展开，或到
           设置 -> 个性化 -> 任务栏 -> 其他系统托盘图标 里打开它。
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
