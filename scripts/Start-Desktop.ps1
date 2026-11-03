param([switch]$Connect, [string]$DataDirectory = '')
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
# Preserve the existing source preview's user settings without starting UE.
# Explicit arguments/environment always take precedence; a new checkout can
# open the desktop without the preview workspace or Unreal installed.
if ($DataDirectory) { $env:WISEYE_DATA_DIR = $DataDirectory }
elseif (-not $env:WISEYE_DATA_DIR) {
    $previewData = Join-Path $repository 'UserData'
    if (Test-Path -LiteralPath (Join-Path $previewData 'ue5\WISEYE\Config\WISEYE')) {
        $env:WISEYE_DATA_DIR = $previewData
    }
}
$env:WISEYE_RESOURCES_DIR = $repository
$python = Join-Path $repository 'Tools\Python\pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = Join-Path $repository 'builds\python-env\Scripts\pythonw.exe' }
if (-not (Test-Path -LiteralPath $python)) {
    $python = Join-Path $repository '.venv\Scripts\pythonw.exe'
}
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Desktop environment missing: builds/python-env or .venv. See docs/DESKTOP.md.'
}
$arguments = @('-m', 'apps.desktop_app.main')
if ($Connect) { $arguments += '--connect' }
# pythonw has no console; the desktop itself is the visible interactive window.
Start-Process -FilePath $python -WorkingDirectory $repository -ArgumentList $arguments -WindowStyle Normal
