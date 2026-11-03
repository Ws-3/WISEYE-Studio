param(
    [string]$BuildWorkspace = (Join-Path (Split-Path -Parent $PSScriptRoot) 'ue5\WISEYE'),
    [string]$EngineRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) 'Tools\UE_5.8'),
    [ValidateSet('city','city_large')][string]$Scene = 'city'
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'Start-InfraredPreview.ps1') @PSBoundParameters
