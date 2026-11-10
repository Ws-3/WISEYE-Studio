param(
    [ValidateSet('Game','Cook','Stage','Desktop','Assemble')][string]$Stage = 'Game',
    [ValidateSet('Development','Shipping')][string]$Configuration = 'Development',
    [ValidateSet('City')][string]$Content = 'City',
    [string]$EngineRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) 'Tools\UE_5.8'),
    [string]$ProjectPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'ue5\WISEYE\test.uproject'),
    [string]$Python,
    [switch]$IncludeBigCity,
    [switch]$IterativeCook
)
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$project = $ProjectPath
$buildRoot = Join-Path $repository 'builds'
$logRoot = Join-Path $buildRoot 'logs'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
if(-not $Python) {
    foreach($candidate in @('Tools\Python\python.exe','.venv\Scripts\python.exe','builds\python-env\Scripts\python.exe')) {
        $resolvedPython=Join-Path $repository $candidate
        if(Test-Path -LiteralPath $resolvedPython){$Python=$resolvedPython;break}
    }
}
if(-not $Python){$Python=(Get-Command python -ErrorAction Stop).Source}
if ($Stage -eq 'Game') {
    # UE 5.8 reserves the positional word test; infer the existing target by type.
    & "$EngineRoot\Engine\Build\BatchFiles\Build.bat" Win64 $Configuration "-Project=$project" -TargetType=Game -WaitMutex -NoHotReloadFromIDE
    if ($LASTEXITCODE -ne 0) { throw "Game build failed: $LASTEXITCODE" }
}
if ($Stage -in @('Cook','Stage')) {
    if ($Stage -eq 'Cook') {
        # Cook uses the Editor module's reflected classes and serialization.
        # Rebuild it too when the Game's native properties have changed.
        & "$EngineRoot\Engine\Build\BatchFiles\Build.bat" Win64 Development "-Project=$project" -TargetType=Editor -WaitMutex -NoHotReloadFromIDE
        if ($LASTEXITCODE -ne 0) { throw "Editor build for Cook failed: $LASTEXITCODE" }
    }
    $maps = '/Game/WISEYE/Scenes/city/CitySample'
    if ($IncludeBigCity) { $maps += '+/Game/WISEYE/Scenes/city_large/BigCity' }
    $archive = Join-Path $buildRoot "staged\$Content-$Configuration"
    $cookOption = if ($Stage -eq 'Cook') { '-cook' } else { '-skipcook' }
    $cookArguments=@($cookOption)
    if($IterativeCook -and $Stage -eq 'Cook'){$cookArguments+='-iterativecooking'}
    & "$EngineRoot\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun "-project=$project" -nop4 -utf8output -platform=Win64 "-clientconfig=$Configuration" -skipbuild @cookArguments -stage -pak -iostore -SkipZenStore '-AdditionalCookerOptions=-SkipZenStore' -compressed -archive "-archivedirectory=$archive" "-map=$maps" -unattended -prereqs -nodebuginfo
    if ($LASTEXITCODE -ne 0) { throw "Cook/Stage failed: $LASTEXITCODE" }
}
if ($Stage -eq 'Desktop') {
    $previousPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = "$repository\packaging\build_support;$repository"
    try {
    & $python -X utf8 -m PyInstaller --noconfirm --clean --onedir --windowed --name WISEYE --paths $repository --collect-all pynng --collect-data projectairsim --exclude-module matplotlib --exclude-module tkinter --distpath "$buildRoot\desktop" --workpath "$buildRoot\pyinstaller" --specpath "$buildRoot" "$repository\packaging\entry.py"
    if ($LASTEXITCODE -ne 0) { throw "Desktop build failed: $LASTEXITCODE" }
    & $python -X utf8 -m PyInstaller --noconfirm --clean --onedir --windowed --name WISEYE-Training --paths $repository --exclude-module matplotlib --exclude-module tkinter --distpath "$buildRoot\desktop" --workpath "$buildRoot\pyinstaller-training" --specpath "$buildRoot" "$repository\packaging\training_entry.py"
    if ($LASTEXITCODE -ne 0) { throw "Training desktop build failed: $LASTEXITCODE" }
    } finally { $env:PYTHONPATH = $previousPythonPath }
}
if ($Stage -eq 'Assemble') {
    $assemblyArgs = @('-X','utf8',"$repository\packaging\assemble.py",'--content',$Content,'--configuration',$Configuration)
    if ($IncludeBigCity) { $assemblyArgs += '--include-big-city' }
    & $python @assemblyArgs
    if ($LASTEXITCODE -ne 0) { throw "Assembly failed: $LASTEXITCODE" }
}
