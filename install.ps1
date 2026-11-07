# Windows launcher for install.py: finds Python 3 and runs the installer with your arguments.
# Usage:  .\install.ps1 --project C:\code\my-app      (see: .\install.ps1 --help)
$ErrorActionPreference = 'Stop'
$installer = Join-Path $PSScriptRoot 'install.py'

foreach ($candidate in @('py -3', 'python3', 'python')) {
    $parts = $candidate -split ' '
    $exe = $parts[0]
    $pre = @($parts | Select-Object -Skip 1)
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
    & $exe @pre -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>$null
    if ($LASTEXITCODE -eq 0) {
        & $exe @pre $installer @args
        exit $LASTEXITCODE
    }
}

Write-Error 'Python 3.8 or newer is required (the kit''s hooks use it). Install it with the Python install manager from https://www.python.org/downloads/ and run this again.'
exit 1
