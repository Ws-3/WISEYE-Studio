param(
    [Parameter(Mandatory=$true)][string]$ProjectPath,
    [ValidatePattern('^[a-z][a-z0-9_]{0,47}$')][string]$Scene='custom'
)
$ErrorActionPreference='Stop'
$repository=Split-Path -Parent $PSScriptRoot
$project=(Resolve-Path -LiteralPath $ProjectPath).Path
if([IO.Path]::GetExtension($project) -ne '.uproject'){throw 'Select a host .uproject'}
$hostRoot=Split-Path -Parent $project
$manifest=Join-Path $hostRoot "Config\WISEYE\Scenes\$Scene.json"
$sceneData=Get-Content -LiteralPath $manifest -Raw -Encoding UTF8 | ConvertFrom-Json
if(-not $sceneData.prepared){throw 'Initialize the WISEYE rig in the host editor first.'}
# A stable host-path digest isolates same-named projects without persisting private paths in Git.
$hasher=[Security.Cryptography.SHA256]::Create()
try {$identity=([BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($project.ToLowerInvariant())))).Replace('-','').Substring(0,12)} finally {$hasher.Dispose()}
$data=Join-Path $repository "UserData\CustomEnvironments\$identity\$Scene"
$configuration=Join-Path $data 'ue5\WISEYE\Config\WISEYE'
New-Item -ItemType Directory -Path $configuration -Force | Out-Null
foreach($file in Get-ChildItem -LiteralPath (Join-Path $hostRoot 'Config\WISEYE') -File -Recurse) {
    $relative=$file.FullName.Substring((Join-Path $hostRoot 'Config\WISEYE').Length).TrimStart('\')
    $destination=Join-Path $configuration $relative
    if(-not(Test-Path -LiteralPath $destination)) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $destination
    }
}
if(-not(Test-Path -LiteralPath (Join-Path $data 'configs'))) {Copy-Item -LiteralPath (Join-Path $repository 'configs') -Destination $data -Recurse}
$env:WISEYE_PREVIEW_PROJECT=$project
& (Join-Path $PSScriptRoot 'Start-Desktop.ps1') -DataDirectory $data
