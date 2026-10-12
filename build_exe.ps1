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

# Whole assets folder: sprites, fonts, locales, sounds (assets/sounds) and music (assets/music)
py -m PyInstaller --noconfirm --clean --onefile --windowed --name MiniCafe `
    --add-data "assets;assets" `
    --add-data "database/schema_postgres.sql;database" `
    --add-data "$embedded;." `
    --collect-submodules game `
    --collect-submodules database `
    main.py

Write-Host "Done: dist\MiniCafe.exe"
