param([string]$BuildWorkspace=(Join-Path (Split-Path -Parent $PSScriptRoot) 'ue5\WISEYE'))
$ErrorActionPreference='Stop'
$repository=Split-Path -Parent $PSScriptRoot
$workspace=(Resolve-Path -LiteralPath $BuildWorkspace).Path
$project=Join-Path $workspace 'test.uproject'
if(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like "*$project*"}) {
    throw 'Close the preview before changing its plugin resource junctions.'
}
foreach($plugin in @('ProjectAirSim','Drone')) {
    $link=Join-Path $workspace "Plugins\$plugin\Content"
    $local=Join-Path $repository "ue5\WISEYE\Plugins\$plugin\Content"
    $item=Get-Item -LiteralPath $link -Force
    if($item.LinkType -ne 'Junction'){throw "Expected an existing junction: $link"}
    $old=[string]$item.Target
    if($old.TrimEnd('\') -eq $local.TrimEnd('\')){continue}
    $resolvedLocal=(Resolve-Path -LiteralPath $local).Path
    if(-not $link.StartsWith($workspace+'\') -or -not $resolvedLocal.StartsWith($repository+'\')){throw 'Resource path outside expected workspace'}
    if((Get-Item -LiteralPath $local -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Local plugin Content must be a physical directory'}
    foreach($file in Get-ChildItem -LiteralPath $link -File -Recurse) {
        $relative=$file.FullName.Substring($link.Length).TrimStart('\')
        $destination=Join-Path $local $relative
        if(-not(Test-Path -LiteralPath $destination)){throw "Local asset missing: $destination"}
        if((Get-FileHash -LiteralPath $file.FullName).Hash -ne (Get-FileHash -LiteralPath $destination).Hash){throw "Local asset mismatch: $relative"}
    }
    # Non-recursive removal of the junction itself. Never remove its target.
    [IO.Directory]::Delete($link)
    try {New-Item -ItemType Junction -Path $link -Target $local | Out-Null}
    catch {New-Item -ItemType Junction -Path $link -Target $old | Out-Null;throw}
    Write-Output "$plugin Content now references the project-local asset copy."
}
