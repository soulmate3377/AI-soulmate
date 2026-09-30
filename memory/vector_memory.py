# vector_memory.py
#
# 向量记忆。
#
# 每条记忆是一条结构化记录：
#
#   {
#     "text":    原文
#     "summary": 一句话摘要（检索/展示用）
#     "role":    user / echo
#     "kind":    statement / promise / preference / fact
#     "time":    记录时间
#     "importance":  重要度 0~1（入库时定）
#     "last_access": 上次被想起的时间
#     "recall":  被想起过几次
#   }
#
# 旧版存的是纯字符串列表，
# 读取时自动升级，不会丢数据。
#
# 记忆面板可以删除某几条；
# faiss 的扁平索引不支持原地删除，
# 所以删完直接按剩下的重建。
#
# ==================================================
# 遗忘曲线（2026-08-31 加）
#
# 之前的检索是纯向量距离：
# 三个月前的「今天中午吃了面」
# 和三小时前的「我妈下周手术」
# 只要文本像，就平起平坐。
# 真人不这么记事。
#
# 艾宾浩斯的形状：R = exp(-t / τ)
#   t = 距上次想起的天数
#   τ = 记忆的"保质期"，由重要度决定：
#     importance >= 0.75 → 240 天（手术、大事）
#     >= 0.5             → 60 天（喜好、习惯）
#     >= 0.3             → 21 天（有情绪的日常）
#     其他               → 7 天（闲聊）
#
# 被想起一次 = 复习一次：
#   last_access 刷新 + recall+1，
#   且 τ × (1 + 0.15×recall)，
#   常被提起的事越来越不容易忘（上限 3 倍）。
#
# 衰减有下限 0.05：很久远的旧事
# 几乎不会冒出来，但偶尔会——
# 像人突然想起一件很久的事。
#
# 只衰减，不删除：
#   "忘掉"是检索排名往后掉，
#   不是记录消失。被再次提及时
#   它还能立刻回来。
# ==================================================

import os
import json
import math

from datetime import datetime

import faiss

import numpy as np

# sentence_transformers 不在这里导入：
# 它会拖起整个 torch，
# 光导入就要几十秒，
# 是"双击之后半天没反应"的元凶。
# 真正用到向量时才付这个钱，
# 见 get_model()。

from core.paths import (
    resolve_data_file,
    resource_path
)


# 完全一样的原文不重复入库

_DEDUP_WINDOW = 20

# 检索时先多取几倍候选，
# 按遗忘曲线重排后再截 top_k

_OVERSAMPLE = 4

# 衰减的底线：再久远的记忆
# 也保留一丝被想起的可能

_RETENTION_FLOOR = 0.05

# 每被想起一次，保质期乘上
# (1 + _RECALL_BONUS)，
# 上限 _RECALL_MAX 倍

_RECALL_BONUS = 0.15

_RECALL_MAX = 3.0


def _now_text():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _parse_time(text):
    """
    记录时间 -> datetime。
    解析不了当「很久以前」处理，
    让它衰减到接近下限，
    而不是当成今天。
    """

    try:

        return datetime.strptime(
            (text or "").strip(),
            "%Y-%m-%d %H:%M:%S"
        )

    except ValueError:

        try:

            return datetime.strptime(
                (text or "").strip()[:10],
                "%Y-%m-%d"
            )

        except ValueError:

            return None


def _halflife_days(importance):
    """
    按重要度取保质期 τ（天）。
    """

    if importance >= 0.75:

        return 240.0

    if importance >= 0.5:

        return 60.0

    if importance >= 0.3:

        return 21.0

    return 7.0


def _retention(record, now=None):
    """
    这条记忆此刻的保留率 0~1。
    """

    imp = record.get(
        "importance", 0.5
    )

    tau = _halflife_days(imp)

    recall = int(
        record.get("recall", 0) or 0
    )

    if recall > 0:

        tau *= min(
            _RECALL_MAX,
            1.0 + _RECALL_BONUS * recall,
        )

    when = _parse_time(
        record.get("last_access")
        or record.get("time")
    )

    if when is None:

        return _RETENTION_FLOOR

    now = now or datetime.now()

    days = max(
        0.0,
        (now - when).total_seconds()
        / 86400.0
    )

    r = math.exp(-days / max(tau, 1e-6))

    return max(
        _RETENTION_FLOOR,
        min(1.0, r)
    )


