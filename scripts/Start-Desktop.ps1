param([switch]$Connect)
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repository '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Desktop environment missing. Create .venv and install requirements.txt as described in docs/DESKTOP.md.'
}
$arguments = @('-m', 'apps.desktop_app.main')
if ($Connect) { $arguments += '--connect' }
Start-Process -FilePath $python -WorkingDirectory $repository -ArgumentList $arguments -WindowStyle Normal
