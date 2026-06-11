# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 — macOS 生成 .app，Windows 生成单文件 .exe。

构建命令（在对应平台上运行）：
    pyinstaller youtube_email_gui.spec
产物在 dist/ 目录。
"""
import sys
import subprocess

APP_NAME = "YouTubeEmailScraper"          # 可执行文件 / .app 基础名（ASCII，跨平台最稳）
MAC_APP_NAME = "YouTube邮箱采集器"          # macOS 图标下显示的名字

block_cipher = None


def _mac_target_arch():
    """若当前 Python 是 universal2（x86_64+arm64），就打通用包，让 Intel 和
    Apple 芯片都能运行；否则只打当前架构。"""
    if sys.platform != "darwin":
        return None
    try:
        out = subprocess.check_output(["lipo", "-archs", sys.executable]).decode()
        if "x86_64" in out and "arm64" in out:
            return "universal2"
    except Exception:
        pass
    return None


TARGET_ARCH = _mac_target_arch()

a = Analysis(
    ["youtube_email_gui.py"],
    pathex=[],
    binaries=[],
    datas=[],
    # 本地模块和第三方依赖；显式列出以防分析遗漏
    hiddenimports=["youtube_email_scraper", "openpyxl", "requests"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["numpy", "pandas", "matplotlib", "PIL", "scipy", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == "darwin":
    # macOS：onedir + .app 包，启动更快、tkinter 资源更稳
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        target_arch=TARGET_ARCH,   # universal2（如可）否则跟随当前架构
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=False, name=APP_NAME,
    )
    app = BUNDLE(
        coll,
        name=f"{MAC_APP_NAME}.app",
        icon=None,                 # 如有图标，填 "icon.icns"
        bundle_identifier="com.youtube.emailscraper",
        info_plist={
            "CFBundleName": MAC_APP_NAME,
            "CFBundleDisplayName": MAC_APP_NAME,
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "10.13",
            "NSHumanReadableCopyright": "",
        },
    )
else:
    # Windows / Linux：单文件可执行
    exe = EXE(
        pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,            # 不弹出黑色命令行窗口
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,                # 如有图标，填 "icon.ico"
    )
