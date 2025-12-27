# RetailOS Windows Bootstrap Script
# Usage: ./bootstrap.ps1

Write-Host "✈️ RetailOS Production Bootstrap" -ForegroundColor Green

# 1. Check Docker
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker not found. Please install Docker Desktop for Windows." -ForegroundColor Red
    exit 1
}

# 2. Check .env
if (-not (Test-Path ".env")) {
    Write-Host "⚠️ No .env file found. Creating from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "Please edit .env with your real API keys before continuing." -ForegroundColor Cyan
    exit 0
}

# 3. Create Data Directory
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Force -Path "data" | Out-Null
    Write-Host "✅ Created ./data directory for keys and database." -ForegroundColor Green
}

# 4. Build and Run
Write-Host "🚀 Building and Starting RetailOS..." -ForegroundColor Green
docker-compose up -d --build

# 5. Check Status
Start-Sleep -Seconds 5
if (docker ps | Select-String "retail_os_cockpit") {
    Write-Host "✅ RetailOS is RUNNING at http://localhost:8501" -ForegroundColor Green
    Start-Process "http://localhost:8501"
} else {
    Write-Host "❌ Failed to start. Check logs with 'docker-compose logs'." -ForegroundColor Red
}
