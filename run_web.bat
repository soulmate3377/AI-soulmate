@echo off
cd /d "%~dp0"

rem ============================================
rem  Soulmate Web 版启动器（可选，给手机用）
rem
rem  桌面版（run_gui.bat）才是主入口；
rem  这个是把同一个大脑开成网页服务，
rem  给同一 WiFi 下的手机浏览器用。
rem
rem  启动后看控制台打印的地址：
rem    http://<本机局域网IP>:<端口>/
rem  第一次进要输密码，密码同时打印在控制台，
rem  也存在数据目录的 web_passcode.txt 里。
rem
rem  注意：桌面版 / 终端版 / Web 版共用同一份
rem  聊天记录，同一时刻只开一个。
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
echo  Starting Soulmate (web UI)...
echo  Data dir: %ECHO_DATA_DIR%
echo.

%PY% web_server.py

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
