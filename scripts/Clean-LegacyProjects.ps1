#requires -Version 7.0
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param([switch]$Execute)

$ErrorActionPreference = 'Stop'
# This is a machine-specific, audited cleanup, not a general disk cleaner.
$sourceRoot = 'F:\WISEYE-Studio'
$sourceItem = Get-Item -LiteralPath $sourceRoot -Force
if ($sourceItem.FullName -ne $sourceRoot -or ($sourceItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'The canonical source must be the physical F:\WISEYE-Studio directory.'
}
if ((Split-Path -Parent $PSScriptRoot) -ne $sourceRoot) { throw 'Run the script from the canonical F: project.' }
if (-not $Execute) { $WhatIfPreference = $true }

$latestZip = Join-Path $sourceRoot 'releases\WISEYE-20261027-City-Windows-x64.zip'
$deliveryFile = $latestZip + '.delivery-verified.json'
$receipt = Get-Content -LiteralPath $deliveryFile -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $receipt.copy_readback_verified -or
    (Get-Item -LiteralPath $latestZip).Length -ne $receipt.bytes -or
    $receipt.destination_sha256 -ne '7450d6daa7bdf5fa1134f0af3f12ddd8f211f2c099ac5082df66e8cf701f36ba') {
    throw 'The latest retained release does not match the verified delivery record.'
}
foreach ($required in @('.git','apps','core','ue5\WISEYE\Source','ue5\WISEYE\Content\WISEYE\Scenes\city\CitySample.umap')) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot $required))) { throw "Missing latest project: $required" }
}
$busy = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^(UnrealEditor(?:-Cmd)?|test-Win64-Shipping|WISEYE|pythonw?)\.exe$' -and
    ($_.CommandLine -like '*WISEYE-Studio*' -or $_.CommandLine -like '*WISEYE-BuildWorkspace*')
}
if ($busy) { throw 'Close WISEYE, UE, flight workers and build Python processes first.' }

# Fixed roots only. Shared E:\Projects\Scene and ProjectAirSim-Evaluation are retained.
$oldRoots = @('E:\Projects\WISEYE-Studio', 'E:\Projects\WISEYE-BuildWorkspace')
$generated = @(
    'builds\desktop', 'builds\pyinstaller', 'builds\smoke-data', 'builds\logs',
    'ue5\WISEYE\Binaries', 'ue5\WISEYE\Intermediate', 'ue5\WISEYE\DerivedDataCache',
    'ue5\WISEYE\Saved\Cooked', 'ue5\WISEYE\Saved\Logs',
    'ue5\WISEYE\Saved\ShaderDebugInfo', 'ue5\WISEYE\Saved\Shaders',
    'ue5\WISEYE\Saved\UnrealBuildTool', 'releases\.incoming-20261023-001704'
)
$oldFiles = @(
    'releases\WISEYE-20261023-Windows-x64.zip',
    'releases\WISEYE-20261023-Windows-x64.zip.json',
    'releases\WISEYE-20261023-Windows-x64.zip.sha256',
    'releases\WISEYE-Desktop-Update-20261026.zip',
    'releases\WISEYE-Desktop-Update-20261026.zip.sha256',
    'releases\运行说明.txt', 'releases\delivery-verified.json',
    'projectairsim_client.log', 'ue5\WISEYE\projectairsim_server.log'
)
$targets = @($generated + $oldFiles | ForEach-Object { Join-Path $sourceRoot $_ }) + $oldRoots

function Get-LinksWithoutFollowing([string]$RootPath) {
    $pending = [Collections.Generic.Stack[string]]::new()
    $pending.Push($RootPath)
    while ($pending.Count) {
        foreach ($child in Get-ChildItem -LiteralPath $pending.Pop() -Force -ErrorAction Stop) {
            if ($child.Attributes -band [IO.FileAttributes]::ReparsePoint) { $child }
            elseif ($child.PSIsContainer) { $pending.Push($child.FullName) }
        }
    }
}

# Validate the complete plan and collect links BEFORE removing anything.
$plan = @()
foreach ($target in $targets) {
    if (-not (Test-Path -LiteralPath $target)) { continue }
    $item = Get-Item -LiteralPath $target -Force
    if ($item.FullName -ne $target -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Unexpected target or redirected root: $target"
    }
    if ($target -notin $oldRoots -and -not $target.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Target outside the audited workspace: $target"
    }
    $links = @()
    if ($item.PSIsContainer) {
        $links = @(Get-LinksWithoutFollowing $target)
        foreach ($link in $links) {
            if (-not $link.FullName.StartsWith($target + '\', [StringComparison]::OrdinalIgnoreCase)) {
                throw "Link outside cleanup root: $($link.FullName)"
            }
        }
    }
    $plan += [pscustomobject]@{ Path=$item.FullName; Directory=$item.PSIsContainer; Links=$links }
}

Write-Host 'KEEP: F:\WISEYE-Studio source, Content, Models, configs, Python dependencies and latest 20261027 ZIP.'
Write-Host 'KEEP: CitySample original library, shared dependencies, user AppData and engine/tool installations.'
Write-Host 'The two unreadable Python __pycache__ folders are not in this cleanup plan.'
Write-Host 'Source UE binaries/caches will need rebuilding; the latest standalone ZIP remains usable.'

$results = @()
foreach ($entry in $plan) {
    if ($PSCmdlet.ShouldProcess($entry.Path, 'Delete audited old project or generated artifact')) {
        # Delete junction entries without recursion; never traverse their targets.
        foreach ($link in $entry.Links) {
            Remove-Item -LiteralPath $link.FullName -Force -ErrorAction Stop
        }
        if ($entry.Directory) { Remove-Item -LiteralPath $entry.Path -Recurse -Force -ErrorAction Stop }
        else { Remove-Item -LiteralPath $entry.Path -Force -ErrorAction Stop }
        if (Test-Path -LiteralPath $entry.Path) { throw "Cleanup incomplete: $($entry.Path)" }
        $results += $entry.Path
        Write-Host "Deleted: $($entry.Path)"
    }
}
if ($Execute -and -not $WhatIfPreference) {
    $record = [ordered]@{ completed_at=(Get-Date).ToString('o'); removed=$results; retained_source=$sourceRoot; retained_release=$latestZip }
    $record | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $sourceRoot 'docs\evidence\cleanup-20261027\executed.json') -Encoding UTF8
} else {
    Write-Host 'PREVIEW ONLY: no files were deleted. Add -Execute to perform this exact cleanup.'
}
