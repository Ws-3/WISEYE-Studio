$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$server = Join-Path $repository 'third_party\mediamtx\mediamtx.exe'
$configuration = Join-Path $repository 'logs\mediamtx-runtime.yml'
$python = Join-Path $repository '.venv\Scripts\python.exe'
$gateway = Join-Path $repository 'integrations\rtsp\rtsp_gateway.py'
if (-not (Test-Path -LiteralPath $server)) { throw 'MediaMTX is missing. Run scripts\Setup-RTSP.ps1 first.' }
if (-not (Test-Path -LiteralPath $python)) { throw 'WISEYE desktop environment is missing.' }
$logDirectory = Join-Path $repository 'logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$configurationCode = 'from pathlib import Path; from core.config import AppConfig, ROOT; c=AppConfig.load(); c.write_mediamtx(ROOT/"logs/mediamtx-runtime.yml"); print(c.rtsp_host)'
Push-Location $repository
try { $rtspHost = & $python -c $configurationCode; if ($LASTEXITCODE -ne 0) { throw 'Invalid endpoint configuration.' } }
finally { Pop-Location }
if ($rtspHost -in @('127.0.0.1','localhost') -and -not (Get-Process mediamtx -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $server -ArgumentList ('"' + $configuration + '"') -WorkingDirectory (Split-Path $server) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'mediamtx.log') -RedirectStandardError (Join-Path $logDirectory 'mediamtx-error.log')
}
$existingGateway = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'rtsp_gateway(\.py)?' }
if (-not $existingGateway) {
    Start-Process -FilePath $python -ArgumentList @('-m','integrations.rtsp.rtsp_gateway') -WorkingDirectory $repository -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'rtsp-gateway.log') -RedirectStandardError (Join-Path $logDirectory 'rtsp-gateway-error.log')
}
Write-Host 'RTSP service ready: CH1 visible, CH2 infrared, OBS observer.'
