#!/bin/bash

set -euo pipefail

DATA_DIR="$HOME/Library/Application Support/TestHubRunner"
CONFIG_PATH="$DATA_DIR/config.json"

echo "请输入新的 TestHub 服务地址，例如：https://testhub.company.com"
read -r -p "TestHub 地址: " SERVER_ORIGIN
SERVER_ORIGIN="${SERVER_ORIGIN%/}"

HTTP_DEV_HOST='(localhost|127(\.[0-9]{1,3}){3}|10(\.[0-9]{1,3}){3}|192\.168(\.[0-9]{1,3}){2}|172\.(1[6-9]|2[0-9]|3[01])(\.[0-9]{1,3}){2}|[A-Za-z0-9.-]+\.local)'
if [[ ! "$SERVER_ORIGIN" =~ ^https://[^/:]+(:[0-9]+)?$ ]] && \
   [[ ! "$SERVER_ORIGIN" =~ ^http://$HTTP_DEV_HOST(:[0-9]+)?$ ]]; then
  echo "地址格式无效。HTTP 仅允许 localhost、.local 主机名或局域网 IP；公网环境必须使用 HTTPS。"
  read -r -p "按回车键关闭窗口..." _
  exit 1
fi

mkdir -p "$DATA_DIR"
ESCAPED_ORIGIN="$(printf '%s' "$SERVER_ORIGIN" | sed 's/\\/\\\\/g; s/"/\\"/g')"
printf '{"server_origin":"%s"}\n' "$ESCAPED_ORIGIN" > "$CONFIG_PATH"

echo
echo "TestHub 服务地址已更新为：$SERVER_ORIGIN"
echo "无需重启常驻进程，下次点击“本机执行”立即生效。"
echo
read -r -p "按回车键关闭窗口..." _
