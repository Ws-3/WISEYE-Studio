param([string]$Python='python')
$ErrorActionPreference='Stop'
$repository=Split-Path -Parent $PSScriptRoot
$client=Join-Path $repository 'builds\dependencies\ProjectAirSimSource\client\python\projectairsim'
if(-not(Test-Path -LiteralPath (Join-Path $client 'pyproject.toml'))) {throw 'Run Setup-ProjectAirSim.ps1 first to prepare the pinned native dependency and client source.'}
$environment=Join-Path $repository '.venv'
$environmentPython=Join-Path $environment 'Scripts\python.exe'
if(-not(Test-Path -LiteralPath $environmentPython)) {
    & $Python -m venv $environment
    if($LASTEXITCODE -ne 0){throw 'Developer environment creation failed; use Python 3.12 or newer.'}
}
& $environmentPython -m pip install -r (Join-Path $repository 'packaging\requirements-build.txt')
if($LASTEXITCODE -ne 0){throw 'Developer/build dependency installation failed.'}
& $environmentPython -m pip install $client
if($LASTEXITCODE -ne 0){throw 'Pinned ProjectAirSim client installation failed.'}
Write-Output "Developer Python ready: $environmentPython"
