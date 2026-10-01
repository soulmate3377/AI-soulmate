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

    # Unpack next to the exe instead of into %TEMP%.
    #
    # A onefile build normally extracts all 344MB into a fresh %TEMP%\_MEIxxxx
    # directory on every launch. That is exactly the pattern antivirus
    # heuristics watch for, and suites like Huorong / 360 / Tencent PC Manager
    # block it -- the user sees a bare "Could not create temporary directory!"
    # dialog and nothing else. It also breaks on locked-down %TEMP% paths.
    #
    # '.' resolves to the current working directory, which for a double-clicked
    # exe is the folder it sits in. The unpack directory is removed on exit.
    #
    # Tradeoff: the exe must live somewhere writable (Desktop, Documents, a USB
    # stick) -- not Program Files. That matches how portable apps behave anyway,
    # and matches data_dir(), which also prefers a portable folder beside the exe.
    #
    # 解压到 exe 旁边，而不是 %TEMP%。
    # 单文件版默认每次启动都把 344MB 解到 %TEMP%\_MEIxxxx —— 这正是杀软
    # 启发式重点盯的行为，火绒/360/电脑管家会拦掉，用户只会看到一个
    # "Could not create temporary directory!" 的报错框。%TEMP% 被锁的机器同样会挂。
    # '.' 解析为当前工作目录；双击运行时就是 exe 所在目录。退出时会删掉解压目录。
    # 代价：exe 得放在可写位置（桌面、文档、U 盘），不能放 Program Files。
    # 这本来就是便携程序的正常要求，也和 data_dir() 优先用 exe 旁边目录一致。
    runtime_tmpdir='.',
)
