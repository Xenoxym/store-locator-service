# scripts/deploy/seed-cloudsql.ps1

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Resolve-Path "$SCRIPT_DIR\..\.."

. "$SCRIPT_DIR\gcp-config.ps1"

Set-Location $PROJECT_ROOT

$env:DATABASE_URL = "postgresql://$DB_USER`:$DB_PASSWORD@localhost:5433/$DB_NAME"

Write-Host "DATABASE_URL=$env:DATABASE_URL"

Write-Host ""
Write-Host "Creating tables..."
python -c "from app.db.base import Base; from app.db.session import engine; import app.models; Base.metadata.create_all(bind=engine)"

Write-Host ""
Write-Host "Loading stores..."
python -m scripts.load_stores data/stores_1000.csv

Write-Host ""
Write-Host "Seeding users..."
python -m scripts.seed_users

Write-Host ""
Write-Host "Verifying counts..."
python -c "from app.db.session import SessionLocal; from app.models.store import Store; from app.models.user import User; db=SessionLocal(); print('stores:', db.query(Store).count()); print('users:', db.query(User).count()); db.close()"

Write-Host ""
Write-Host "Cloud SQL seed complete."