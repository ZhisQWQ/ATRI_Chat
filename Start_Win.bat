@echo off
chcp 65001 >nul
title ATRI 启动器

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查并激活虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 未找到虚拟环境: venv\Scripts\activate.bat
    echo 当前目录: %cd%
    echo 请确认虚拟环境文件夹名是否为 venv，或手动修改脚本中的路径。
    pause
    exit /b 1
)

call "venv\Scripts\activate.bat"
echo [信息] 虚拟环境已激活
echo.

REM 菜单循环
:menu
echo ==============================
echo    请选择要启动的程序
echo ==============================
echo    [1] ATRI_Chat.py
echo    [2] ATRI_Chat_Setting.py
echo    [3] 仅激活虚拟环境
echo    [0] 退出
echo ==============================
choice /c 1230 /n /m "请输入选项: "

if errorlevel 4 goto :bye
if errorlevel 3 goto :shell
if errorlevel 2 goto :run_setting
if errorlevel 1 goto :run_chat

:run_chat
echo.
echo [INFO] ATRI_Chat.py ...
python "ATRI_Chat.py"
echo.
echo [INFO] 程序已退出
pause
goto :menu

:run_setting
echo.
echo [INFO] ATRI_Chat_Setting.py ...
python "ATRI_Chat_Setting.py"
echo.
echo [INFO] 程序已退出
pause
goto :menu

:shell
echo.
echo [INFO] 已进入虚拟环境命令行，输入 exit 可返回菜单。
echo.
cmd /k
echo.
echo [INFO] 已退出虚拟环境命令行。
pause
goto :menu

:bye
echo 已退出。
exit /b 0