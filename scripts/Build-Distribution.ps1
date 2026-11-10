param(
    [Parameter(Mandatory=$true)][ValidateSet('Plugin','Full')][string]$Kind,
    [ValidateSet('Development','Shipping')][string]$Configuration='Shipping',
    [string]$EngineRoot,
    [string]$OutputDirectory,
    [string]$Python,
    [switch]$IncludeBigCity,
    [switch]$IterativeCook
)
$ErrorActionPreference='Stop'
$repository=Split-Path -Parent $PSScriptRoot
if($Kind -eq 'Plugin') {
    $arguments=@{}
    if($OutputDirectory){$arguments.OutputDirectory=$OutputDirectory}
    if($Python){$arguments.Python=$Python}
    & (Join-Path $PSScriptRoot 'Export-WISEYEPlugin.ps1') @arguments
    return
}
if($OutputDirectory){throw 'Full build output uses builds/staged and releases; OutputDirectory is for Plugin only.'}
if(-not $EngineRoot) {
    $setting=Join-Path $PSScriptRoot 'engine-root.local.txt'
    if(Test-Path -LiteralPath $setting){$EngineRoot=(Get-Content -LiteralPath $setting -Raw -Encoding UTF8).Trim()}
    else {$EngineRoot=Join-Path $repository 'Tools\UE_5.8'}
}
if(-not [IO.Path]::IsPathRooted($EngineRoot)){$EngineRoot=Join-Path $repository $EngineRoot}
foreach($step in @('Game','Cook','Desktop','Assemble')) {
    $arguments=@{Stage=$step;Configuration=$Configuration;EngineRoot=$EngineRoot;ProjectPath=(Join-Path $repository 'ue5\WISEYE\test.uproject')}
    if($IncludeBigCity){$arguments.IncludeBigCity=$true}
    if($Python){$arguments.Python=$Python}
    if($IterativeCook -and $step -eq 'Cook'){$arguments.IterativeCook=$true}
    & (Join-Path $PSScriptRoot 'Build-Release.ps1') @arguments
}
