# TestHub Local Playwright Agent

这是一个按需启动的本机执行器：网页通过 `testhub-runner://` 唤起进程，进程领取一个任务、执行、上传 Trace/截图/结果，然后关闭 Playwright 并退出。它没有心跳，也不常驻后台。

## 0.5 动作与断言

0.5 保持协议 3，通过 `step-runtime-v2` 能力标识启用新动作和等待式断言。
使用这些能力的任务会在领取时拒绝旧执行器并提示升级；只含旧动作的任务仍可使用旧执行器。
更新源码后须重新打包、分发并安装 Runner；只更新平台不会更新用户电脑上的执行器。

- 新动作：`selectOption`（原生 select）、`check`、`uncheck`、`press`。
- 下拉选项输入 `value:值`、`label:显示文字` 或 `index:0`；无前缀按 value 匹配。
  自定义下拉仍通过点击展开和点击选项操作。
- 按键示例：`Enter`、`Tab`、`Escape`、`ControlOrMeta+a`。组合键修饰符支持
  `Control`、`Shift`、`Alt`、`Meta`、`ControlOrMeta`；最后一个键为字符或常用命名键。
- 勾选/取消设置目标状态，重复执行不会反向切换；目标为原生 checkbox/radio。
- `getText` 的输入值可填写变量名（如 `orderId`），后续输入或断言通过
  `${runtime.orderId}` 引用。变量只在当前用例/数据行内有效；未定义变量明确失败。
  留空保持原有的文本日志行为。数据行参数 `${column}` 和运行变量使用不同命名空间。
- 断言支持文本包含/相等、可见/不可见、存在/不存在、输入框值、属性值、
  选中/未选中、启用/禁用、元素数量、URL 相等/包含。
  属性断言的输入值为属性名，期望值为属性值；URL 断言不需要元素。
- 断言在步骤 `wait_time` 毫秒内等待条件满足，成功立即继续，超时失败。
  新建断言默认 5000ms；旧步骤保留原超时值。不可见允许元素不存在，未选中要求元素存在。
- 未知动作和未知断言统一失败，不能当作成功跳过。

服务端 Playwright 与本机 Runner 复用 `step_runtime.py`；Selenium 遵循同一参数契约。
部署平台时执行 `python manage.py migrate` 应用 `0013_step_runtime_actions`。
浏览器集成测试可用 `TESTHUB_BROWSER_TESTS=1` 启用（需要 Playwright Chromium 和 Chrome/WebDriver）。

## 数据驱动用例

0.3 版支持 UI 用例的数据驱动执行：按保存的数据行依次启动独立浏览器会话，一行失败后继续下一行。每行单独回传步骤结果、截图和 Trace；平台执行记录保存当次数据快照。

启用数据驱动后，请使用新版安装包更新本机执行器。旧版执行器无法回传完整的数据行结果，平台会拒绝将其标记为执行成功。服务端执行、套件和定时任务无需安装本机执行器。

## macOS 用户安装

套件管理的执行弹窗支持「服务器运行 / 本地运行」。本地运行需要 0.4 或以上的执行器（协议 3）：一次唤起后按套件顺序执行，各参数化数据行使用独立浏览器会话，某条失败仍继续执行其余用例。结果汇总到套件报告，每条执行的 Trace 和截图可在执行记录中下载。旧执行器会收到更新提示，不会误报套件执行成功。

管理员把 `TestHubRunner-macos-arm64.zip` 发给 Apple 芯片 Mac 用户。用户解压后双击 `安装 TestHub Runner.command`，按提示输入 TestHub 地址即可。安装位置为 `~/Applications/TestHubRunner.app`，浏览器和配置位于 `~/Library/Application Support/TestHubRunner`。

服务地址变化时，双击安装包中的 `配置 TestHub 地址.command` 输入新地址即可，不需要重新安装或重新打包。本地联调可以使用 `http://192.168.1.20:8000` 这类局域网私有 IP，或 `http://your-mac.local:8000`；公网地址必须使用 HTTPS。

如果点击“本机执行”后没有启动浏览器，运行安装包里的 `诊断 TestHub Runner.command`。它会检查应用、配置、浏览器文件和协议注册，并显示最近日志。Agent 启动失败时也会弹出错误窗口；日志保存在 `~/Library/Application Support/TestHubRunner/runner.log`。

macOS 包必须按芯片架构区分：`arm64` 用于 Apple Silicon，`x86_64` 用于 Intel Mac。

macOS 构建命令：

```bash
cd local_playwright_agent
./build_macos.sh
```

## 普通用户安装

管理员在 Windows 构建机生成 `release\TestHubRunner-win-x64.zip` 后，将压缩包发给用户。用户解压后，在 PowerShell 中执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1 -ServerOrigin "https://testhub.example.com"
```

该命令不需要管理员权限，也不要求用户安装 Python。它会把 Agent 和 Playwright 浏览器复制到 `%LOCALAPPDATA%\TestHubRunner`，并为当前 Windows 用户注册 `testhub-runner://`。

## 本地开发

```powershell
cd local_playwright_agent
python -m pip install -r requirements.txt
python -m playwright install chromium
.\register_protocol.ps1 -ServerOrigin "https://testhub.example.com"
```

开发环境可将 `ServerOrigin` 配置成 `http://localhost:8000`、局域网私有 IP 或 `.local` 主机名；公网地址必须使用 HTTPS。

## 打包

打包必须在 Windows x64 构建机执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build.ps1
```

输出文件为 `release\TestHubRunner-win-x64.zip`，包含 EXE、Chromium、Firefox、WebKit 和一键安装脚本。

反向代理部署时要确保 Django 能识别原始 HTTPS 协议，否则生成的领取地址可能是内部 HTTP 地址，并会被 Agent 的安全校验拒绝。
