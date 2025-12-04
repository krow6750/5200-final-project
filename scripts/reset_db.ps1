param(
    [string]$User = "kevin",
    [string]$Db = "cs2_esports",
    [string]$Server = "127.0.0.1",
    [string]$SqlFile = "chen_final_project.sql",
    [string]$Password = $null
)

$ErrorActionPreference = "Stop"
if ($Password) { $env:PGPASSWORD = $Password }

Write-Host "Resetting $Db as user $User on $Server using $SqlFile..."
psql -U $User -h $Server -d $Db -f $SqlFile
Write-Host "Done."
