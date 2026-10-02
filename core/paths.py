# paths.py
#
# Data paths
# 数据路径管理
#
# Packaged as exe the launch dir is unpredictable, so all user data (memory,
# relationship, personality...) goes to the system user dir, not the launch dir.
# 打包成 exe 后启动目录不确定，用户数据（记忆、关系、人格……）统一写到系统用户目录。
# Windows: %APPDATA%\Soulmate\ ; elsewhere: ~/.soulmate/ ; ECHO_DATA_DIR overrides.
# Windows 是 %APPDATA%\Soulmate\；其他系统 ~/.soulmate/；可用 ECHO_DATA_DIR 覆盖
# （开发调试用；名字是历史遗留，懒得全改）。
# Old data under the legacy relative paths is migrated on first launch.
# 首次启动时自动把旧版相对路径下的数据迁移过来。

import os
import sys
import shutil

from pathlib import Path


APP_NAME = "Soulmate"

# Portable-mode data folder name (sits next to the exe, travels on the USB stick)
# 便携模式的数据文件夹名（放在 exe 旁边，跟着U盘走）

PORTABLE_DIR = "SoulmateData"



def _on_removable_drive(path):

    """
    判断路径是否在可移动磁盘上
    （Windows: GetDriveType == 2）
    """

    if sys.platform != "win32":

        return False

    try:

        import ctypes

        root = Path(path).anchor

        return (
            ctypes.windll.kernel32
            .GetDriveTypeW(root) == 2
        )

    except Exception:

        return False



def _migrate_from_appdata(target):

    """
    首次在U盘上运行时，
    把本机 %APPDATA% 里的旧数据
    整体带过来

    First run from a USB stick: bring the machine's old %APPDATA% data
    along, so the stick carries her memories instead of starting empty.

    Returns True when data was actually copied.
    真的搬了东西才返回 True。
    """

    try:

        old = Path(

            os.environ.get(

                "APPDATA",

                Path.home()
                / "AppData"
                / "Roaming"

            )

        ) / APP_NAME

        if old.exists() and not target.exists():

            shutil.copytree(old, target)

            return True

    except OSError:

        pass

    return False



def data_dir():


    override = os.environ.get(
        "ECHO_DATA_DIR"
    )


    if override:

        base = Path(override)

    else:

        # Portable mode: SoulmateData already sits next to the exe, or the exe
        # runs from a removable drive like a USB stick. Either way the data
        # follows the program instead of the machine.
        # 便携模式：exe 旁边已有 SoulmateData，或者 exe 在U盘等可移动磁盘上，
        # 这两种情况数据都是跟着程序走，而不是跟着机器走，
        # 换电脑不丢。

        base = None

        if getattr(sys, "frozen", False):

            exe_dir = Path(
                sys.executable
            ).parent

            portable = exe_dir / PORTABLE_DIR

            if portable.exists():

                base = portable

            else:

                # Portable first: if a packaged copy can write next to
                # itself, keep the data there. A visible SoulmateData folder
                # beside the exe is what people can find and back up; the
                # %APPDATA% fallback is a hidden directory they will never
                # stumble on. Only give up on portable when the write
                # actually fails (Program Files, read-only drive).
                # 便携优先：打包后的程序只要能在自己旁边写，就把数据放那儿。
                # exe 旁边一个看得见的 SoulmateData 才是用户找得到、备份得了的；
                # %APPDATA% 那个隐藏目录没人会翻到。只有真的写不进去
                # （比如装在 Program Files、只读盘）才退回 APPDATA。
                try:

                    portable.mkdir(parents=True)

                    if not _migrate_from_appdata(portable):

                        # Nothing old to bring over, and an empty folder would
                        # just look like leftover junk. Recording the migration
                        # below recreates it when a write really happens.
                        # 没有旧数据可搬，空目录只会像残留垃圾。下面真正写入时
                        # 会自动重建。
                        try:

                            portable.rmdir()

                        except OSError:

                            pass

                    base = portable

                except OSError:

                    # Not writable next to the exe; fall through to %APPDATA%.
                    # exe 旁边不可写，退回 %APPDATA%。
                    base = None

        if base is None and not getattr(
            sys, "frozen", False
        ):

            # =========================
            # Running from source follows the same rule: a SoulmateData sitting next
            # to the project is used directly, so shortcuts and autostart need no
            # env var, and nothing gets scattered into %APPDATA%.
            # 源码运行是同一条规矩：项目目录旁边躺着 SoulmateData 就直接用它，
            # 这样快捷方式和开机自启都不用再设环境变量，
            # 数据也不会写散到 %APPDATA% 里。
            # =========================

            proj = (
                Path(__file__)
                .resolve().parent.parent
            )

            for cand in (

                proj / PORTABLE_DIR,

                proj.parent / PORTABLE_DIR,

            ):

                if cand.exists():

                    base = cand

                    break

        if base is None:

            if sys.platform == "win32":

                base = Path(

                    os.environ.get(

                        "APPDATA",

                        Path.home()
                        / "AppData"
                        / "Roaming"

                    )

                ) / APP_NAME

            else:

                base = Path.home() / ".soulmate"


    base.mkdir(
        parents=True,
        exist_ok=True
    )

    return base



