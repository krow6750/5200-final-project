$ErrorActionPreference = "Stop"
$env:DATABASE_URL = $env:DATABASE_URL -ne $null ? $env:DATABASE_URL : "postgresql://kevin:808080@127.0.0.1:5432/cs2_esports"
Write-Host "Using DATABASE_URL=$env:DATABASE_URL"
python -m app.smoke_test
