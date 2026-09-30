#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_SOURCE="$SCRIPT_DIR/TestHubRunner.app"
BROWSERS_SOURCE="$SCRIPT_DIR/ms-playwright"
APP_DEST="$HOME/Applications/TestHubRunner.app"
DATA_DIR="$HOME/Library/Application Support/TestHubRunner"
BROWSERS_DEST="$DATA_DIR/ms-playwright"
CONFIG_PATH="$DATA_DIR/config.json"

pause_on_error() {
  echo
  echo "安装失败。请把上面的错误信息发给管理员。"
  read -r -p "按回车键关闭窗口..." _
}
trap pause_on_error ERR

SERVER_ORIGIN="${1:-}"
if [[ -z "$SERVER_ORIGIN" ]]; then
  echo "请输入 TestHub 服务地址，例如：https://testhub.company.com"
  read -r -p "TestHub 地址: " SERVER_ORIGIN
fi
SERVER_ORIGIN="${SERVER_ORIGIN%/}"

HTTP_DEV_HOST='(localhost|127(\.[0-9]{1,3}){3}|10(\.[0-9]{1,3}){3}|192\.168(\.[0-9]{1,3}){2}|172\.(1[6-9]|2[0-9]|3[01])(\.[0-9]{1,3}){2}|[A-Za-z0-9.-]+\.local)'
if [[ ! "$SERVER_ORIGIN" =~ ^https://[^/:]+(:[0-9]+)?$ ]] && \
   [[ ! "$SERVER_ORIGIN" =~ ^http://$HTTP_DEV_HOST(:[0-9]+)?$ ]]; then
  echo "地址格式无效。HTTP 仅允许 localhost、.local 主机名或局域网 IP；公网环境必须使用 HTTPS。"
  exit 1
fi
if [[ ! -d "$APP_SOURCE" ]] || [[ ! -d "$BROWSERS_SOURCE" ]]; then
  echo "安装包不完整：缺少 TestHubRunner.app 或 ms-playwright。"
  exit 1
fi

mkdir -p "$HOME/Applications" "$DATA_DIR" "$BROWSERS_DEST"
ditto "$APP_SOURCE" "$APP_DEST"
ditto "$BROWSERS_SOURCE" "$BROWSERS_DEST"

python_escape_json() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}
ESCAPED_ORIGIN="$(python_escape_json "$SERVER_ORIGIN")"
printf '{"server_origin":"%s"}\n' "$ESCAPED_ORIGIN" > "$CONFIG_PATH"

xattr -dr com.apple.quarantine "$APP_DEST" "$DATA_DIR" 2>/dev/null || true
codesign --force --deep --sign - "$APP_DEST" >/dev/null 2>&1

LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
"$LSREGISTER" -f "$APP_DEST"

echo
echo "TestHub Runner 安装完成。"
echo "安装位置：$APP_DEST"
echo "现在回到 TestHub 网页，点击“本机执行”即可。"
echo "浏览器首次询问是否打开 TestHubRunner 时，请选择允许。"
echo
read -r -p "按回车键关闭窗口..." _
