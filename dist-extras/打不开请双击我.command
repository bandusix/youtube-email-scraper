#!/bin/bash
# 双击我：自动把 App 安装到「应用程序」、解除 macOS 的"未签名"安全拦截，然后打开。
cd "$(dirname "$0")"
APP="YouTube邮箱采集器.app"

clear
echo "================================================"
echo "    YouTube 邮箱采集器 — 一键安装并打开"
echo "================================================"
echo ""

if [ ! -d "$APP" ]; then
  echo "X  没找到 $APP"
  echo "   请确认本工具和 App 在同一个窗口里（直接在 dmg 里双击我）。"
  echo ""
  read -p "按回车键关闭…"
  exit 1
fi

DEST="/Applications/$APP"
echo "-> 正在安装到「应用程序」…"
rm -rf "$DEST" 2>/dev/null
if cp -R "$APP" /Applications/ 2>/dev/null; then
  TARGET="$DEST"
else
  echo "   （没有「应用程序」写入权限，改装到桌面）"
  rm -rf "$HOME/Desktop/$APP" 2>/dev/null
  cp -R "$APP" "$HOME/Desktop/" 2>/dev/null && TARGET="$HOME/Desktop/$APP"
fi

if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "X  安装失败，请手动把 App 拖进「应用程序」后再双击我一次。"
  read -p "按回车键关闭…"
  exit 1
fi

echo "-> 正在解除安全拦截…"
xattr -cr "$TARGET" 2>/dev/null

echo "-> 正在打开…"
open "$TARGET"

echo ""
echo "OK  完成！以后在「启动台 / 应用程序」里直接打开即可。"
echo "    （这个终端窗口可以关掉了）"
sleep 1
