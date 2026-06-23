# Chronos dev server (UTF-8 console)
$ErrorActionPreference = "Stop"
$chronosRoot = Split-Path $PSScriptRoot -Parent
Set-Location $chronosRoot

$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
try { chcp 65001 | Out-Null } catch {}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:NODE_OPTIONS = ($env:NODE_OPTIONS, "--enable-source-maps") -join " "

& npm exec -- vite
