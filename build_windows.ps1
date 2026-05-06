$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$venv = Join-Path $root ".venv"

function Test-LocalPython {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return $false
    }

    & $Path --version *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-LocalPython $python)) {
    if (Test-Path $venv) {
        Write-Host "Removing broken local virtual environment ..."
        Remove-Item -LiteralPath $venv -Recurse -Force
    }
    Write-Host "Creating local virtual environment in .venv ..."
    py -3 -m venv $venv
}

& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $root "requirements-build.txt")

$addData = @(
    "--add-data", "$root\src\style.qss;src",
    "--add-data", "$root\Sozai;Sozai"
)

$icon = Join-Path $root "app_icon.ico"
$iconArgs = @()
if (Test-Path $icon) {
    $iconArgs = @("--icon", $icon)
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name NekoDiary `
    @iconArgs `
    @addData `
    (Join-Path $root "src\main.py")

Write-Host "Built: $root\dist\NekoDiary\NekoDiary.exe"
