param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$repository = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$relativePaths = @(
    'runtime', 'logs', 'ue5\WISEYE\Saved\Logs',
    'ue5\WISEYE\Saved\ShaderDebugInfo', 'ue5\WISEYE\Saved\UnrealBuildTool',
    'ue5\WISEYE\Saved\AutoScreenshot.png', 'apps\__pycache__',
    'apps\desktop_app\__pycache__', 'core\__pycache__', 'tests\__pycache__'
)
if ($Apply) {
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
        throw 'Save and close Unreal Editor before cleanup.'
    }
    $desktop = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'apps\.desktop_app' }
    if ($desktop) { throw 'Close WISEYE desktop before cleanup.' }
}
$manifest = foreach ($relativePath in $relativePaths) {
    $target = [IO.Path]::GetFullPath((Join-Path $repository $relativePath))
    if (-not $target.StartsWith($repository + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Target outside repository: $target"
    }
    if (-not (Test-Path -LiteralPath $target)) { continue }
    $entry = Get-Item -LiteralPath $target -Force
    if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point: $target" }
    if ($entry.PSIsContainer) {
        $children = @(Get-ChildItem -LiteralPath $target -Recurse -Force)
        if ($children | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
            throw "Reparse point inside: $target"
        }
        $files = @($children | Where-Object { -not $_.PSIsContainer })
    } else { $files = @($entry) }
    [PSCustomObject]@{path=$target; files=$files.Count; bytes=($files | Measure-Object Length -Sum).Sum}
}
$manifest | Format-Table -AutoSize
if (-not $Apply) {
    Write-Output 'Preview only. Run with -Apply after saving and closing UE and WISEYE.'
    return
}
foreach ($item in $manifest) { Remove-Item -LiteralPath $item.path -Recurse -Force }
Write-Output 'Temporary files removed. Models, papers, environment and experiment outputs preserved.'
