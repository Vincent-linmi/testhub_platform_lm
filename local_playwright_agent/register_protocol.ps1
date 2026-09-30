param(
    [Parameter(Mandatory = $true)]
    [string]$ServerOrigin,
    [string]$PythonExe = "python",
    [string]$AgentPath = "$PSScriptRoot\agent.py",
    [string]$RunnerExe = ""
)

$origin = $ServerOrigin.TrimEnd('/')
$configDir = Join-Path $env:LOCALAPPDATA "TestHubRunner"
$configPath = Join-Path $configDir "config.json"
New-Item -ItemType Directory -Path $configDir -Force | Out-Null
$configJson = @{ server_origin = $origin } | ConvertTo-Json
[System.IO.File]::WriteAllText($configPath, $configJson, [System.Text.UTF8Encoding]::new($false))

$protocolRoot = "HKCU:\Software\Classes\testhub-runner"
New-Item -Path $protocolRoot -Force | Out-Null
Set-Item -Path $protocolRoot -Value "URL:TestHub Runner Protocol"
Set-ItemProperty -Path $protocolRoot -Name "URL Protocol" -Value ""
New-Item -Path "$protocolRoot\shell\open\command" -Force | Out-Null
if ($RunnerExe) {
    $command = "`"$RunnerExe`" `"%1`""
} else {
    $command = "`"$PythonExe`" `"$AgentPath`" `"%1`""
}
Set-Item -Path "$protocolRoot\shell\open\command" -Value $command

Write-Host "testhub-runner:// protocol registered for $origin"
