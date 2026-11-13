# Удобный запуск из корня проекта:  .\scripts\run.ps1 [--steps N] [--instance-id I]
$py = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
& $py (Join-Path $PSScriptRoot "run_arena.py") @args
