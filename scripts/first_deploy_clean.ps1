param(
    [switch]$RecreateVenv,
    [switch]$SkipPipInstall
)

$ErrorActionPreference = "Stop"

function Step($message) {
    Write-Host "`n==> $message" -ForegroundColor Cyan
}

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

Step "Limpiando artefactos locales"
$pathsToDelete = @("migrations", "instance", "__pycache__")
foreach ($path in $pathsToDelete) {
    if (Test-Path $path) {
        Remove-Item -Recurse -Force $path
    }
}

Get-ChildItem -Path "." -Filter "*.db" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path "." -Filter "*.sqlite3" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path "." -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

$uploadsDir = "app\static\uploads"
if (Test-Path $uploadsDir) {
    Get-ChildItem -Path $uploadsDir -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
}

if ($RecreateVenv -and (Test-Path ".venv")) {
    Step "Recreando entorno virtual"
    Remove-Item -Recurse -Force ".venv"
}

if (-not (Test-Path ".venv")) {
    Step "Creando entorno virtual"
    python -m venv .venv
}

$venvPython = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "No se encontro Python del entorno virtual en $venvPython"
}

if (-not $SkipPipInstall) {
    Step "Instalando dependencias"
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt
}

if (-not (Test-Path ".env")) {
    Step "Creando archivo .env desde .env.example"
    Copy-Item ".env.example" ".env"
}

Step "Generando migraciones iniciales"
& $venvPython -m flask --app run.py db init
& $venvPython -m flask --app run.py db migrate -m "init schema"
& $venvPython -m flask --app run.py db upgrade

Step "Creando administrador del sistema (si no existe)"
$adminUsername = if ($env:ADMIN_USERNAME) { $env:ADMIN_USERNAME } else { "admin" }
$adminEmail = if ($env:ADMIN_EMAIL) { $env:ADMIN_EMAIL } else { "admin@cecum.link" }
if ($env:ADMIN_PASSWORD) {
    & $venvPython -m flask --app run.py create-admin --username "$adminUsername" --email "$adminEmail" --password "$env:ADMIN_PASSWORD"
}
else {
    & $venvPython -m flask --app run.py create-admin --username "$adminUsername" --email "$adminEmail"
}

Step "Validando proyecto"
& $venvPython -m compileall app
& $venvPython -c "from app import create_app; app=create_app(); print('APP_OK', len(app.url_map._rules))"

Write-Host "`nDespliegue limpio completado." -ForegroundColor Green
Write-Host "Para iniciar: .\.venv\Scripts\python.exe run.py"
