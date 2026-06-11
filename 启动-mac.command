#!/bin/bash
# macOS 双击启动脚本：自动安装依赖并打开图形界面
cd "$(dirname "$0")"
echo "正在检查依赖..."
python3 -m pip install --quiet -r requirements.txt
echo "启动 YouTube 邮箱采集器..."
python3 youtube_email_gui.py
