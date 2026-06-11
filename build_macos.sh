#!/bin/bash
# 在 macOS 上构建 .app 并打包成 .dmg。
# 关键：必须用「自带新版 Tcl/Tk（8.6 或 9.0）」的 Python 打包。
# 千万不要用系统自带的 /usr/bin/python3 —— 它依赖系统 Tk 8.5，
# 在 macOS 新版本上会一启动就崩溃（Tcl_Panic / TkpInit）。
set -e
cd "$(dirname "$0")"

APP_NAME="YouTube邮箱采集器"

# 按优先级挑选打包用的 Python：
#  1) python.org 官方版（universal2，自带 Tk 8.6）→ 打出 Intel+Apple 通用包【最佳】
#  2) Homebrew python3（arm64，自带 Tk 9.0）→ 打出 Apple 芯片包
# 不接受系统 /usr/bin/python3（Tk 8.5，会崩）。
PYBIN=""
for cand in \
  /Library/Frameworks/Python.framework/Versions/3.*/bin/python3 \
  /opt/homebrew/bin/python3.14 /opt/homebrew/bin/python3 \
  /usr/local/bin/python3 ; do
  for p in $cand; do
    [ -x "$p" ] || continue
    case "$p" in */CommandLineTools/*|/usr/bin/python3) continue;; esac
    TKV=$("$p" -c "import tkinter; print(tkinter.TkVersion)" 2>/dev/null || echo 0)
    # 需要 Tk >= 8.6
    if [ "$(printf '%s\n8.6\n' "$TKV" | sort -g | head -1)" = "8.6" ] || [ "$TKV" = "9.0" ]; then
      PYBIN="$p"; break 2
    fi
  done
done

if [ -z "$PYBIN" ]; then
  echo "❌ 没找到自带新版 Tk(>=8.6) 的 Python。"
  echo "   请装其一后重试："
  echo "   · Homebrew：  brew install python-tk      （打 Apple 芯片包）"
  echo "   · 通用包：    从 python.org 下载并安装 Python（universal2，自带 Tk 8.6，"
  echo "                 可打出 Intel+Apple 通用包）"
  exit 1
fi

TKV=$("$PYBIN" -c "import tkinter; print(tkinter.TkVersion)" 2>/dev/null)
echo "==> 用 $("$PYBIN" -V 2>&1)  (Tk $TKV)  打包"

rm -rf .venv-build build dist
"$PYBIN" -m venv .venv-build
VENV=.venv-build/bin/python
"$VENV" -m pip install --quiet --upgrade pip
"$VENV" -m pip install --quiet requests openpyxl pyinstaller

echo "==> PyInstaller 打包 .app ..."
"$VENV" -m PyInstaller --noconfirm youtube_email_gui.spec

echo "==> 组装 .dmg 内容（App + 一键解除小工具 + 说明 + 应用程序快捷方式）..."
STAGE="$(mktemp -d)"
cp -R "dist/${APP_NAME}.app" "$STAGE/"
if [ -d dist-extras ]; then
  cp dist-extras/*.command "$STAGE/" 2>/dev/null || true
  cp dist-extras/*.txt "$STAGE/" 2>/dev/null || true
  chmod +x "$STAGE/"*.command 2>/dev/null || true
fi
ln -s /Applications "$STAGE/应用程序"

echo "==> 生成 .dmg 安装包..."
hdiutil create -volname "${APP_NAME}" -srcfolder "$STAGE" -ov -format UDZO "dist/${APP_NAME}.dmg"
rm -rf "$STAGE"

ARCH=$(lipo -archs "dist/${APP_NAME}.app/Contents/MacOS/YouTubeEmailScraper" 2>/dev/null)
echo ""
echo "✅ 完成！架构：${ARCH}（universal2 = Intel+Apple 通用；arm64 = 仅 Apple 芯片）"
echo "   安装包: dist/${APP_NAME}.dmg"
echo ""
echo "提示：未做苹果签名。别人首次打开需双击 dmg 里的「打不开请双击我.command」，"
echo "      或右键 → 打开。（详见 README 常见问题）"
