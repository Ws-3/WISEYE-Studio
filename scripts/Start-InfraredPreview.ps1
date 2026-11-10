param(
    [string]$BuildWorkspace = (Join-Path (Split-Path -Parent $PSScriptRoot) 'ue5\WISEYE'),
    [string]$EngineRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) 'Tools\UE_5.8'),
    [ValidateSet('city','city_large')][string]$Scene = 'city',
    [string]$DataDirectory = $env:WISEYE_DATA_DIR
)
$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent $PSScriptRoot
$localEngine = Join-Path $PSScriptRoot 'engine-root.local.txt'
$localProject = Join-Path $PSScriptRoot 'preview-project.local.txt'
if (-not $PSBoundParameters.ContainsKey('EngineRoot') -and (Test-Path -LiteralPath $localEngine)) {
    $EngineRoot = (Get-Content -LiteralPath $localEngine -Raw -Encoding UTF8).Trim()
    if (-not [IO.Path]::IsPathRooted($EngineRoot)) { $EngineRoot = Join-Path $sourceRoot $EngineRoot }
}
if (-not $PSBoundParameters.ContainsKey('BuildWorkspace') -and (Test-Path -LiteralPath $localProject)) {
    $configuredProject = (Get-Content -LiteralPath $localProject -Raw -Encoding UTF8).Trim()
    if (-not [IO.Path]::IsPathRooted($configuredProject)) { $configuredProject = Join-Path $sourceRoot $configuredProject }
    $BuildWorkspace = Split-Path -Parent $configuredProject
}

$project = Join-Path $BuildWorkspace 'ue5\WISEYE\test.uproject'
if (-not (Test-Path -LiteralPath $project)) { $project=Join-Path $BuildWorkspace 'test.uproject' }
$editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
$python = Join-Path $sourceRoot 'Tools\Python\python.exe'
$pythonw = Join-Path $sourceRoot 'Tools\Python\pythonw.exe'
$material = Join-Path (Split-Path -Parent $project) 'Content\WISEYE\Sensors\M_IR_Reference.uasset'
foreach ($file in @($project,$editor,$python,$pythonw,$material)) {
    if (-not (Test-Path -LiteralPath $file)) { throw "Preview dependency missing: $file" }
}
foreach ($port in @(50051,50052)) {
    $probe = [Net.Sockets.TcpClient]::new()
    try { $probe.Connect('127.0.0.1',$port); throw "Port $port is occupied. Close the previous simulation first." }
    catch [Net.Sockets.SocketException] { }
    finally { $probe.Dispose() }
}
$data = if ($DataDirectory) { $DataDirectory } else { Join-Path $sourceRoot 'UserData' }
$configuration = Join-Path $data 'ue5\WISEYE\Config'
New-Item -ItemType Directory -Path $configuration,(Join-Path $data 'logs') -Force | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $configuration 'WISEYE'))) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot 'ue5\WISEYE\Config\WISEYE') -Destination $configuration -Recurse
}
if (-not (Test-Path -LiteralPath (Join-Path $data 'configs'))) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot 'configs') -Destination $data -Recurse
}
# SceneStore resolves source maps from the canonical project. Do not create
# absolute junctions in portable user data: those break when the drive changes.
# Windows PowerShell 5.1 otherwise treats BOM-less UTF-8 as the system ANSI
# code page, corrupting Chinese strings before ConvertFrom-Json parses them.
$manifest = Get-Content -LiteralPath (Join-Path $configuration "WISEYE\Scenes\$Scene.json") -Raw -Encoding UTF8 | ConvertFrom-Json
# One supervisor owns every child, including venv Python descendants.
Push-Location -LiteralPath $sourceRoot
try {
& $python -m apps.desktop_app.preview_session --editor $editor --project $project --data $data --scene $Scene
} finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "Preview session failed; see $data\logs\session.log" }
