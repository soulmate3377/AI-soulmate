# core/backup.py
#
# 数据目录的每日自动备份。
#
# ==================================================
# 为什么要有这个东西
# ==================================================
#
# 她的全部记忆——聊天记录、向量库、
# 关系和人格状态——都只有数据目录
# （SoulmateData）里这一份。写入意外、
# 磁盘抖一下，就全没了。
#
# 所以让她每天启动时把自己
# 整个 zip 一份，保留最近 7 份。
# 备份放在数据目录旁边的
# SoulmateData_backups 里——必须在外面，
# 不然备份会把备份再备进去。
#
# 备份失败只记日志，
# 绝不拦着启动和聊天。

import logging
import zipfile

from datetime import datetime
from pathlib import Path

from core.paths import data_dir


log = logging.getLogger("echo.backup")


# 备份目录名（数据目录的兄弟目录）

BACKUP_DIR_NAME = "SoulmateData_backups"


# 保留最近几份

KEEP = 7


# 距上次备份超过 20 小时才再备。
# 不写整 24：如果每天只在
# 固定时段开她，严格的 24 小时
# 会一点点往后漂，隔天就跳空

INTERVAL_HOURS = 20


# 运行锁正在被占用，不碰

SKIP_NAMES = {"run.lock"}



def _backup_dir():

    d = (
        data_dir().parent
        / BACKUP_DIR_NAME
    )

    d.mkdir(
        parents=True,
        exist_ok=True,
    )

    return d



def _existing():

    # 文件名带时间戳，
    # 字典序就是时间序

    return sorted(
        _backup_dir().glob(
            "echo-backup-*.zip"
        )
    )



def run_if_due(force=False):

    """
    到点了就把整个数据目录
    zip 一份。

    返回备份文件路径；
    没到点没备就返回 None。
    force=True 无视间隔强制备一份
    （手动"立即备份"用）。
    """

    olds = _existing()


    if (

        not force

        and olds

        and (
            datetime.now()
            - datetime.fromtimestamp(
                olds[-1]
                .stat()
                .st_mtime
            )
        ).total_seconds()
        < INTERVAL_HOURS * 3600
    ):

        return None


    source = data_dir()


    dest = _backup_dir() / (

        "echo-backup-"

        # 精确到微秒：
        # 手动连点"立即备份"时
        # 同秒的文件名不能互相覆盖

        + datetime.now().strftime(
            "%Y%m%d-%H%M%S-%f"
        )

        + ".zip"
    )


    with zipfile.ZipFile(

        dest,

        "w",

        zipfile.ZIP_DEFLATED,

    ) as zf:

        for p in sorted(
            source.rglob("*")
        ):

            if not p.is_file():

                continue


            # 锁文件和写了一半的
            # 临时文件没有备份价值

            if p.name in SKIP_NAMES:

                continue


            if p.suffix == ".tmp":

                continue


            # 归档里带上 SoulmateData 这层
            # 目录名，解压即还原

            zf.write(

                p,

                p.relative_to(
                    source.parent
                ),

            )


    log.info(
        "数据已备份: %s",
        dest,
    )


    # 只留最近 KEEP 份，
    # 旧的清掉

    for extra in (
        _existing()[:-KEEP]
    ):

        try:

            extra.unlink()

        except OSError:

            pass


    return dest
