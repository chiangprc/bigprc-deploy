# ============================================================
# sync_tokens.ps1 — Design Token sync (Windows)
# Copies the canonical _tokens.css to all consumer locations.
# ⚠  _tokens.css is the SINGLE SOURCE OF TRUTH.
# ============================================================
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Src = Join-Path $ScriptDir "root\scripts\templates\_tokens.css"

if (-not (Test-Path $Src)) {
    Write-Error "Canonical source not found: $Src"
    exit 1
}

# custom-pages/css/design-tokens.css
$DstCss = Join-Path $ScriptDir "root\custom-pages\css\design-tokens.css"
$DstDir = Split-Path -Parent $DstCss
if (-not (Test-Path $DstDir)) { New-Item -ItemType Directory -Force $DstDir | Out-Null }
Copy-Item $Src $DstCss -Force
Write-Output "✅  $DstCss"

Write-Output ""
Write-Output "Design tokens synced from canonical source."
Write-Output "  source: $Src"
