param(
    [Parameter(Mandatory=$true)][string]$AirSimRoot,
    [Parameter(Mandatory=$true)][string]$EngineRoot,
    [Parameter(Mandatory=$true)][string]$VisualStudioRoot,
    [ValidateSet('SimLibs','Tests','Editor')][string]$Stage = 'SimLibs'
)
$ErrorActionPreference = 'Stop'
# Keep test dependencies outside WISEYE. Set environment only in this process.
$AirSimRoot = (Resolve-Path -LiteralPath $AirSimRoot).Path
$EngineRoot = (Resolve-Path -LiteralPath $EngineRoot).Path
$VisualStudioRoot = (Resolve-Path -LiteralPath $VisualStudioRoot).Path
$saved = @{}
foreach ($name in @('UE_ROOT','VSINSTALLDIR','PATH','CMAKE_BUILD_PARALLEL_LEVEL')) {
    $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
Push-Location $AirSimRoot
try {
    $env:UE_ROOT = $EngineRoot
    # vcvarsall requires the trailing separator when VSINSTALLDIR is pre-set.
    $env:VSINSTALLDIR = $VisualStudioRoot.TrimEnd('\') + '\'
    $cmake = Join-Path $VisualStudioRoot 'Common7\IDE\CommonExtensions\Microsoft\CMake'
    $env:PATH = "$env:SystemRoot\System32;$cmake\CMake\bin;$cmake\Ninja;$env:PATH"
    $env:CMAKE_BUILD_PARALLEL_LEVEL = '8'
    if ($Stage -eq 'SimLibs') {
        & .\build.cmd simlibs_release
    } elseif ($Stage -eq 'Tests') {
        & .\build.cmd test_simlibs_release
    } else {
        & "$EngineRoot\Engine\Build\BatchFiles\Build.bat" BlocksEditor Win64 Development "-Project=$AirSimRoot\unreal\Blocks\Blocks.uproject" -WaitMutex
    }
    if ($LASTEXITCODE -ne 0) { throw "Project AirSim $Stage failed (exit $LASTEXITCODE)." }
} finally {
    Pop-Location
    foreach ($name in $saved.Keys) {
        [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process')
    }
}
