param(
  [string]$PythonBin = "python"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot "backend\.venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

& $PythonBin -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'
if ($LASTEXITCODE -ne 0) { throw "Python 3.12+ is required." }

# A virtual environment copied from macOS cannot be reused on Windows.
# Preserve it instead of mixing files from two platforms in the same environment.
if ((Test-Path -LiteralPath $venvPath) -and -not (Test-Path -LiteralPath $venvPython)) {
  $resolvedVenv = (Resolve-Path -LiteralPath $venvPath).Path
  $backupPath = [IO.Path]::GetFullPath((Join-Path $repoRoot (".runtime\backups\venv-" + [guid]::NewGuid())))
  if ($resolvedVenv -ne [IO.Path]::GetFullPath($venvPath) -or
      -not $backupPath.StartsWith($repoRoot + "\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Virtual environment paths are outside the expected workspace."
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backupPath) | Out-Null
  Move-Item -LiteralPath $resolvedVenv -Destination $backupPath
  Write-Host "Preserved the previous environment at $backupPath"
}

if (-not (Test-Path -LiteralPath $venvPython)) {
  & $PythonBin -m venv $venvPath
  if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}
& $venvPython -m pip install -r (Join-Path $repoRoot "backend\requirements-dev.lock")
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
& $venvPython -m pip install --no-deps --no-build-isolation -e (Join-Path $repoRoot "backend")
if ($LASTEXITCODE -ne 0) { throw "Backend package installation failed." }
& npm.cmd --prefix (Join-Path $repoRoot "frontend") ci --no-fund
if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }
Write-Host "Setup complete. See README.md for the Windows startup commands."
