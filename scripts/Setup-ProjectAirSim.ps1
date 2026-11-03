param(
    [string]$AirSimRoot,
    [string]$EngineRoot = $env:UE_ROOT,
    [string]$VisualStudioRoot,
    [string]$Python = 'python',
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$projectsRoot = Split-Path -Parent $repository
if (-not $AirSimRoot) { $AirSimRoot = Join-Path $repository 'builds\dependencies\ProjectAirSimSource' }
$pinnedCommit = '62229cd7c77ad31da7bc8aba8dd6303c564d8ba2'
$patch = Join-Path $repository 'third_party\patches\projectairsim-simpleflight-completion.patch'

if (-not (Test-Path -LiteralPath (Join-Path $AirSimRoot '.git'))) {
    git clone https://github.com/iamaisim/ProjectAirSim.git $AirSimRoot
    if ($LASTEXITCODE -ne 0) { throw 'Project AirSim clone failed.' }
    git -C $AirSimRoot checkout $pinnedCommit
    if ($LASTEXITCODE -ne 0) { throw 'Project AirSim pinned commit checkout failed.' }
    git -C $AirSimRoot apply --ignore-space-change $patch
    if ($LASTEXITCODE -ne 0) { throw 'WISEYE Project AirSim patch failed.' }
} else {
    $head = (git -C $AirSimRoot rev-parse HEAD).Trim()
    if ($head -ne $pinnedCommit) { throw "Project AirSim must be at pinned commit $pinnedCommit; current $head." }
    # A clean checkout is expected to fail this reverse-patch probe. Windows
    # PowerShell turns native stderr into a terminating error under Stop.
    $probeErrorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        git -C $AirSimRoot apply --reverse --check --ignore-space-change $patch 2>&1 | Out-Null
        $patchAlreadyApplied = ($LASTEXITCODE -eq 0)
    } finally {
        $ErrorActionPreference = $probeErrorPreference
    }
    if (-not $patchAlreadyApplied) {
        git -C $AirSimRoot diff --quiet HEAD
        if ($LASTEXITCODE -ne 0) { throw 'Project AirSim has unrelated local changes. Preserve them before setup.' }
        git -C $AirSimRoot apply --ignore-space-change $patch
        if ($LASTEXITCODE -ne 0) { throw 'WISEYE Project AirSim patch failed.' }
    }
}

# UE 5.8 marks GLastGCFrame at collection start; wait for true completion
# before creating another robot. Keep this additive patch reproducible.
$gcPatch = Join-Path $repository 'third_party\patches\projectairsim-ue58-gc-completion.patch'
$gcErrorPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    git -C $AirSimRoot apply --reverse --check --ignore-space-change $gcPatch 2>&1 | Out-Null
    $gcPatchApplied = ($LASTEXITCODE -eq 0)
} finally { $ErrorActionPreference = $gcErrorPreference }
if (-not $gcPatchApplied) {
    git -C $AirSimRoot apply --check --ignore-space-change $gcPatch
    if ($LASTEXITCODE -ne 0) { throw 'GC patch does not match this dependency; preserve local changes and inspect it.' }
    git -C $AirSimRoot apply --ignore-space-change $gcPatch
    if ($LASTEXITCODE -ne 0) { throw 'WISEYE UE 5.8 GC completion patch failed.' }
}

# Preserve the current control response during repeated wall contacts.
$wallPatch = Join-Path $repository 'third_party\patches\projectairsim-wall-contact.patch'
$wallErrorPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    git -C $AirSimRoot apply --reverse --check --ignore-space-change $wallPatch 2>&1 | Out-Null
    $wallPatchApplied = ($LASTEXITCODE -eq 0)
} finally { $ErrorActionPreference = $wallErrorPreference }
if (-not $wallPatchApplied) {
    git -C $AirSimRoot apply --check --ignore-space-change $wallPatch
    if ($LASTEXITCODE -ne 0) { throw 'Wall-contact patch does not match this dependency; preserve local changes and inspect it.' }
    git -C $AirSimRoot apply --ignore-space-change $wallPatch
    if ($LASTEXITCODE -ne 0) { throw 'WISEYE wall-contact patch failed.' }
}

