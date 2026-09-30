# storage.py
#
# Local storage shared by the whole project
# 全项目统一的本地存储
#
# 1. Atomic JSON I/O: write a temp file then replace it, so a power cut or a
#    crash never leaves half a file behind.
# 1. JSON 原子读写：先写临时文件再替换，中途断电/崩溃不会留下半个文件。
#
# 2. DPAPI encryption for the API key: Windows encrypts per user, no extra
#    password; copied to another machine or user it won't decrypt, just re-enter.
# 2. API Key 的 DPAPI 加密：Windows 按当前用户加密，不需要额外密码；
#    文件拷到别的电脑/别的用户解不开，换机时在设置里重填即可。
#
# 3. One entry point for config.json: merge-style writes keep unrelated fields.
# 3. config.json 的统一入口：合并式读写，不覆盖无关字段。

import json
import os
import base64

from core.paths import data_dir


# ==================================================
# JSON atomic read/write
# JSON 原子读写

def read_json(path, default=None):

    try:

        with open(
            path, "r", encoding="utf-8"
        ) as f:

            return json.load(f)

    except (OSError, ValueError):

        return default


def write_json(path, data):

    path = str(path)

    os.makedirs(

        os.path.dirname(path)
        or ".",

        exist_ok=True

    )

    tmp = path + ".tmp"

    with open(
        tmp, "w", encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )

    os.replace(tmp, path)


# ==================================================
# DPAPI encrypt/decrypt (Windows)
# DPAPI 加解密（Windows）

def _dpapi_available():

    return os.name == "nt"


def protect_text(text):

    """
    加密字符串，返回 base64。
    失败时返回 None，
    调用方决定退路。
    """

    if not text or not _dpapi_available():

        return None

    try:

        import ctypes
        import ctypes.wintypes as wt

        class DATA_BLOB(ctypes.Structure):

            _fields_ = [
                ("cbData", wt.DWORD),
                ("pbData", ctypes.POINTER(
                    ctypes.c_char
                )),
            ]

        raw = text.encode("utf-8")

        blob_in = DATA_BLOB(
            len(raw),
            ctypes.cast(
                ctypes.c_char_p(raw),
                ctypes.POINTER(ctypes.c_char)
            ),
        )

        blob_out = DATA_BLOB()

        ok = (
            ctypes.windll.crypt32
            .CryptProtectData(

                ctypes.byref(blob_in),
                None,
                None,
                None,
                None,
                0,
                ctypes.byref(blob_out),

            )
        )

        if not ok:

            return None

        try:

            encrypted = ctypes.string_at(

                blob_out.pbData,
                blob_out.cbData,

            )

        finally:

            ctypes.windll.kernel32.LocalFree(
                blob_out.pbData
            )

        return base64.b64encode(
            encrypted
        ).decode("ascii")

    except Exception:

        return None


def unprotect_text(blob_b64):

    """
    解密 base64 密文。
    解不开（换电脑/换用户/损坏）
    返回 None。
    """

    if (
        not blob_b64
        or not _dpapi_available()
    ):

        return None

    try:

        import ctypes
        import ctypes.wintypes as wt

        class DATA_BLOB(ctypes.Structure):

            _fields_ = [
                ("cbData", wt.DWORD),
                ("pbData", ctypes.POINTER(
                    ctypes.c_char
                )),
            ]

        raw = base64.b64decode(
            blob_b64
        )

        blob_in = DATA_BLOB(
            len(raw),
            ctypes.cast(
                ctypes.c_char_p(raw),
                ctypes.POINTER(ctypes.c_char)
            ),
        )

        blob_out = DATA_BLOB()

        ok = (
            ctypes.windll.crypt32
            .CryptUnprotectData(

                ctypes.byref(blob_in),
                None,
                None,
                None,
                None,
                0,
                ctypes.byref(blob_out),

            )
        )

        if not ok:

            return None

        try:

            plain = ctypes.string_at(

                blob_out.pbData,
                blob_out.cbData,

            )

        finally:

            ctypes.windll.kernel32.LocalFree(
                blob_out.pbData
            )

        return plain.decode("utf-8")

    except Exception:

        return None


# ==================================================
# Provider settings (base_url + three model names)
# 服务商配置（base_url + 三个模型名）
# Plaintext in config.json: the model names and endpoint aren't sensitive,
# only the key is encrypted.
# 明文存 config.json：模型名和接口地址不敏感，只有 Key 走加密
# ==================================================

# Fields allowed to be persisted / 允许落盘的字段白名单

_LLM_FIELDS = (
    "api_base",
    "model_think",
    "model_reflect",
    "model_speak",
)


def load_llm_settings():

    """
    返回已保存的服务商配置，
    没配过的字段不出现。
    """

    cfg = load_config()

    return {
        k: cfg[k]
        for k in _LLM_FIELDS
        if cfg.get(k)
    }


def save_llm_settings(
    api_base=None,
    models=None,
):

    """
    合并式写入。

    字段语义：
    传非空值 → 生效；
    传空值   → 从配置里移除，
               回到出厂默认；
    不传     → 保持原值。
    models 是
    {"think":..., "reflect":..., "speak":...}
    的子集即可。
    """

    cfg = load_config()


    if api_base is not None:

        value = str(api_base).strip()

        if value:

            cfg["api_base"] = value

        else:

            cfg.pop(
                "api_base", None
            )


    for role, value in (
        models or {}
    ).items():

        field = "model_" + role

        if field not in _LLM_FIELDS:

            continue

        value = str(value).strip()

        if value:

            cfg[field] = value

        else:

            cfg.pop(
                field, None
            )

    save_config(cfg)


# ==================================================
# config.json entry point
# config.json 统一入口

def _config_file():

    return data_dir() / "config.json"


def load_config():

    cfg = read_json(
        _config_file(), {}
    )

    return cfg or {}


def save_config(cfg):

    write_json(_config_file(), cfg)


# ==================================================
# API key storage
# API Key 存取

def save_api_key(key):

    """
    加密保存 Key。
    DPAPI 不可用时退回明文
    （至少功能不断），
    并清掉旧的明文字段。
    """

    cfg = load_config()

    cfg.pop("api_key", None)

    blob = protect_text(key)

    if blob:

        cfg["api_key_protected"] = blob

    else:

        # Fallback for non-Windows / 非 Windows 等环境退路

        cfg["api_key"] = key

    save_config(cfg)


def load_api_key():

    """
    读取 Key。
    优先解 DPAPI 密文；
    发现旧版明文时自动迁移成密文。
    """

    cfg = load_config()

    blob = cfg.get("api_key_protected")

    if blob:

        key = unprotect_text(blob)

        if key:

            return key

        # Usually another machine or user, so the blob is dead: drop it and let the user re-enter.
        # 解不开通常是换了电脑/用户，密文已失效，清掉让用户重填。

        cfg.pop(
            "api_key_protected", None
        )

        save_config(cfg)

    legacy = cfg.get("api_key")

    if legacy:

        # Legacy plaintext, migrate it to encrypted / 旧版明文 → 迁移成密文

        save_api_key(legacy)

        return legacy

    return None
