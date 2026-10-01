# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置：Soulmate 桌面版（单文件）
# PyInstaller build config: Soulmate desktop build, single file
#
# 用法 / Usage:
#   pyinstaller soulmate.spec --noconfirm
#
# 产物：dist/Soulmate.exe 一个文件，双击即用
# Output: a single dist/Soulmate.exe, double-click to run
#
# 打包前先装好依赖（含 pyinstaller）：
# Install dependencies first, pyinstaller included:
#   uv pip install --python .venv\Scripts\python.exe -r requirements.txt pyinstaller

from PyInstaller.utils.hooks import collect_all

import sys
import os

datas = [
    ('assets', 'assets'),
    ('models', 'models'),
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


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Soulmate',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets/echo.ico',
)
