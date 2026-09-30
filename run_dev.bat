@echo off
cd /d "%~dp0"

rem ============================================
rem  Soulmate 开发版启动器（源码直接跑，不用打包）
rem  Soulmate dev launcher (from source, no packaging)
rem
rem  改完代码双击这个，几秒就能看到效果。打包一次要四分钟，
rem  调界面别走那条路。
rem  Double-click after editing code to see the change in seconds.
rem  Packaging takes four minutes; don't use it while tweaking UI.
rem
rem  这是 run_gui.bat 的旧版名字，内容一样，留着只为不弄坏已有的快捷方式。
rem  Old name of run_gui.bat, same content, kept so existing shortcuts work.
rem
rem  和桌面版 / 终端版 / Web 版共用同一个大脑和同一份记忆，
rem  但同一时刻只能开一个。
rem  Shares one brain and one data dir with the other entry points,
rem  but only one instance may run at a time.
rem
rem  ---------- 改这个文件前先看这段 / read before editing ----------
rem  本文件必须存成 GBK（ANSI）编码。cmd.exe 不看 BOM，按系统代码页
rem  逐行解析 .bat，存成 UTF-8 会让中文注释变乱码、某些字节被当成
rem  命令执行。
rem  This file must stay GBK (ANSI) encoded. cmd.exe ignores BOM and
rem  parses .bat by system codepage; UTF-8 turns these comments into
rem  mojibake and some bytes get run as commands.
rem
rem  必须用 CRLF 换行。cmd.exe 靠文件偏移逐行重读批处理，LF-only 会
rem  错位、把后续行读成命令。
rem  Must stay CRLF. cmd.exe re-reads the batch by byte offset; LF-only
rem  shifts offsets and feeds later lines to the shell.
rem
rem  不要加 chcp 65001：解析途中换代码页会把多字节字符读断。
rem  Do not add chcp 65001: switching codepage mid-parse splits
rem  multi-byte characters.
rem
rem  会"执行/回显"的内容只用 ASCII，中文只放在 rem 注释里。
rem  Keep everything executed or echoed in ASCII; Chinese lives only
rem  in rem comments.
rem ============================================

set ECHO_DATA_DIR=%~dp0..\SoulmateData

call :find_python
if errorlevel 1 exit /b 1

echo.
echo  Starting Soulmate (desktop, source mode)...
echo  Data dir: %ECHO_DATA_DIR%
echo.

%PY% main.py

if errorlevel 1 (
    echo.
    echo  Soulmate exited with code %errorlevel%
    echo  See log: %%APPDATA%%\Soulmate\echo_error.log
)

pause
exit /b 0

:find_python
rem 优先 py -3（能挑到已装的 3.x），退回 PATH 里的 python
rem Prefer py -3 (picks an installed 3.x), fall back to python on PATH.
where py >nul 2>nul
if not errorlevel 1 (
    set "PY=py -3"
    exit /b 0
)
where python >nul 2>nul
if not errorlevel 1 (
    set "PY=python"
    exit /b 0
)
echo.
echo  Python not found.
echo  Install Python 3.12+ and tick "Add python.exe to PATH":
echo    https://www.python.org/downloads/
echo.
pause
exit /b 1
