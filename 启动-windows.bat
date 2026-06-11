@echo off
REM Windows 双击启动脚本：自动安装依赖并打开图形界面
chcp 65001 >nul
cd /d "%~dp0"
echo 正在检查依赖...
python -m pip install --quiet -r requirements.txt
echo 启动 YouTube 邮箱采集器...
python youtube_email_gui.py
pause
