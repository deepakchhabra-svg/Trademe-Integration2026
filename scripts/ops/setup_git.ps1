# Git Setup Helper Script
# This script will help you install and configure Git for the Trade Me Integration project

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git Setup Helper for Trade Me Integration" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if Git is already installed
Write-Host "Checking for Git installation..." -ForegroundColor Yellow
$gitInstalled = $false

try {
    $gitVersion = & git --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $gitInstalled = $true
        Write-Host "✓ Git is already installed: $gitVersion" -ForegroundColor Green
    }
}
catch {
    # Git not in PATH
}

# Check common installation locations
$commonPaths = @(
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files (x86)\Git\cmd\git.exe",
    "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe"
)

foreach ($path in $commonPaths) {
    if (Test-Path $path) {
        Write-Host "⚠ Git found at: $path" -ForegroundColor Yellow
        Write-Host "  But it's not in your PATH!" -ForegroundColor Yellow
        
        $addToPath = Read-Host "Would you like to add Git to your PATH? (y/n)"
        if ($addToPath -eq 'y') {
            $gitDir = Split-Path $path
            $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
            if ($currentPath -notlike "*$gitDir*") {
                [Environment]::SetEnvironmentVariable("Path", "$currentPath;$gitDir", "User")
                Write-Host "✓ Added to PATH. Please restart PowerShell." -ForegroundColor Green
                $gitInstalled = $true
            }
        }
        break
    }
}

if (-not $gitInstalled) {
    Write-Host "`n❌ Git is not installed on this system." -ForegroundColor Red
    Write-Host "`nOptions:" -ForegroundColor Cyan
    Write-Host "1. Download and install Git for Windows manually" -ForegroundColor White
    Write-Host "   URL: https://git-scm.com/download/win" -ForegroundColor Gray
    Write-Host "`n2. Install using winget (Windows Package Manager)" -ForegroundColor White
    Write-Host "   Command: winget install --id Git.Git -e --source winget" -ForegroundColor Gray
    Write-Host "`n3. Install using Chocolatey (if installed)" -ForegroundColor White
    Write-Host "   Command: choco install git" -ForegroundColor Gray
    
    $choice = Read-Host "`nWould you like to try installing with winget? (y/n)"
    
    if ($choice -eq 'y') {
        Write-Host "`nAttempting to install Git using winget..." -ForegroundColor Yellow
        try {
            winget install --id Git.Git -e --source winget
            Write-Host "✓ Git installation completed!" -ForegroundColor Green
            Write-Host "⚠ Please restart PowerShell and run this script again." -ForegroundColor Yellow
            exit 0
        }
        catch {
            Write-Host "❌ winget installation failed. Please install manually." -ForegroundColor Red
            Write-Host "Download from: https://git-scm.com/download/win" -ForegroundColor Cyan
            exit 1
        }
    }
    else {
        Write-Host "`nPlease install Git manually:" -ForegroundColor Yellow
        Write-Host "1. Visit: https://git-scm.com/download/win" -ForegroundColor White
        Write-Host "2. Download the installer" -ForegroundColor White
        Write-Host "3. Run the installer (use default settings)" -ForegroundColor White
        Write-Host "4. Restart PowerShell" -ForegroundColor White
        Write-Host "5. Run this script again" -ForegroundColor White
        exit 1
    }
}

# Configure Git
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Git Configuration" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$currentName = git config --global user.name 2>$null
$currentEmail = git config --global user.email 2>$null

if ($currentName) {
    Write-Host "Current Git name: $currentName" -ForegroundColor Gray
    $changeName = Read-Host "Change name? (y/n)"
    if ($changeName -ne 'y') {
        $userName = $currentName
    }
}

if (-not $userName) {
    $userName = Read-Host "Enter your name (e.g., 'Deepak Chhabra')"
    git config --global user.name "$userName"
    Write-Host "✓ Name set to: $userName" -ForegroundColor Green
}

if ($currentEmail) {
    Write-Host "Current Git email: $currentEmail" -ForegroundColor Gray
    $changeEmail = Read-Host "Change email? (y/n)"
    if ($changeEmail -ne 'y') {
        $userEmail = $currentEmail
    }
}

if (-not $userEmail) {
    $userEmail = Read-Host "Enter your email (e.g., 'deepak.chhabra@datacom.co.nz')"
    git config --global user.email "$userEmail"
    Write-Host "✓ Email set to: $userEmail" -ForegroundColor Green
}

