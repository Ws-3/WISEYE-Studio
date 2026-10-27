param(
    [string]$BuildWorkspace = 'E:\Projects\WISEYE-BuildWorkspace',
    [string]$EngineRoot = 'E:\Programs\UE_5.8',
    [ValidateSet('city','original','test_range')][string]$Scene = 'city'
)
$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent $PSScriptRoot
$project = Join-Path $BuildWorkspace 'ue5\WISEYE\test.uproject'
$editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
$python = Join-Path $BuildWorkspace 'builds\python-env\Scripts\python.exe'
$pythonw = Join-Path $BuildWorkspace 'builds\python-env\Scripts\pythonw.exe'
$material = Join-Path $BuildWorkspace 'ue5\WISEYE\Content\WISEYE\Sensors\M_IR_Experimental.uasset'
foreach ($file in @($project,$editor,$python,$pythonw,$material)) {
    if (-not (Test-Path -LiteralPath $file)) { throw "Preview dependency missing: $file" }
}
foreach ($port in @(50051,50052)) {
    $probe = [Net.Sockets.TcpClient]::new()
    try { $probe.Connect('127.0.0.1',$port); throw "Port $port is occupied. Close the previous simulation first." }
    catch [Net.Sockets.SocketException] { }
    finally { $probe.Dispose() }
}
$data = Join-Path $BuildWorkspace 'builds\infrared-preview-data'
$configuration = Join-Path $data 'ue5\WISEYE\Config'
New-Item -ItemType Directory -Path $configuration,(Join-Path $data 'logs') -Force | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $configuration 'WISEYE'))) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot 'ue5\WISEYE\Config\WISEYE') -Destination $configuration -Recurse
}
if (-not (Test-Path -LiteralPath (Join-Path $data 'configs'))) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot 'configs') -Destination $data -Recurse
}
# Source-mode scene discovery checks .umap availability. Reference existing
# build assets instead of duplicating the city inside disposable user data.
$content = Join-Path $data 'ue5\WISEYE\Content'
if (-not (Test-Path -LiteralPath $content)) {
    New-Item -ItemType Junction -Path $content -Target (Join-Path $BuildWorkspace 'ue5\WISEYE\Content') | Out-Null
}
# Windows PowerShell 5.1 otherwise treats BOM-less UTF-8 as the system ANSI
# code page, corrupting Chinese strings before ConvertFrom-Json parses them.
$manifest = Get-Content -LiteralPath (Join-Path $configuration "WISEYE\Scenes\$Scene.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$oldData = $env:WISEYE_DATA_DIR
$oldResources = $env:WISEYE_RESOURCES_DIR
try {
    $env:WISEYE_DATA_DIR = $data
    $env:WISEYE_RESOURCES_DIR = $BuildWorkspace
    $arguments = @(('"' + $project + '"'),($manifest.map + '?game=/Script/test.WiseEyeGameMode?wiseeye_scene=' + $Scene),'-game','-windowed','-ResX=1280','-ResY=720','-nosplash',('-WiseEyeDataDir="'+$data+'"'),('-UserDir="'+(Join-Path $data 'UE')+'"'),('-simlogdir="'+(Join-Path $data 'logs')+'"'))
    $game = Start-Process -FilePath $editor -ArgumentList $arguments -WorkingDirectory $BuildWorkspace -WindowStyle Normal -PassThru
    $flight = Start-Process -FilePath $python -ArgumentList @('-m','integrations.ProjectAirSim.run_wiseye_flight','--scene',$Scene,'--loops','0') -WorkingDirectory $BuildWorkspace -WindowStyle Hidden -RedirectStandardOutput (Join-Path $data 'logs\flight.log') -RedirectStandardError (Join-Path $data 'logs\flight-error.log') -PassThru
    Start-Process -FilePath $pythonw -ArgumentList @('-m','apps.desktop_app.main') -WorkingDirectory $BuildWorkspace -WindowStyle Normal
    Write-Host 'Wait for city loading, then connect UE. Infrared properties provide enhanced/legacy modes.'
    Write-Host "Preview data: $data. Keep this launcher open. Land before closing the game and desktop."
    $game.WaitForExit()
} finally {
    if ($flight -and -not $flight.HasExited) { Stop-Process -Id $flight.Id -ErrorAction SilentlyContinue }
    $env:WISEYE_DATA_DIR = $oldData
    $env:WISEYE_RESOURCES_DIR = $oldResources
}
Write-Host 'Game closed; the owned preview flight worker has been stopped.'
