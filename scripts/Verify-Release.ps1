param([Parameter(Mandatory=$true)][string]$ReleaseRoot)
$ErrorActionPreference = 'Stop'
$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$manifest = Get-Content -LiteralPath (Join-Path $release 'checksums.json') -Raw -Encoding utf8 | ConvertFrom-Json
$entries = @($manifest.PSObject.Properties)
foreach ($entry in $entries) {
    $path = [IO.Path]::GetFullPath((Join-Path $release $entry.Name))
    if (-not $path.StartsWith($release + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid manifest path' }
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing file: $($entry.Name)" }
    if ((Get-Item -LiteralPath $path).Length -ne $entry.Value.bytes) { throw "Size mismatch: $($entry.Name)" }
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $entry.Value.sha256) { throw "Hash mismatch: $($entry.Name)" }
}
Write-Output "Verified $($entries.Count) release files."
