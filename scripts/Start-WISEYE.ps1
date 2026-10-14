param(
    [string]$EngineRoot = $env:UE_ROOT,
    [switch]$BuildOnly,
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$project = Join-Path $repository 'ue5\WISEYE\test.uproject'
$localEngineFile = Join-Path $PSScriptRoot 'engine-root.local.txt'
if (-not $EngineRoot -and (Test-Path -LiteralPath $localEngineFile)) {
    $EngineRoot = (Get-Content -LiteralPath $localEngineFile -Raw).Trim()
}
if (-not $EngineRoot) {
    $installed = Get-ItemProperty 'HKLM:\SOFTWARE\EpicGames\Unreal Engine\5.8' -ErrorAction SilentlyContinue
    if ($installed) { $EngineRoot = $installed.InstalledDirectory }
}
if (-not $EngineRoot) {
    $candidate = Join-Path $env:ProgramFiles 'Epic Games\UE_5.8'
    if (Test-Path -LiteralPath $candidate) { $EngineRoot = $candidate }
}
if (-not $EngineRoot) { throw 'UE 5.8 not found. Run with -EngineRoot "C:\path\UE_5.8", or set UE_ROOT.' }
$builder = Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat'
$editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
if (-not (Test-Path -LiteralPath $builder)) { throw "Build tool not found: $builder" }
if (-not (Test-Path -LiteralPath $editor)) { throw "Editor not found: $editor" }
if (-not $SkipBuild) {
    & $builder testEditor Win64 Development "-Project=$project" -WaitMutex -NoHotReloadFromIDE
    if ($LASTEXITCODE -ne 0) { throw "UE build failed ($LASTEXITCODE). Check VS C++ tools and UE version." }
}
if (-not $BuildOnly) {
    Start-Process -FilePath $editor -WorkingDirectory (Split-Path -Parent $editor) -ArgumentList @(('"' + $project + '"'), '/Game/WISEYE-test', '-EnablePlugins=PythonScriptPlugin') -WindowStyle Normal
}
