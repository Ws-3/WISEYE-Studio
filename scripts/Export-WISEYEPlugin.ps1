param([string]$OutputDirectory,[string]$Python)
$ErrorActionPreference='Stop'
$repository=Split-Path -Parent $PSScriptRoot
if(-not $OutputDirectory) { $OutputDirectory=Join-Path $repository ('builds\distributions\WISEYE-Plugin-'+(Get-Date -Format 'yyyyMMdd-HHmmss')) }
if(-not $Python) {
    foreach($candidate in @('Tools\Python\python.exe','.venv\Scripts\python.exe','builds\python-env\Scripts\python.exe')) {
        $resolvedPython=Join-Path $repository $candidate
        if(Test-Path -LiteralPath $resolvedPython){$Python=$resolvedPython;break}
    }
}
if(-not $Python){$Python=(Get-Command python -ErrorAction Stop).Source}
& $Python -X utf8 (Join-Path $repository 'packaging\plugin_bundle.py') --output $OutputDirectory
if($LASTEXITCODE -ne 0) { throw 'WISEYE plugin bundle export failed.' }
