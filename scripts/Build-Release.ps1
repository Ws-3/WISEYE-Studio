param(
    [ValidateSet('Game','Cook','Stage','Desktop','Assemble')][string]$Stage = 'Game',
    [ValidateSet('Development','Shipping')][string]$Configuration = 'Development',
    [ValidateSet('Base','City','All')][string]$Content = 'Base',
    [string]$EngineRoot = 'E:\Programs\UE_5.8'
)
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$project = Join-Path $repository 'ue5\WISEYE\test.uproject'
$buildRoot = Join-Path $repository 'builds'
$logRoot = Join-Path $buildRoot 'logs'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$python = Join-Path $buildRoot 'python-env\Scripts\python.exe'
if ($Stage -eq 'Game') {
    # UE 5.8 reserves the positional word test; infer the existing target by type.
    & "$EngineRoot\Engine\Build\BatchFiles\Build.bat" Win64 $Configuration "-Project=$project" -TargetType=Game -WaitMutex -NoHotReloadFromIDE
    if ($LASTEXITCODE -ne 0) { throw "Game build failed: $LASTEXITCODE" }
}
if ($Stage -in @('Cook','Stage')) {
    $maps = switch ($Content) {
        Base { '/Game/WISEYE-test+/Game/WISEYE/Scenes/test_range/TestRange' }
        City { '/Game/WISEYE/Scenes/city/CitySample' }
        All { '/Game/WISEYE-test+/Game/WISEYE/Scenes/test_range/TestRange+/Game/WISEYE/Scenes/city/CitySample' }
    }
    $archive = Join-Path $buildRoot "staged\$Content-$Configuration"
    $cookOption = if ($Stage -eq 'Cook') { '-cook' } else { '-skipcook' }
    & "$EngineRoot\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun "-project=$project" -nop4 -utf8output -platform=Win64 "-clientconfig=$Configuration" -skipbuild $cookOption -stage -pak -iostore -SkipZenStore '-AdditionalCookerOptions=-SkipZenStore' -compressed -archive "-archivedirectory=$archive" "-map=$maps" -unattended -prereqs -nodebuginfo
    if ($LASTEXITCODE -ne 0) { throw "Cook/Stage failed: $LASTEXITCODE" }
}
if ($Stage -eq 'Desktop') {
    $previousPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = "$repository\packaging\build_support;$repository"
    try {
    & $python -X utf8 -m PyInstaller --noconfirm --clean --onedir --windowed --name WISEYE --paths $repository --collect-all pynng --collect-data projectairsim --exclude-module matplotlib --exclude-module tkinter --distpath "$buildRoot\desktop" --workpath "$buildRoot\pyinstaller" --specpath "$buildRoot" "$repository\packaging\entry.py"
    if ($LASTEXITCODE -ne 0) { throw "Desktop build failed: $LASTEXITCODE" }
    } finally { $env:PYTHONPATH = $previousPythonPath }
}
if ($Stage -eq 'Assemble') {
    & $python -X utf8 "$repository\packaging\assemble.py" --content $Content --configuration $Configuration
    if ($LASTEXITCODE -ne 0) { throw "Assembly failed: $LASTEXITCODE" }
}