# Configure credential helper
Write-Host "`nConfiguring credential helper..." -ForegroundColor Yellow
git config --global credential.helper wincred
Write-Host "✓ Credential helper configured" -ForegroundColor Green

# Configure line endings
Write-Host "Configuring line endings for Windows..." -ForegroundColor Yellow
git config --global core.autocrlf true
Write-Host "✓ Line endings configured" -ForegroundColor Green

# Initialize repository
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Repository Initialization" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$projectDir = "c:\Users\deepak.chhabra\OneDrive - Datacom\Documents\Trademe Integration"
Set-Location $projectDir

if (Test-Path ".git") {
    Write-Host "✓ Git repository already initialized" -ForegroundColor Green
}
else {
    Write-Host "Initializing Git repository..." -ForegroundColor Yellow
    git init
    Write-Host "✓ Repository initialized" -ForegroundColor Green
}

# Check .gitignore
if (Test-Path ".gitignore") {
    Write-Host "✓ .gitignore file exists" -ForegroundColor Green
}
else {
    Write-Host "⚠ .gitignore file not found (should have been created)" -ForegroundColor Yellow
}

# Show status
Write-Host "`nCurrent repository status:" -ForegroundColor Cyan
git status --short

# Offer to make initial commit
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Initial Commit" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$makeCommit = Read-Host "Would you like to make an initial commit? (y/n)"

if ($makeCommit -eq 'y') {
    Write-Host "`nStaging files..." -ForegroundColor Yellow
    git add .
    
    Write-Host "Files to be committed:" -ForegroundColor Cyan
    git status --short
    
    $confirmCommit = Read-Host "`nProceed with commit? (y/n)"
    
    if ($confirmCommit -eq 'y') {
        git commit -m "Initial commit - Trade Me Integration project"
        Write-Host "✓ Initial commit created!" -ForegroundColor Green
        
        # Show commit
        git log -1 --oneline
    }
}

# Remote repository setup
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Remote Repository Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$currentRemote = git remote get-url origin 2>$null

if ($currentRemote) {
    Write-Host "✓ Remote 'origin' already configured: $currentRemote" -ForegroundColor Green
}
else {
    Write-Host "No remote repository configured yet." -ForegroundColor Yellow
    Write-Host "`nOptions:" -ForegroundColor Cyan
    Write-Host "1. Azure DevOps (recommended for Datacom)" -ForegroundColor White
    Write-Host "2. GitHub" -ForegroundColor White
    Write-Host "3. GitLab" -ForegroundColor White
    Write-Host "4. Skip for now" -ForegroundColor White
    
    $remoteChoice = Read-Host "`nChoose option (1-4)"
    
    if ($remoteChoice -ne '4') {
        $remoteUrl = Read-Host "Enter the remote repository URL"
        
        if ($remoteUrl) {
            git remote add origin $remoteUrl
            Write-Host "✓ Remote 'origin' added: $remoteUrl" -ForegroundColor Green
            
            $pushNow = Read-Host "`nPush to remote now? (y/n)"
            if ($pushNow -eq 'y') {
                Write-Host "Pushing to remote..." -ForegroundColor Yellow
                git branch -M main
                git push -u origin main
                Write-Host "✓ Pushed to remote!" -ForegroundColor Green
            }
        }
    }
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Git Configuration:" -ForegroundColor Cyan
Write-Host "  Name: $(git config --global user.name)" -ForegroundColor White
Write-Host "  Email: $(git config --global user.email)" -ForegroundColor White

if ($currentRemote -or $remoteUrl) {
    Write-Host "`nRemote Repository:" -ForegroundColor Cyan
    Write-Host "  $(git remote get-url origin 2>$null)" -ForegroundColor White
}

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "1. Review VERSION_CONTROL.md for Git workflow" -ForegroundColor White
Write-Host "2. Make commits regularly: git add . && git commit -m 'message'" -ForegroundColor White
Write-Host "3. Push to remote: git push" -ForegroundColor White
Write-Host "4. Create feature branches: git checkout -b feature/name" -ForegroundColor White

Write-Host "`nUseful Commands:" -ForegroundColor Cyan
Write-Host "  git status          - Check current status" -ForegroundColor Gray
Write-Host "  git add .           - Stage all changes" -ForegroundColor Gray
Write-Host "  git commit -m 'msg' - Commit changes" -ForegroundColor Gray
Write-Host "  git push            - Push to remote" -ForegroundColor Gray
Write-Host "  git log             - View history" -ForegroundColor Gray

Write-Host "`n✅ You're ready to use Git!" -ForegroundColor Green
