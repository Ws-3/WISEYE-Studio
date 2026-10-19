$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$server = Join-Path $repository 'third_party\mediamtx\mediamtx.exe'
$configuration = Join-Path $repository 'integrations\rtsp\mediamtx.yml'
$python = Join-Path $repository '.venv\Scripts\python.exe'
$gateway = Join-Path $repository 'integrations\rtsp\rtsp_gateway.py'
if (-not (Test-Path -LiteralPath $server)) { throw 'MediaMTX is missing. Run scripts\Setup-RTSP.ps1 first.' }
if (-not (Test-Path -LiteralPath $python)) { throw 'WISEYE desktop environment is missing.' }
$logDirectory = Join-Path $repository 'logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
if (-not (Get-Process mediamtx -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $server -ArgumentList ('"' + $configuration + '"') -WorkingDirectory (Split-Path $server) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'mediamtx.log') -RedirectStandardError (Join-Path $logDirectory 'mediamtx-error.log')
}
$existingGateway = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*rtsp_gateway.py*' }
if (-not $existingGateway) {
    Start-Process -FilePath $python -ArgumentList ('"' + $gateway + '"') -WorkingDirectory $repository -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'rtsp-gateway.log') -RedirectStandardError (Join-Path $logDirectory 'rtsp-gateway-error.log')
}
Write-Host 'RTSP service ready: CH1 visible, CH2 infrared.'
