[CmdletBinding()]
param(
    [string]$Python = "py"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath ".\.venv\Scripts\python.exe")) {
    & $Python -m venv ".\.venv"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python build environment."
    }
}

$buildPython = ".\.venv\Scripts\python.exe"
& $buildPython -m pip install --disable-pip-version-check -r ".\requirements-build.txt"
if ($LASTEXITCODE -ne 0) {
    throw "Could not install the build requirements."
}

New-Item -ItemType Directory -Force -Path ".\build", ".\dist" | Out-Null
& $buildPython -m PyInstaller `
    --clean `
    --noconfirm `
    --onefile `
    --windowed `
    --name "Character Card Pro" `
    --distpath ".\dist" `
    --workpath ".\build" `
    --specpath ".\build" `
    ".\chub_card_editor.py"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed to build Character Card Pro."
}

Write-Host "Built: $projectRoot\dist\Character Card Pro.exe"