def data_path(rel):


    p = data_dir() / rel

    p.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    return str(p)



def resolve_data_file(rel):


    """

    返回数据文件的正式路径。
    旧版相对路径存在而新位置没有时，
    自动把旧数据迁移过来。

    """


    new = Path(data_path(rel))

    legacy = Path(rel)


    if (

        not new.exists()

        and legacy.exists()

    ):

        try:

            if (

                legacy.resolve()
                != new.resolve()

            ):

                shutil.copy2(
                    legacy,
                    new
                )

        except OSError:

            pass


    return str(new)



def resource_path(rel):


    """

    只读资源（打包进 exe 的文件）
    PyInstaller 运行时在 _MEIPASS 下

    Read-only assets bundled into the exe; under PyInstaller they live in
    _MEIPASS.

    交付一个绝对路径。以前兜底直接返回相对的 rel，能不能找到文件就完全
    取决于当前工作目录——用快捷方式启动、或"起始位置"不是项目目录时，
    图标会静默变成空图标，托盘图标就没了。现在按顺序试：_MEIPASS、
    当前目录、项目根目录，都不行才退回原样。

    Always hands back an absolute path where one exists. The old fallback
    returned the relative name as-is, so whether the file was found depended
    entirely on the working directory: launched from a shortcut with a
    different "start in" folder, icons silently became null and the tray
    icon vanished. Now it tries _MEIPASS, then the cwd, then the repo root,
    and only then gives up.

    """


    p = Path(rel)


    if p.is_absolute():

        return str(p)


    candidates = []


    base = getattr(
        sys,
        "_MEIPASS",
        None
    )


    if base:

        candidates.append(
            Path(base) / rel
        )


    candidates.append(Path.cwd() / rel)


    # 源码运行：相对路径是相对项目根，不是相对当前目录
    # Running from source: the relative path is anchored at the repo root,
    # not at whatever the working directory happens to be.

    candidates.append(

        Path(__file__)
        .resolve().parent.parent
        / rel

    )


    for cand in candidates:

        try:

            if cand.exists():

                return str(cand)

        except OSError:

            continue


    return rel



def resolve_asset(path):


    """

    解析头像等资源：
    依次尝试 绝对路径 / 当前目录 /
    数据目录 / 程序内置资源

    """


    if not path:

        return path


    p = Path(path)

    if p.is_absolute() and p.exists():

        return str(p)

    if p.exists():

        return str(p)


    d = data_dir() / path

    if d.exists():

        return str(d)


    return resource_path(path)
