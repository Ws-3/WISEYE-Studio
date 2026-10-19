$ErrorActionPreference = 'Stop'
$version = '1.21.2'
$repository = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $repository 'third_party\mediamtx'
$archiveName = "mediamtx_v${version}_windows_amd64.zip"
$base = "https://github.com/bluenviron/mediamtx/releases/download/v${version}"
$temporary = Join-Path ([IO.Path]::GetTempPath()) ("WISEYE-mediamtx-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary | Out-Null
try {
    $archive = Join-Path $temporary $archiveName
    $checksums = Join-Path $temporary 'checksums.sha256'
    Invoke-WebRequest "$base/$archiveName" -OutFile $archive
    Invoke-WebRequest "$base/checksums.sha256" -OutFile $checksums
    $expectedLine = Get-Content -LiteralPath $checksums | Where-Object { $_ -match [regex]::Escape($archiveName) } | Select-Object -First 1
    if (-not $expectedLine) { throw 'MediaMTX checksum entry was not found.' }
    $expected = ($expectedLine -split '\s+')[0].ToLowerInvariant()
    $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expected) { throw 'MediaMTX checksum verification failed.' }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Expand-Archive -LiteralPath $archive -DestinationPath $destination -Force
    Write-Host "MediaMTX $version installed and verified in $destination"
}
finally {
    Remove-Item -LiteralPath $temporary -Recurse -Force -ErrorAction SilentlyContinue
}
