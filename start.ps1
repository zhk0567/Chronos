# Chronos startup script (save as UTF-8 with BOM)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
try { chcp 65001 | Out-Null } catch {}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "Chronos - 个人心理健康洞察" -ForegroundColor Cyan

if (-not (Test-Path "node_modules")) {
    Write-Host "安装 Node 依赖..." -ForegroundColor Yellow
    npm install
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "创建 Python 虚拟环境..." -ForegroundColor Yellow
    python -m venv .venv
    & $venvPython -m pip install -e ./engine
} elseif (-not (& $venvPython -c "import fastapi" 2>$null)) {
    Write-Host "安装 Python 引擎依赖..." -ForegroundColor Yellow
    & $venvPython -m pip install -e ./engine
}

Write-Host "启动开发服务器..." -ForegroundColor Green
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "scripts\dev.ps1")
