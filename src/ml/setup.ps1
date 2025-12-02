Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# override when invoking .\setup_py36.ps1 -PyVersion 3.6.8 -EnvName .venv36
param(
  [string]$PyVersion = '3.6.8',
  [string]$EnvName   = '.venv36',
  [string]$ReqFile   = 'HiGitClass\requirements.txt'
)

#check pyenv
$pyenvRoot = $env:PYENV_ROOT
if (-not $pyenvRoot) { $pyenvRoot = Join-Path $env:USERPROFILE '.pyenv\pyenv-win' }
$pyenvBin  = Join-Path $pyenvRoot 'bin'
$pyenvShims= Join-Path $pyenvRoot 'shims'

foreach ($p in @($pyenvBin,$pyenvShims)) {
  if (Test-Path $p -and ($env:Path -notlike "*$p*")) { $env:Path = "$p;$env:Path" }
}

if (-not (Get-Command pyenv -ErrorAction SilentlyContinue)) {
  throw "pyenv-win not found on PATH. Install from https://github.com/pyenv-win/pyenv-win and rerun."
}

Write-Host "Installing Python $PyVersion via pyenv (idempotent)…"
pyenv install -s $PyVersion | Out-Null

Write-Host "Setting local Python to $PyVersion in this directory…"
pyenv local $PyVersion

$python = 'python'
if (Test-Path $EnvName) {
  Write-Host "Removing existing virtual environment '$EnvName'…"
  Remove-Item -Recurse -Force $EnvName
}
Write-Host "Creating virtual environment '$EnvName'…"
& $python -m venv $EnvName

$venvPy = Join-Path $EnvName 'Scripts\python.exe'
$venvPip = { & $venvPy -m pip @args }
Write-Host "Upgrading pip/setuptools/wheel with version caps…"
& $venvPy -m pip install --upgrade "pip<22" "setuptools<60" "wheel<0.38"

if (Test-Path $ReqFile) {
  Write-Host "Installing from $ReqFile…"
  & $venvPy -m pip install -r $ReqFile
} else {
  Write-Host "No $ReqFile found; skipping."
}

Write-Host "Installing smart_open==1.9.0…"
& $venvPy -m pip install "smart_open==1.9.0"

$pyver = & $venvPy -V
Write-Host ""
Write-Host "Done."
Write-Host "Environment:  $EnvName"
Write-Host "Interpreter:  $venvPy"
Write-Host "Python:       $pyver"
Write-Host ""
Write-Host "To use the environment in the current shell:"
Write-Host "  `& `"$((Resolve-Path $EnvName).Path)\Scripts\Activate.ps1`""
