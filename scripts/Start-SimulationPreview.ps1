param(
    [string]$BuildWorkspace = 'E:\Projects\WISEYE-BuildWorkspace',
    [string]$EngineRoot = 'E:\Programs\UE_5.8',
    [ValidateSet('city','original','test_range')][string]$Scene = 'city'
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'Start-InfraredPreview.ps1') @PSBoundParameters
