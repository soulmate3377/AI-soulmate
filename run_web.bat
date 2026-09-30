@echo off
cd /d "%~dp0"

rem ============================================
rem  Soulmate Web 版启动器（可选，给手机用）
rem  Soulmate web UI launcher, optional, for your phone
rem
rem  桌面版（run_gui.bat）才是主入口；这个是把同一个大脑开成网页服务，
rem  给同一 WiFi 下的手机浏览器用。
rem  The desktop build (run_gui.bat) is the main entry point. This one
rem  serves the same brain over HTTP for a phone browser on the same WiFi.
rem
rem  启动后看控制台打印的地址。第一次进要输密码，密码同时打印在控制台，
rem  也存在数据目录的 web_passcode.txt 里。
rem  Watch the console for the URL. It asks for a passcode on first visit;
rem  the passcode is printed there and saved to web_passcode.txt.
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
echo  Starting Soulmate (web UI)...
echo  Data dir: %ECHO_DATA_DIR%
echo.

%PY% web_server.py

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
