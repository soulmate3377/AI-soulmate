@echo off
cd /d "%~dp0"

rem ============================================
rem  Soulmate 桌面版（GUI）启动器
rem
rem  双击这个 = 打开窗口界面和她聊天。
rem  和终端版（run_cli.bat）是同一个大脑、
rem  同一份记忆，但同一时刻只能开一个。
rem
rem  ECHO_DATA_DIR 指向项目旁的 SoulmateData。
rem  源码运行时 core/paths.py 本来就会自动找到它，
rem  这里显式设一遍，是为了和 exe / Web 版
rem  跑在同一份数据上。
rem
rem  ---------- 改这个文件前先看这段 ----------
rem  1) 必须存成 GBK（ANSI）。cmd.exe 不看 BOM，
rem     按系统代码页逐行解析 .bat，存成 UTF-8
rem     会让中文注释变乱码、某些字节被当命令执行。
rem  2) 必须用 CRLF 换行。cmd.exe 靠文件偏移逐行
rem     重读批处理，LF-only 会错位、把后续行读成命令。
rem  3) 不要写 chcp 65001：解析途中换代码页会
rem     把多字节字符读断。
rem  4) 会"执行/回显"的内容只用 ASCII，中文只放在
rem     rem 注释里；引号留给参数的 %* 用。
rem ============================================

set ECHO_DATA_DIR=%~dp0..\SoulmateData

call :find_python
if errorlevel 1 exit /b 1

echo.
echo  Starting Soulmate (desktop GUI)...
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
