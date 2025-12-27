# Windows Task Scheduler Setup for RetailOS
# Run this script as Administrator to schedule all automation tasks

Write-Host "🔧 RetailOS - Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Get project root
$ProjectRoot = (Get-Location).Path
$PythonExe = (Get-Command python).Source

Write-Host "Project Root: $ProjectRoot" -ForegroundColor Yellow
Write-Host "Python: $PythonExe" -ForegroundColor Yellow
Write-Host ""

# Function to create scheduled task
function Create-RetailOSTask {
    param(
        [string]$TaskName,
        [string]$ScriptPath,
        [string]$Schedule,  # HOURLY, DAILY, WEEKLY
        [int]$Interval = 1,
        [string]$StartTime = "09:00"
    )
    
    Write-Host "Creating task: $TaskName" -ForegroundColor Green
    
    # Remove existing task if it exists
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "  → Removed existing task" -ForegroundColor Gray
    }
    
    # Create action
    $action = New-ScheduledTaskAction -Execute $PythonExe -Argument $ScriptPath -WorkingDirectory $ProjectRoot
    
    # Create trigger based on schedule
    switch ($Schedule) {
        "HOURLY" {
            $trigger = New-ScheduledTaskTrigger -Once -At $StartTime -RepetitionInterval (New-TimeSpan -Hours $Interval) -RepetitionDuration ([TimeSpan]::MaxValue)
        }
        "DAILY" {
            $trigger = New-ScheduledTaskTrigger -Daily -At $StartTime
        }
        "WEEKLY" {
            $trigger = New-ScheduledTaskTrigger -Weekly -At $StartTime -DaysOfWeek Monday
        }
    }
    
    # Create settings
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    
    # Register task
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "RetailOS Automation" | Out-Null
    
    Write-Host "  ✅ Task created successfully" -ForegroundColor Green
}

Write-Host "📅 Creating Scheduled Tasks..." -ForegroundColor Cyan
Write-Host ""

# 1. Scraper - Every 4 hours
Create-RetailOSTask -TaskName "RetailOS-Scraper" `
    -ScriptPath "scripts/run_unified_pipeline.py --limit 200" `
    -Schedule "HOURLY" -Interval 4 -StartTime "06:00"

# 2. Order Sync - Every 1 hour
Create-RetailOSTask -TaskName "RetailOS-OrderSync" `
    -ScriptPath "scripts/sync_sold_items.py" `
    -Schedule "HOURLY" -Interval 1 -StartTime "08:00"

# 3. Lifecycle Analysis - Daily at 2 AM
Create-RetailOSTask -TaskName "RetailOS-Lifecycle" `
    -ScriptPath "scripts/run_lifecycle.py" `
    -Schedule "DAILY" -StartTime "02:00"

# 4. Enrichment Daemon - Every 2 hours
Create-RetailOSTask -TaskName "RetailOS-Enrichment" `
    -ScriptPath "scripts/run_enrichment_daemon.py --batch-size 10" `
    -Schedule "HOURLY" -Interval 2 -StartTime "07:00"

# 5. Health Check - Daily at 3 AM
Create-RetailOSTask -TaskName "RetailOS-HealthCheck" `
    -ScriptPath "scripts/healthcheck.py" `
    -Schedule "DAILY" -StartTime "03:00"

# 6. Database Backup - Daily at 1 AM
Create-RetailOSTask -TaskName "RetailOS-Backup" `
    -ScriptPath "scripts/backup_db.py" `
    -Schedule "DAILY" -StartTime "01:00"

# 7. Validation - Daily at 4 AM
Create-RetailOSTask -TaskName "RetailOS-Validation" `
    -ScriptPath "scripts/validator.py" `
    -Schedule "DAILY" -StartTime "04:00"

# 8. Command Worker - Continuous (every 5 minutes)
Create-RetailOSTask -TaskName "RetailOS-CommandWorker" `
    -ScriptPath "retail_os/trademe/worker.py" `
    -Schedule "HOURLY" -Interval 1 -StartTime "00:05"

Write-Host ""
Write-Host "✅ All tasks created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Task Summary:" -ForegroundColor Cyan
Write-Host "  1. Scraper: Every 4 hours (starting 6 AM)" -ForegroundColor White
Write-Host "  2. Order Sync: Every hour (starting 8 AM)" -ForegroundColor White
Write-Host "  3. Lifecycle Analysis: Daily at 2 AM" -ForegroundColor White
Write-Host "  4. Enrichment: Every 2 hours (starting 7 AM)" -ForegroundColor White
Write-Host "  5. Health Check: Daily at 3 AM" -ForegroundColor White
Write-Host "  6. Database Backup: Daily at 1 AM" -ForegroundColor White
Write-Host "  7. Validation: Daily at 4 AM" -ForegroundColor White
Write-Host "  8. Command Worker: Every hour" -ForegroundColor White
Write-Host ""
Write-Host "🔍 View tasks: Get-ScheduledTask | Where-Object {$_.TaskName -like 'RetailOS-*'}" -ForegroundColor Yellow
Write-Host "🗑️  Remove all: Get-ScheduledTask | Where-Object {$_.TaskName -like 'RetailOS-*'} | Unregister-ScheduledTask -Confirm:$false" -ForegroundColor Yellow
Write-Host ""
Write-Host "✅ Setup Complete!" -ForegroundColor Green
