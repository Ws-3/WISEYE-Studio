param([string]$VisualStudioRoot='E:\Programs\Microsoft\VisualStudio\2022\Community')
$ErrorActionPreference='Stop'
$repository=Split-Path -Parent $PSScriptRoot
$source=Join-Path $repository 'builds\dependencies\jsbsim-1.2.4'
if (-not (Test-Path -LiteralPath (Join-Path $source 'CMakeLists.txt'))) {
    & git clone --depth 1 --branch v1.2.4 https://github.com/JSBSim-Team/jsbsim.git $source
    if ($LASTEXITCODE -ne 0) { throw 'JSBSim download failed' }
}
$revision=(& git -C $source rev-parse HEAD).Trim()
if ($revision -ne 'e07a7d810d4f1048039d42545d008b8a998636fa') { throw 'Unexpected JSBSim source revision' }
$cmake=Join-Path $VisualStudioRoot 'Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
$build=Join-Path $repository 'builds\jsbsim-native'
$destination=Join-Path $repository 'ue5\WISEYE\ThirdParty\JSBSim'
& $cmake -S (Join-Path $repository 'third_party\jsbsim_adapter') -B $build -G 'Visual Studio 17 2022' -A x64 "-DJSBSIM_SOURCE=$source" "-DCMAKE_INSTALL_PREFIX=$destination"
if ($LASTEXITCODE -ne 0) { throw 'JSBSim configure failed' }
& $cmake --build $build --config Release --target WiseEyeJSBSim --parallel 8
if ($LASTEXITCODE -ne 0) { throw 'JSBSim build failed' }
New-Item -ItemType Directory -Path (Join-Path $destination 'bin') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $build 'Release\WiseEyeJSBSim.dll') -Destination (Join-Path $destination 'bin\WiseEyeJSBSim.dll') -Force
Copy-Item -LiteralPath (Join-Path $source 'COPYING') -Destination (Join-Path $destination 'JSBSim-LICENSE.txt') -Force
@{version='1.2.4';commit=$revision;source='https://github.com/JSBSim-Team/jsbsim';adapter='third_party/jsbsim_adapter';license='LGPL-2.1-or-later'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $destination 'version.json') -Encoding UTF8
