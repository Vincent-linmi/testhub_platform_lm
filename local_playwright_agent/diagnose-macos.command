#!/bin/bash

set -u

APP_PATH="$HOME/Applications/TestHubRunner.app"
DATA_DIR="$HOME/Library/Application Support/TestHubRunner"
CONFIG_PATH="$DATA_DIR/config.json"
BROWSERS_PATH="$DATA_DIR/ms-playwright"
LOG_PATH="$DATA_DIR/runner.log"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"

echo "=== TestHub Runner 诊断 ==="
echo

if [[ -d "$APP_PATH" ]]; then
  echo "[正常] Agent 已安装：$APP_PATH"
  "$LSREGISTER" -f "$APP_PATH" >/dev/null 2>&1
  echo "[正常] 已重新注册 testhub-runner:// 协议"
else
  echo "[异常] 未找到 Agent，请重新运行新版安装脚本"
fi

if [[ -f "$CONFIG_PATH" ]]; then
  echo "[配置] $(tr -d '\n' < "$CONFIG_PATH")"
else
  echo "[异常] 未找到服务地址配置，请运行“配置 TestHub 地址.command”"
fi

if [[ -d "$BROWSERS_PATH" ]]; then
  echo "[正常] Playwright 浏览器目录存在"
else
  echo "[异常] 未找到 Playwright 浏览器，请重新运行新版安装脚本"
fi

echo
echo "=== 最近运行日志 ==="
if [[ -f "$LOG_PATH" ]]; then
  tail -n 80 "$LOG_PATH"
else
  echo "尚无日志。请回到网页点击一次“本机执行”，然后再次运行本诊断工具。"
fi

echo
read -r -p "按回车键关闭窗口..." _
