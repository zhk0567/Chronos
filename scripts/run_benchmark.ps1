# Run Chronos benchmark on all fixtures
Set-Location $PSScriptRoot\..
$env:CHRONOS_DATA_DIR = Join-Path (Get-Location) "data"
python -m benchmark.run_eval --all --save