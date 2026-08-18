$databasePath = Join-Path $PSScriptRoot "meetup_bot.sqlite3"

Write-Host "WARNING: This will permanently delete all local registrations, funnel data, statuses, and other SQLite data." -ForegroundColor Yellow

if (-not (Test-Path -LiteralPath $databasePath -PathType Leaf)) {
    Write-Host "Database does not exist. Nothing to reset."
    exit 0
}

$confirmation = Read-Host "Type RESET to continue"
if ($confirmation -cne "RESET") {
    Write-Host "Database reset cancelled."
    exit 0
}

# An exclusive handle makes an active SQLite lock/use visible before deletion.
$databaseHandle = $null
try {
    $databaseHandle = [System.IO.File]::Open(
        $databasePath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
}
catch [System.IO.IOException] {
    Write-Host "Database is locked or in use. Stop the bot first, then run this script again." -ForegroundColor Red
    exit 1
}
finally {
    if ($null -ne $databaseHandle) {
        $databaseHandle.Dispose()
    }
}

try {
    Remove-Item -LiteralPath $databasePath -Force -ErrorAction Stop
}
catch {
    Write-Host "Database could not be deleted because it is locked or in use. Stop the bot first, then run this script again." -ForegroundColor Red
    exit 1
}

Write-Host "Database deleted successfully." -ForegroundColor Green
Write-Host "The next time you run 'python bot.py', the database and tables will be recreated automatically."
