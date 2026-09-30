@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem ============================================
rem  Soulmate 开发版启动器（源码直接跑，不用打包）
rem
rem  改完代码双击这个，几秒就能看到效果。
rem  打包一次要四分钟，调界面别走那条路。
rem
rem  ECHO_DATA_DIR 指向 SoulmateData，
rem  不设的话源码会另用 %APPDATA%\Soulmate，
rem  聊天记录会分成两摊。
rem ============================================

set ECHO_DATA_DIR=%~dp0..\SoulmateData

echo.
echo  正在用源码启动 Soulmate...
echo  数据目录：%ECHO_DATA_DIR%
echo.

python main.py

if errorlevel 1 (
    echo.
    echo  Soulmate 退出了，错误码 %errorlevel%
    echo  详细日志见 %%APPDATA%%\Soulmate\echo_error.log
)

pause
