# Sync current-year Echo diaries into Chronos data/
$ErrorActionPreference = "Stop"
$chronosRoot = Split-Path $PSScriptRoot -Parent
Set-Location $chronosRoot

$year = (Get-Date).Year
$echoRoot = Join-Path (Split-Path $chronosRoot -Parent) "Echo"
$echoEntries = Join-Path $echoRoot "entries"
$localEntries = Join-Path $chronosRoot "data\entries"

if (-not (Test-Path $localEntries)) {
    New-Item -ItemType Directory -Path $localEntries -Force | Out-Null
}

$removed = 0
$oldFiles = Get-ChildItem $localEntries -Filter "*.json" | Where-Object { -not $_.Name.StartsWith("$year-") }
foreach ($f in $oldFiles) {
    Remove-Item $f.FullName
    $removed++
}

$synced = 0
if (Test-Path $echoEntries) {
    $yearFiles = Get-ChildItem $echoEntries -Filter "$year-*.json"
    foreach ($f in $yearFiles) {
        Copy-Item $f.FullName (Join-Path $localEntries $f.Name) -Force
        $synced++
    }
    Write-Host "Synced $synced entries for year $year to data/entries/"
} else {
    Write-Host "Echo entries not found: $echoEntries"
}

if ($removed -gt 0) {
    Write-Host "Removed $removed non-$year entries"
}

$metaDir = Join-Path $chronosRoot "data\meta"
New-Item -ItemType Directory -Path $metaDir -Force | Out-Null
$watchlist = Join-Path $echoRoot "name-watchlist.json"
if (Test-Path $watchlist) {
    Copy-Item $watchlist (Join-Path $metaDir "name-watchlist.json") -Force
    Write-Host "Copied name-watchlist.json to data/meta/"
}

$count = (Get-ChildItem $localEntries -Filter "$year-*.json").Count
Write-Host "Local total: $count entries for year $year"
