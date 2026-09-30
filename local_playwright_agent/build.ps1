param([string]$ServerOrigin)

$ErrorActionPreference = "Stop"
$distDir = "$PSScriptRoot\dist"
$browserDir = "$distDir\ms-playwright"
$releaseDir = "$PSScriptRoot\release"

try {
    python -m pip --version | Out-Null
    python -m pip install -r "$PSScriptRoot\requirements.txt"
} catch {
    uv pip install --python (Get-Command python).Source -r "$PSScriptRoot\requirements.txt"
}
python -m PyInstaller --noconfirm --clean --onefile --name TestHubRunner `
    --distpath $distDir `
    --workpath "$PSScriptRoot\build" `
    --specpath "$PSScriptRoot" `
    "$PSScriptRoot\agent.py"

$previousBrowserPath = $env:PLAYWRIGHT_BROWSERS_PATH
$env:PLAYWRIGHT_BROWSERS_PATH = $browserDir
try {
    python -m playwright install chromium firefox webkit
} finally {
    $env:PLAYWRIGHT_BROWSERS_PATH = $previousBrowserPath
}

Copy-Item "$PSScriptRoot\install.ps1" "$distDir\install.ps1" -Force
Copy-Item "$PSScriptRoot\register_protocol.ps1" "$distDir\register_protocol.ps1" -Force
Copy-Item "$PSScriptRoot\README.md" "$distDir\README.md" -Force

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
$archive = "$releaseDir\TestHubRunner-win-x64.zip"
if (Test-Path $archive) {
    Remove-Item $archive -Force
}
Compress-Archive -Path "$distDir\*" -DestinationPath $archive -CompressionLevel Optimal
Write-Host "Release package created: $archive"

if ($ServerOrigin) {
    & "$distDir\install.ps1" -ServerOrigin $ServerOrigin
}
