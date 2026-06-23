# 本地跑完整分析流水线（18 步三期）
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$env:CHRONOS_DATA_DIR = Join-Path (Get-Location) "data"
$env:PYTHONUTF8 = "1"
$env:CHRONOS_EXTRACT_MODEL = "gemma3:4b"

Write-Host "[chronos] 数据目录: $env:CHRONOS_DATA_DIR"
Write-Host "[chronos] 常驻城市: 洛阳 (34.6197, 112.454)"
Write-Host "[chronos] 抽取模型: gemma3:4b (批量 12 篇/次)"

$python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

& $python (Join-Path $PSScriptRoot "run_analysis.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "[chronos] 分析产物: data\analysis\runs\"