def _upgrade(raw):

    """
    把旧版的字符串记忆
    升级成结构化记录。
    """

    out = []

    for item in raw or []:

        if isinstance(item, dict):

            record = {
                "text": item.get(
                    "text", ""
                ),
                "summary": item.get(
                    "summary"
                )
                or item.get("text", ""),
                "role": item.get(
                    "role", "user"
                ),
                "kind": item.get(
                    "kind", "statement"
                ),
                "time": item.get(
                    "time", ""
                ),

                # 旧记录没有这三个字段：
                # importance 给默认 0.5，
                # last_access 落到记录时间
                # （从今天开始衰减，
                #  对老记忆是宽容的起点），
                # recall 从 0 起。

                "importance": float(
                    item.get(
                        "importance", 0.5
                    ) or 0.5
                ),
                "last_access": (
                    item.get("last_access")
                    or item.get("time", "")
                ),
                "recall": int(
                    item.get("recall", 0) or 0
                ),
            }

        else:

            record = {
                "text": str(item),
                "summary": str(item),
                "role": "user",
                "kind": "statement",
                "time": "",
                "importance": 0.5,
                "last_access": "",
                "recall": 0,
            }

        if record["text"]:

            out.append(record)

    return out


_MODEL = None


def _model_path():

    """
    按顺序找 embedding 模型：
    1. 环境变量 ECHO_EMBEDDING_MODEL
    2. 打包进程序的模型文件
    3. 本机 modelscope 缓存
    4. 按模型名在线下载
    """

    bundled = resource_path(
        "models/bge-small-zh-v1.5"
    )

    default_local = os.path.expandvars(
        r"%USERPROFILE%\.cache\modelscope\models"
        r"\AI-ModelScope--bge-small-zh-v1.5\snapshots\master"
    )

    model_path = os.environ.get(
        "ECHO_EMBEDDING_MODEL"
    )

    if not model_path:

        if os.path.exists(bundled):

            model_path = bundled

            # 内置模型不需要联网检查，
            # 防止打包环境下卡住或报错

            os.environ.setdefault(
                "HF_HUB_OFFLINE", "1"
            )

            os.environ.setdefault(
                "TRANSFORMERS_OFFLINE", "1"
            )

        elif os.path.exists(
            default_local
        ):

            model_path = default_local

        else:

            model_path = (
                "BAAI/bge-small-zh-v1.5"
            )

    return model_path


def get_model():

    """
    全局共享一个 embedding 模型。

    Brain 里会同时创建好几个
    VectorMemory（检索、记忆管道各一个），
    每个都加载一遍的话
    启动时间和内存都要翻倍。
    """

    global _MODEL

    if _MODEL is None:

        # 延迟导入：
        # 第一次真正要用向量才加载
        # torch，启动路径不背这个包袱

        from sentence_transformers import (
            SentenceTransformer,
        )

        _MODEL = SentenceTransformer(
            _model_path()
        )

    return _MODEL


