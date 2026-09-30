@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem ============================================
rem  Echo Web 版启动器（手机用）
rem
rem  双击这个，然后手机连同一个 WiFi，
rem  浏览器打开控制台里显示的地址。
rem
rem  ECHO_DATA_DIR 指向 E:\A1\EchoData，
rem  和桌面版同一份记忆。
rem
rem  注意：桌面版和 Web 版不要同时开
rem  （两边写同一份聊天记录，同时写会丢消息）。
rem ============================================

set ECHO_DATA_DIR=E:\A1\EchoData

set PY=D:\KimiData\daimon-share\daimon\runtime\python\.venv\Scripts\python.exe

if not exist "%PY%" (
    echo.
    echo  找不到 Python：%PY%
    echo  打包环境在 D 盘另一个工具的目录里。
    echo.
    pause
    exit /b 1
)

echo.
echo  正在启动 Echo Web 版...
echo  数据目录：%ECHO_DATA_DIR%
echo.

"%PY%" web_server.py

pause
