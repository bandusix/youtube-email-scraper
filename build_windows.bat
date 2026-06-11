@echo off
REM 在 Windows 上构建单文件 .exe
REM 双击运行，或在命令行执行：build_windows.bat
chcp 65001 >nul
cd /d "%~dp0"

echo ==^> 安装构建依赖...
python -m pip install -r requirements.txt pyinstaller

echo ==^> 清理旧产物...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo ==^> 用 PyInstaller 打包 .exe ...
python -m PyInstaller --noconfirm youtube_email_gui.spec

echo.
echo ✅ 完成！可执行文件： dist\YouTubeEmailScraper.exe
echo    直接把这个 exe 发给别人，双击即可运行（无需安装 Python）。
echo.
pause
