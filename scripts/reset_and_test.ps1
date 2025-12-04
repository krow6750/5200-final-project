param(
    [string]$User = "kevin",
    [string]$Db = "cs2_esports",
    [string]$Server = "127.0.0.1",
    [string]$Password = "808080",
    [string]$SqlFile = "chen_final_project.sql"
)

$ErrorActionPreference = "Stop"

# Configure env vars
$env:PGPASSWORD = $Password
$env:DATABASE_URL = "postgresql://${User}:${Password}@${Server}:5432/${Db}"
Write-Host "Using DATABASE_URL=$env:DATABASE_URL"

# Reload schema/seed
Write-Host "Reloading $Db..."
psql -U $User -h $Server -d $Db -f $SqlFile

# Smoke test
Write-Host "Running smoke test..."
python -m app.smoke_test
Write-Host "All done."