class VectorMemory:

    def __init__(self):

        self.model = get_model()

        # 向量维度

        self.dimension = 512

        # 存储路径（用户数据目录，
        # 旧数据自动迁移）

        self.index_file = resolve_data_file(
            "memory/vector_store/memory.index"
        )

        self.data_file = resolve_data_file(
            "memory/vector_store/memory.json"
        )

        # 初始化索引

        if os.path.exists(
            self.index_file
        ):

            self.index = faiss.read_index(
                self.index_file
            )

        else:

            self.index = faiss.IndexFlatL2(
                self.dimension
            )

        # 初始化文本数据

        raw = []

        if os.path.exists(
            self.data_file
        ):

            with open(
                self.data_file,
                "r",
                encoding="utf-8"
            ) as f:

                try:

                    raw = json.load(f)

                except ValueError:

                    raw = []

        self.memories = _upgrade(raw)

        # 索引和记录对不上就以记录为准重建，
        # 免得检索返回错位的内容

        if (
            self.index.ntotal
            != len(self.memories)
        ):

            self._rebuild(self.memories)


    # =========================
    # 添加记忆
    # =========================

    def add_memory(
        self,
        text,
        summary=None,
        role="user",
        kind="statement",
        importance=0.5
    ):

        """
        存一条记忆。
        importance 0~1：
        决定这条记忆的保质期
        （见文件头的遗忘曲线）。
        返回记录本身；
        重复或空内容返回 None。
        """

        text = (text or "").strip()

        if not text:

            return None

        # 最近几条里已经有一样的原文就不存

        recent = [
            m["text"]
            for m in self.memories[
                -_DEDUP_WINDOW:
            ]
        ]

        if text in recent:

            return None

        try:

            importance = min(
                1.0,
                max(
                    0.0,
                    float(importance)
                ),
            )

        except (TypeError, ValueError):

            importance = 0.5

        now = _now_text()

        record = {

            "text": text,

            "summary": (
                summary or ""
            ).strip() or text,

            "role": role,

            "kind": kind,

            "time": now,

            # 新记忆第一天是满的，
            # 从现在开始忘

            "importance": importance,

            "last_access": now,

            "recall": 0,

        }

        vector = self.model.encode(
            [text]
        )

        vector = np.array(
            vector
        ).astype("float32")

        self.index.add(vector)

        self.memories.append(record)

        self.save()

        return record


    # =========================
    # 搜索记忆
    # -------------------------
    # 两层排序：
    #   1. 向量距离粗筛（取 top_k×4 候选）
    #   2. 相关度 × 保留率 重排，
    #      只留此刻还没"忘掉"的
    #
    # 被选中的记忆算"想起了一次"：
    # last_access 刷新、recall+1。
    # 这是遗忘曲线的另一半——
    # 复习让记忆保鲜。
    # =========================

    def search(self, query, top_k=3):

        """
        返回最相关的若干条完整记录。
        结果按 相关度×保留率 从高到低。
        """

        if (
            not self.memories
            or not (query or "").strip()
        ):

            return []

        vector = self.model.encode(
            [query]
        )

        vector = np.array(
            vector
        ).astype("float32")

        top_k = min(
            top_k, len(self.memories)
        )

        # 粗筛多取一些，
        # 给衰减留出淘汰空间

        fetch = min(
            len(self.memories),
            top_k * _OVERSAMPLE,
        )

        distance, index = (
            self.index.search(
                vector, fetch
            )
        )

        scored = []

        for rank, i in enumerate(
            index[0]
        ):

            if not (
                0 <= i < len(self.memories)
            ):

                continue

            record = self.memories[i]

            # L2 距离 -> 相似度 0~1

            d = float(
                distance[0][rank]
            )

            similarity = 1.0 / (
                1.0 + d
            )

            keep = _retention(record)

            scored.append(
                (
                    similarity * keep,
                    i,
                )
            )

        scored.sort(
            key=lambda t: t[0],
            reverse=True
        )

        result = []

        touched = False

        for _, i in scored[:top_k]:

            record = (
                self.memories[i]
            )

            # 想起了一次：
            # 复习效应

            record["recall"] = (
                int(
                    record.get(
                        "recall", 0
                    ) or 0
                )
                + 1
            )

            record["last_access"] = (
                _now_text()
            )

            touched = True

            result.append(record)

        # 只写 json，不动 faiss 索引
        # （索引里向量没变，
        #  重写一遍纯浪费）

        if touched:

            self._save_data()

        return result


    # =========================
    # 全部记忆（记忆面板用）
    # =========================

    def all_records(self):

        return list(self.memories)


    # =========================
    # 删除记忆，然后重建索引
    # =========================

    def delete(self, indices):

        """
        indices 是要删掉的下标集合。
        """

        drop = set(indices or [])

        if not drop:

            return 0

        keep = [

            m
            for i, m in enumerate(
                self.memories
            )

            if i not in drop

        ]

        removed = (
            len(self.memories) - len(keep)
        )

        if removed:

            self._rebuild(keep)

        return removed


    def clear(self):

        removed = len(self.memories)

        if removed:

            self._rebuild([])

        return removed


    def _rebuild(self, records):

        """
        按给定的记录重建整个索引。
        faiss 的扁平索引删不掉单条，
        重建是最稳的做法。
        """

        self.index = faiss.IndexFlatL2(
            self.dimension
        )

        self.memories = list(records)

        if self.memories:

            vectors = self.model.encode(

                [
                    m["text"]
                    for m in self.memories
                ]

            )

            vectors = np.array(
                vectors
            ).astype("float32")

            self.index.add(vectors)

        self.save()


    # =========================
    # 保存
    # =========================

    def save(self):

        faiss.write_index(
            self.index,
            self.index_file
        )

        self._save_data()


    # =========================
    # 只写 json（检索想起记忆时用）：
    # 向量没变，faiss 索引不必重写
    # =========================

    def _save_data(self):

        with open(
            self.data_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.memories,
                f,
                ensure_ascii=False,
                indent=4
            )
