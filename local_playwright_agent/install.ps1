param(
    [Parameter(Mandatory = $true)]
    [string]$ServerOrigin
)

$ErrorActionPreference = "Stop"
$sourceDir = $PSScriptRoot
$installDir = Join-Path $env:LOCALAPPDATA "TestHubRunner"
$sourceExe = Join-Path $sourceDir "TestHubRunner.exe"
$sourceBrowsers = Join-Path $sourceDir "ms-playwright"
$targetExe = Join-Path $installDir "TestHubRunner.exe"
$targetBrowsers = Join-Path $installDir "ms-playwright"

if (-not (Test-Path $sourceExe)) {
    throw "安装包缺少 TestHubRunner.exe"
}
if (-not (Test-Path $sourceBrowsers)) {
    throw "安装包缺少 ms-playwright 浏览器目录"
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null
New-Item -ItemType Directory -Path $targetBrowsers -Force | Out-Null
Copy-Item $sourceExe $targetExe -Force
Copy-Item "$sourceBrowsers\*" $targetBrowsers -Recurse -Force

& "$sourceDir\register_protocol.ps1" `
    -ServerOrigin $ServerOrigin `
    -RunnerExe $targetExe

Write-Host "TestHub Runner 安装完成：$installDir"
Write-Host "现在可以回到 TestHub 网页点击“本机执行”。"