# Standalone monolithic games do not expose the editor module filename API.
$cookedPatch = Join-Path $repository 'third_party\patches\projectairsim-cooked-game.patch'
$cookedErrorPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    git -C $AirSimRoot apply --reverse --check --ignore-space-change $cookedPatch 2>&1 | Out-Null
    $cookedPatchApplied = ($LASTEXITCODE -eq 0)
} finally { $ErrorActionPreference = $cookedErrorPreference }
if (-not $cookedPatchApplied) {
    git -C $AirSimRoot apply --check --ignore-space-change $cookedPatch
    if ($LASTEXITCODE -ne 0) { throw 'Cooked-game patch does not match; preserve dependency changes and inspect.' }
    git -C $AirSimRoot apply --ignore-space-change $cookedPatch
    if ($LASTEXITCODE -ne 0) { throw 'WISEYE cooked-game patch failed.' }
}

function Install-WiseEyeAirSimLinks {
    $pluginRoot = Join-Path $repository 'ue5\WISEYE\Plugins'
    $sourcePlugins = Join-Path $AirSimRoot 'unreal\Blocks\Plugins'
    foreach ($plugin in @('ProjectAirSim','Drone')) {
        $local = Join-Path $pluginRoot $plugin
        $source = Join-Path $sourcePlugins $plugin
        New-Item -ItemType Directory -Force -Path $local | Out-Null
        Copy-Item -LiteralPath (Join-Path $source "$plugin.uplugin") -Destination $local -Force
        $folders = if ($plugin -eq 'ProjectAirSim') { @('Source','SimLibs','Content','Resources') } else { @('Content','Resources') }
        foreach ($folder in $folders) {
            $target = Join-Path $source $folder
            if (-not (Test-Path -LiteralPath $target)) { continue }
            $link = Join-Path $local $folder
            if (Test-Path -LiteralPath $link) {
                $item = Get-Item -LiteralPath $link -Force
                $actualTarget = [IO.Path]::GetFullPath([string]$item.Target).TrimEnd('\')
                $expectedTarget = [IO.Path]::GetFullPath($target).TrimEnd('\')
                if ($item.LinkType -ne 'Junction' -or $actualTarget -ne $expectedTarget) {
                    throw "Refusing to replace non-matching plugin path: $link"
                }
            } else {
                New-Item -ItemType Junction -Path $link -Target $target | Out-Null
            }
        }
    }
}

$venvPython = Join-Path $AirSimRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $Python -m venv (Join-Path $AirSimRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Project AirSim Python environment creation failed.' }
}
& $venvPython -c 'import projectairsim'
if ($LASTEXITCODE -ne 0) {
    & $venvPython -m pip install -e (Join-Path $AirSimRoot 'client\python\projectairsim')
    if ($LASTEXITCODE -ne 0) { throw 'Project AirSim Python client installation failed.' }
}

if (-not $SkipBuild) {
    if (-not $EngineRoot) {
        $engineFile = Join-Path $PSScriptRoot 'engine-root.local.txt'
        if (Test-Path -LiteralPath $engineFile) { $EngineRoot = (Get-Content -LiteralPath $engineFile -Raw).Trim() }
    }
    if (-not $VisualStudioRoot) {
        $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
        if (Test-Path -LiteralPath $vswhere) { $VisualStudioRoot = (& $vswhere -latest -products * -property installationPath).Trim() }
    }
    if (-not $EngineRoot -or -not $VisualStudioRoot) { throw 'EngineRoot and VisualStudioRoot are required to build Project AirSim sim libraries.' }
    & (Join-Path $PSScriptRoot 'Test-ProjectAirSimBuild.ps1') -AirSimRoot $AirSimRoot -EngineRoot $EngineRoot -VisualStudioRoot $VisualStudioRoot -Stage SimLibs
}
# SimLibs does not exist on a clean checkout until the first build completes.
Install-WiseEyeAirSimLinks
Write-Host 'Project AirSim is patched and linked into WISEYE. For a configured source project, run scripts/Start-ProjectAirSim.ps1. See docs/USER_GUIDE.md for the current preview entry.'
