# core/backup.py
# Daily zip of the whole data dir on startup, keep the newest 7.
# Her memories — chat log, vector index, relationship, personality — live in
# SoulmateData only, so one bad write or a disk hiccup loses everything. Backups
# sit beside it in SoulmateData_backups, outside the data dir, otherwise the backup
# would back itself up. Failures only get logged, never block startup or chatting.
# 数据目录的每日自动备份，保留最近 7 份。
# 她的记忆——聊天记录、向量库、关系、人格——只有 SoulmateData 这一份，
# 写入意外或磁盘抖一下就全没了。备份放在旁边的 SoulmateData_backups，
# 必须在数据目录外面，不然备份会把备份自己再备进去。
# 备份失败只记日志，绝不拦着启动和聊天。

import logging
import zipfile
from datetime import datetime
from pathlib import Path
from core.paths import data_dir
log = logging.getLogger("echo.backup")

# Backup dir name (sibling of the data dir)
# 备份目录名（数据目录的兄弟目录）
BACKUP_DIR_NAME = "SoulmateData_backups"

# How many backups to keep
# 保留最近几份
KEEP = 7

# 20h, not a strict 24h: if she only runs at a fixed hour each day, a 24h window
# drifts later and later until a whole day gets skipped.
# 用 20 小时而不是整 24：她每天只在固定时段上线的话，24 小时窗口会一直往后漂，
# 漂到某天整个跳空。
INTERVAL_HOURS = 20

# The lock may be held by a running instance, leave it alone
# 运行锁可能正被实例占用，不碰
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
    # Timestamped names, so lexicographic sort is time order
    # 文件名带时间戳，字典序就是时间序
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
        # Microseconds, so two 'back up now' clicks in the same second don't overwrite
        # each other.
        # 精确到微秒：同一秒内连点两次“立即备份”不会互相覆盖。
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

            # The lock file and half-written .tmp files aren't worth archiving
            # 锁文件和写了一半的 .tmp 文件没有备份价值
            if p.name in SKIP_NAMES:
                continue
            if p.suffix == ".tmp":
                continue

            # Keep the SoulmateData level inside the zip, so extracting restores it
            # 归档里带上 SoulmateData 这层目录，解压即还原
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

    # Keep only the newest KEEP, drop the older ones
    # 只留最近 KEEP 份，旧的清掉
    for extra in (
        _existing()[:-KEEP]
    ):
        try:
            extra.unlink()
        except OSError:
            pass
    return dest
