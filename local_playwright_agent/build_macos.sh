#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist-macos"
BUILD_DIR="$SCRIPT_DIR/build-macos"
RELEASE_DIR="$SCRIPT_DIR/release"
PACKAGE_DIR="$BUILD_DIR/package"
APP_PATH="$DIST_DIR/TestHubRunner.app"
BROWSER_PATH="$PACKAGE_DIR/ms-playwright"
ARCH="$(uname -m)"

if python -m pip --version >/dev/null 2>&1; then
  python -m pip install -r "$SCRIPT_DIR/requirements.txt"
elif command -v uv >/dev/null 2>&1; then
  uv pip install --python "$(command -v python)" -r "$SCRIPT_DIR/requirements.txt"
else
  echo "缺少 pip 或 uv，无法安装构建依赖。" >&2
  exit 1
fi
python -m PyInstaller --noconfirm --clean --windowed --onedir --argv-emulation \
  --name TestHubRunner \
  --osx-bundle-identifier com.testhub.localrunner \
  --distpath "$DIST_DIR" \
  --workpath "$BUILD_DIR/pyinstaller" \
  --specpath "$BUILD_DIR" \
  "$SCRIPT_DIR/agent.py"

python - "$APP_PATH/Contents/Info.plist" "$SCRIPT_DIR/step_runtime.py" <<'PY'
import plistlib
import runpy
import sys

path = sys.argv[1]
with open(path, 'rb') as handle:
    info = plistlib.load(handle)
info['CFBundleShortVersionString'] = runpy.run_path(sys.argv[2])['RUNNER_VERSION']
info['CFBundleVersion'] = info['CFBundleShortVersionString']
info['CFBundleDisplayName'] = 'TestHub Runner'
info['CFBundleName'] = 'TestHub Runner'
info['CFBundleURLTypes'] = [{
    'CFBundleURLName': 'com.testhub.localrunner.execute',
    'CFBundleURLSchemes': ['testhub-runner'],
}]
info['LSUIElement'] = True
with open(path, 'wb') as handle:
    plistlib.dump(info, handle)
PY

codesign --force --deep --sign - "$APP_PATH"

mkdir -p "$PACKAGE_DIR" "$BROWSER_PATH" "$RELEASE_DIR"
rm -rf "$PACKAGE_DIR/TestHubRunner.app"
ditto "$APP_PATH" "$PACKAGE_DIR/TestHubRunner.app"

PREVIOUS_BROWSER_PATH="${PLAYWRIGHT_BROWSERS_PATH:-}"
export PLAYWRIGHT_BROWSERS_PATH="$BROWSER_PATH"
python -m playwright install chromium firefox webkit
if [[ -n "$PREVIOUS_BROWSER_PATH" ]]; then
  export PLAYWRIGHT_BROWSERS_PATH="$PREVIOUS_BROWSER_PATH"
else
  unset PLAYWRIGHT_BROWSERS_PATH
fi

cp "$SCRIPT_DIR/install-macos.command" "$PACKAGE_DIR/安装 TestHub Runner.command"
cp "$SCRIPT_DIR/configure-macos.command" "$PACKAGE_DIR/配置 TestHub 地址.command"
cp "$SCRIPT_DIR/diagnose-macos.command" "$PACKAGE_DIR/诊断 TestHub Runner.command"
cp "$SCRIPT_DIR/README.md" "$PACKAGE_DIR/README.md"
chmod +x "$PACKAGE_DIR/安装 TestHub Runner.command"
chmod +x "$PACKAGE_DIR/配置 TestHub 地址.command"
chmod +x "$PACKAGE_DIR/诊断 TestHub Runner.command"

ARCHIVE="$RELEASE_DIR/TestHubRunner-macos-$ARCH.zip"
rm -f "$ARCHIVE"
ditto -c -k --sequesterRsrc --keepParent "$PACKAGE_DIR" "$ARCHIVE"

echo "macOS release package created: $ARCHIVE"
