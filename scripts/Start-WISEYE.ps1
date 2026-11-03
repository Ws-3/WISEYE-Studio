param(
    [string]$EngineRoot = $env:UE_ROOT,
    [switch]$BuildOnly,
    [switch]$SkipBuild,
    [switch]$AutoPlay,
    [string]$Map = '/Game/WISEYE/Scenes/city/CitySample',
    [string]$PrepareScene
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
if (-not [IO.Path]::IsPathRooted($EngineRoot)) { $EngineRoot = Join-Path $repository $EngineRoot }
$builder = Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat'
$editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
if (-not (Test-Path -LiteralPath $builder)) { throw "Build tool not found: $builder" }
if (-not (Test-Path -LiteralPath $editor)) { throw "Editor not found: $editor" }
if (-not $SkipBuild) {
    & $builder testEditor Win64 Development "-Project=$project" -WaitMutex -NoHotReloadFromIDE
    if ($LASTEXITCODE -ne 0) { throw "UE build failed ($LASTEXITCODE). Check VS C++ tools and UE version." }
}
if (-not $BuildOnly) {
    if ($Map -notmatch '^/Game/([A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+$') { throw 'Invalid map package path.' }
    $editorArgs = @(('"' + $project + '"'), $Map, '-EnablePlugins=PythonScriptPlugin')
    if ($AutoPlay) {
        $playScript = Join-Path $repository 'ue5\scripts\play_demo.py'
        $playCommand = 'py ' + $playScript.Replace('\', '/')
        $editorArgs += ('-ExecCmds="' + $playCommand + '"')
    }
    if ($PrepareScene) {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'Save and close UE before preparing a scene.' }
        if ($PrepareScene -notmatch '^[a-z][a-z0-9_]{0,47}$') { throw 'Invalid scene ID.' }
        $env:WISEYE_PREPARE_SCENE = $PrepareScene
        $prepareScript = Join-Path $repository 'ue5\scripts\prepare_registered_scene.py'
        $editorArgs += ('-ExecutePythonScript="' + $prepareScript + '"')
    }
    $existingEditor = Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*$project*" }
    if ($existingEditor) { Write-Host 'WISEYE editor is already open. Reusing it; click Play if needed.'; return }
    Start-Process -FilePath $editor -WorkingDirectory (Split-Path -Parent $editor) -ArgumentList $editorArgs -WindowStyle Normal
}
