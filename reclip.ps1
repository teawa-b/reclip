$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is required. Install Python 3.10+ and run this script again."
}

if (-not (Test-Path ".venv")) {
    Write-Host "Setting up virtual environment..."
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

if (-not $env:PORT) {
    $env:PORT = "8899"
}

Write-Host ""
Write-Host "  ReClip is running at http://localhost:$env:PORT"
Write-Host ""
& ".\.venv\Scripts\python.exe" app.py
