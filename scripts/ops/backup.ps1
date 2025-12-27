# Backup Script for Retail OS
# Run this script regularly to backup critical data

$ErrorActionPreference = "Stop"

# Configuration
$PROJECT_ROOT = "c:\Users\deepak.chhabra\OneDrive - Datacom\Documents\Trademe Integration"
$BACKUP_ROOT = "$PROJECT_ROOT\backups"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_DIR = "$BACKUP_ROOT\$TIMESTAMP"

# Create backup directory
Write-Host "Creating backup directory: $BACKUP_DIR" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null

# Backup database
Write-Host "Backing up database..." -ForegroundColor Yellow
if (Test-Path "$PROJECT_ROOT\trademe_store.db") {
    Copy-Item "$PROJECT_ROOT\trademe_store.db" "$BACKUP_DIR\trademe_store.db"
    Write-Host "✓ Database backed up" -ForegroundColor Green
} else {
    Write-Host "⚠ Database not found" -ForegroundColor Red
}

# Backup .env file
Write-Host "Backing up environment configuration..." -ForegroundColor Yellow
if (Test-Path "$PROJECT_ROOT\.env") {
    Copy-Item "$PROJECT_ROOT\.env" "$BACKUP_DIR\.env"
    Write-Host "✓ Environment file backed up" -ForegroundColor Green
} else {
    Write-Host "⚠ .env file not found" -ForegroundColor Red
}

# Backup exports directory
Write-Host "Backing up exports..." -ForegroundColor Yellow
if (Test-Path "$PROJECT_ROOT\exports") {
    Compress-Archive -Path "$PROJECT_ROOT\exports\*" -DestinationPath "$BACKUP_DIR\exports.zip" -Force
    Write-Host "✓ Exports backed up" -ForegroundColor Green
} else {
    Write-Host "⚠ Exports directory not found" -ForegroundColor Red
}

# Backup media (if not too large)
Write-Host "Checking media directory size..." -ForegroundColor Yellow
if (Test-Path "$PROJECT_ROOT\data\media") {
    $mediaSize = (Get-ChildItem "$PROJECT_ROOT\data\media" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "Media directory size: $([math]::Round($mediaSize, 2)) MB" -ForegroundColor Cyan
    
    if ($mediaSize -lt 500) {
        Write-Host "Backing up media (small enough)..." -ForegroundColor Yellow
        Compress-Archive -Path "$PROJECT_ROOT\data\media\*" -DestinationPath "$BACKUP_DIR\media.zip" -Force
        Write-Host "✓ Media backed up" -ForegroundColor Green
    } else {
        Write-Host "⚠ Media directory too large ($([math]::Round($mediaSize, 2)) MB), skipping" -ForegroundColor Yellow
        Write-Host "  Consider backing up media separately or using cloud storage" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠ Media directory not found" -ForegroundColor Red
}

# Backup critical scripts
Write-Host "Backing up critical scripts..." -ForegroundColor Yellow
$criticalScripts = @(
    "scripts\run_pipeline.py",
    "scripts\run_dual_site_pipeline.py",
    "scripts\enrich_products.py",
    "scripts\monitor_live.py"
)

$scriptsBackupDir = "$BACKUP_DIR\scripts"
New-Item -ItemType Directory -Path $scriptsBackupDir -Force | Out-Null

foreach ($script in $criticalScripts) {
    $fullPath = "$PROJECT_ROOT\$script"
    if (Test-Path $fullPath) {
        Copy-Item $fullPath "$scriptsBackupDir\$(Split-Path $script -Leaf)"
    }
}
Write-Host "✓ Scripts backed up" -ForegroundColor Green

# Create backup manifest
$manifest = @{
    timestamp = $TIMESTAMP
    database_size = if (Test-Path "$PROJECT_ROOT\trademe_store.db") { (Get-Item "$PROJECT_ROOT\trademe_store.db").Length } else { 0 }
    media_size = if (Test-Path "$PROJECT_ROOT\data\media") { (Get-ChildItem "$PROJECT_ROOT\data\media" -Recurse | Measure-Object -Property Length -Sum).Sum } else { 0 }
    backup_size = (Get-ChildItem $BACKUP_DIR -Recurse | Measure-Object -Property Length -Sum).Sum
}

$manifest | ConvertTo-Json | Out-File "$BACKUP_DIR\manifest.json"

# Cleanup old backups (keep last 7 days)
Write-Host "`nCleaning up old backups..." -ForegroundColor Yellow
$cutoffDate = (Get-Date).AddDays(-7)
$oldBackups = Get-ChildItem $BACKUP_ROOT -Directory | Where-Object { $_.CreationTime -lt $cutoffDate }

if ($oldBackups) {
    foreach ($oldBackup in $oldBackups) {
        Write-Host "  Removing old backup: $($oldBackup.Name)" -ForegroundColor Gray
        Remove-Item $oldBackup.FullName -Recurse -Force
    }
    Write-Host "✓ Removed $($oldBackups.Count) old backup(s)" -ForegroundColor Green
} else {
    Write-Host "  No old backups to remove" -ForegroundColor Gray
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "BACKUP COMPLETED SUCCESSFULLY" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backup Location: $BACKUP_DIR" -ForegroundColor White
Write-Host "Backup Size: $([math]::Round($manifest.backup_size / 1MB, 2)) MB" -ForegroundColor White
Write-Host "Database Size: $([math]::Round($manifest.database_size / 1MB, 2)) MB" -ForegroundColor White
Write-Host "Media Size: $([math]::Round($manifest.media_size / 1MB, 2)) MB" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor Cyan

# Optional: Upload to cloud storage
# Uncomment and configure if you want to upload to OneDrive, Azure, etc.
# Write-Host "Uploading to cloud storage..." -ForegroundColor Yellow
# # Add your cloud upload logic here
# Write-Host "✓ Uploaded to cloud" -ForegroundColor Green
