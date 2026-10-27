# Build MiniCafe.exe with PyInstaller.
# Run from the project root:  powershell -ExecutionPolicy Bypass -File build_exe.ps1
# NOTE: close any running MiniCafe.exe before building.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# embedded.env holds DATABASE_URL and is bundled into the exe (see database/orm.py).
# Prefer a dedicated embedded.env in the project root (e.g. a restricted DB user), else use .env.
$tmp = Join-Path $env:TEMP "minicafe_build"
New-Item $tmp -ItemType Directory -Force | Out-Null
$embedded = Join-Path $tmp "embedded.env"
if (Test-Path "embedded.env") {
    Copy-Item "embedded.env" $embedded -Force
} elseif (Test-Path ".env") {
    Write-Warning "embedded.env not found - bundling .env instead (make sure it is not an admin DB user!)"
    Copy-Item ".env" $embedded -Force
} else {
    New-Item $embedded -ItemType File -Force | Out-Null
}

# Find available Python executable (prioritizing real python binary over WindowsApp store aliases)
$pyCandidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Launcher\py.exe"
)
$py = $null
foreach ($cand in $pyCandidates) {
    if (Test-Path $cand) {
        $py = $cand
        break
    }
}
if (-not $py) {
    if (Get-Command py -ErrorAction SilentlyContinue) { $py = "py" }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
    else { throw "Python not found!" }
}

Write-Host "Using Python: $py"

# Whole assets folder: sprites, fonts, locales, sounds (assets/sounds) and music (assets/music)
& $py -m PyInstaller --noconfirm --clean --onefile --windowed --name MiniCafe `
    --icon "assets/icon.ico" `
    --add-data "assets;assets" `
    --add-data "database/schema_postgres.sql;database" `
    --add-data "$embedded;." `
    --collect-submodules game `
    --collect-submodules database `
    main.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

Write-Host "Done: dist\MiniCafe.exe"
