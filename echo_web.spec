# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置：Soulmate Web 手机端（单文件）
# 用法：pyinstaller echo_web.spec --noconfirm
# 产物：dist/SoulmateWeb.exe 一个文件
#
# 和桌面版的区别：
#   - 入口是 web_server.py（HTTP 服务，不是 GUI）
#   - console=True：控制台要显示
#     手机该访问的 IP 和 6 位密码
#   - datas 多带一个 web/（手机端页面）
#   - exe 放在 SoulmateData 旁边即走
#     便携模式，和桌面版共用记忆

from PyInstaller.utils.hooks import collect_all

import sys
import importlib.util

# 入口模块名，用于检查入口存在
import os

datas = [
    ('assets', 'assets'),
    ('models', 'models'),
    ('web', 'web'),
]

binaries = []

# venv 环境下 PyInstaller 找不到
# base Python 的 OpenSSL DLL，手动带上
_dlls = os.path.join(sys.base_prefix, 'DLLs')
for dll in ('libcrypto-3-x64.dll', 'libssl-3-x64.dll'):
    p = os.path.join(_dlls, dll)
    if os.path.exists(p):
        binaries.append((p, '.'))

hiddenimports = []

# sentence-transformers 系列需要完整收集
for pkg in ('sentence_transformers', 'transformers', 'tokenizers'):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# 桌面版是 GUI（PySide6），Web 版用不上。
# 不收集 PySide6 能省一大截体积和时间。
excludes = ['PySide6', 'PyQt5', 'PyQt6']


a = Analysis(
    ['web_server.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SoulmateWeb',
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon='assets/echo.ico',
)
