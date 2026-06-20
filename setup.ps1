# ==========================================
# BigPRC One-Time Setup — create local venv on SSD
# Run ONCE per new machine:  .\setup.ps1
# Auto-installs Python if missing (winget / direct download).
# ==========================================

$VENV_DIR = Join-Path $PSScriptRoot "venv"
$PYTHON_EXE = Join-Path $VENV_DIR "Scripts\python.exe"

# ============================================================
# Helper: refresh PATH from registry so freshly-installed
# Python is visible in the current session.
# ============================================================
function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    # Remove common duplicates
    $env:Path = ($env:Path -split ";") | Select-Object -Unique | Where-Object { $_ } -join ";"
}

# ============================================================
# Helper: find a working python.exe in PATH
# ============================================================
function Find-Python {
    $candidates = @(
        (Get-Command python -ErrorAction SilentlyContinue),
        (Get-Command python3 -ErrorAction SilentlyContinue)
    )
    # Also scan Program Files directly (sometimes PATH refresh lags)
    $scanDirs = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312",
        "$env:LOCALAPPDATA\Programs\Python\Python313",
        "$env:LOCALAPPDATA\Programs\Python\Python311",
        "$env:ProgramFiles\Python312",
        "$env:ProgramFiles\Python313",
        "$env:ProgramFiles\Python311",
        "C:\Python312",
        "C:\Python313"
    )
    foreach ($dir in $scanDirs) {
        $exe = Join-Path $dir "python.exe"
        if (Test-Path $exe) { return [PSCustomObject]@{ Source = $exe } }
    }
    foreach ($c in $candidates) { if ($c) { return $c } }
    return $null
}

# ============================================================
# Auto-install Python if missing
# ============================================================
function Install-PythonAuto {
    Write-Host ""
    Write-Host "Python not found. Attempting automatic installation ..." -ForegroundColor Yellow

    # --- Strategy A: winget (built into Win10 1709+ / Win11) ---
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "[A] Trying winget install Python 3.12 ..." -ForegroundColor DarkGray
        winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent 2>&1 | Out-Null
        Refresh-Path
        $py = Find-Python
        if ($py) {
            Write-Host "[OK] Python installed via winget: $($py.Source)" -ForegroundColor Green
            return $py
        }
        Write-Host "[WARN] winget install appeared to succeed but python not on PATH yet" -ForegroundColor Yellow
    } else {
        Write-Host "[A] winget not available on this Windows build" -ForegroundColor DarkGray
    }

    # --- Strategy B: direct download from python.org ---
    Write-Host "[B] Downloading Python 3.12.9 from python.org ..." -ForegroundColor DarkGray
    $installerUrl = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe"
    $installerPath = "$env:TEMP\python-3.12.9-amd64.exe"

    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing -TimeoutSec 120
        Write-Host "[B] Downloaded. Running silent installer (will request Admin) ..." -ForegroundColor DarkGray
        $proc = Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait -PassThru -Verb RunAs
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue

        if ($proc.ExitCode -eq 0) {
            Refresh-Path
            $py = Find-Python
            if ($py) {
                Write-Host "[OK] Python installed via direct download: $($py.Source)" -ForegroundColor Green
                return $py
            }
        }
        Write-Host "[WARN] Installer exit code: $($proc.ExitCode)" -ForegroundColor Yellow
    } catch {
        Write-Host "[WARN] Download/install failed: $_" -ForegroundColor Yellow
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
    }

    # --- Failed ---
    Write-Host ""
    Write-Host "Automatic installation failed." -ForegroundColor Red
    Write-Host "Please install Python 3.9+ manually from https://python.org" -ForegroundColor Yellow
    Write-Host "Tick 'Add Python to PATH' during installation, then re-run setup.ps1" -ForegroundColor Yellow
    return $null
}

# ============================================================
# Step 1: check system Python (auto-install if missing)
# ============================================================
$systemPython = Find-Python
if (-not $systemPython) {
    $systemPython = Install-PythonAuto
    if (-not $systemPython) { exit 1 }
}
$PYTHON_SYSTEM = $systemPython.Source
Write-Host "[OK] System Python: $PYTHON_SYSTEM" -ForegroundColor Green

# Quick version check
$ver = & $PYTHON_SYSTEM --version 2>&1
Write-Host "     Version: $ver" -ForegroundColor DarkGray

# ============================================================
# Step 2: create venv on SSD
# ============================================================
$venvBroken = $false
if (Test-Path $PYTHON_EXE) {
    $testRun = & $PYTHON_EXE -c "print('OK')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SKIP] venv already exists and works at $VENV_DIR" -ForegroundColor DarkGray
    } else {
        Write-Host "[WARN] venv exists but is broken (old machine copy?), recreating ..." -ForegroundColor Yellow
        Remove-Item $VENV_DIR -Recurse -Force -ErrorAction SilentlyContinue
        $venvBroken = $true
    }
}
if (-not (Test-Path $PYTHON_EXE) -or $venvBroken) {
    Write-Host "Creating venv at $VENV_DIR ..."
    & $PYTHON_SYSTEM -m venv $VENV_DIR
    if (-not (Test-Path $PYTHON_EXE)) {
        Write-Host "ERROR: venv creation failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] venv created" -ForegroundColor Green
}

# ============================================================
# Step 3: install packages into venv
# ============================================================
Write-Host "Installing packages into venv ..."
& $PYTHON_EXE -m pip install --quiet jinja2 python-dotenv requests
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip install failed" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Packages installed: jinja2, python-dotenv, requests" -ForegroundColor Green

# ============================================================
# Step 4: verify
# ============================================================
Write-Host "Verifying ..."
& $PYTHON_EXE -c "import jinja2, dotenv, requests; print('All imports OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: import check failed" -ForegroundColor Red
    exit 1
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Setup complete. You can now run:" -ForegroundColor Cyan
Write-Host "   .\preview.ps1" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
