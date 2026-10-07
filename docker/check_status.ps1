# STLC Manager - Service Status Check
Write-Host "===============================" -ForegroundColor Cyan
Write-Host " STLC Manager Service Check    " -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""

# Backend Check
Write-Host "Backend Status..." -ForegroundColor Yellow
try {
    $null = Invoke-WebRequest -Uri "http://localhost:8100/docs" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  OK - Backend running (port 8000)" -ForegroundColor Green
} catch {
    Write-Host "  FAIL - Backend not running" -ForegroundColor Red
}

# Frontend Check
Write-Host "Frontend Status..." -ForegroundColor Yellow
try {
    $null = Invoke-WebRequest -Uri "http://localhost:5175" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  OK - Frontend running (port 5173)" -ForegroundColor Green
} catch {
    Write-Host "  FAIL - Frontend not running" -ForegroundColor Red
}

# LM Studio Check
Write-Host "LM Studio Status..." -ForegroundColor Yellow
try {
    $null = Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  OK - LM Studio running (port 1234)" -ForegroundColor Green
} catch {
    Write-Host "  FAIL - LM Studio not running" -ForegroundColor Red
}

# MongoDB Check
Write-Host "MongoDB Status..." -ForegroundColor Yellow
$mongo = Get-Process -Name mongod -ErrorAction SilentlyContinue
if ($mongo) {
    Write-Host "  OK - MongoDB running" -ForegroundColor Green
} else {
    Write-Host "  WARN - MongoDB process not found" -ForegroundColor Yellow
}

# Docker Check
Write-Host "Docker Status..." -ForegroundColor Yellow
try {
    $null = docker ps 2>$null
    Write-Host "  OK - Docker Desktop running" -ForegroundColor Green
} catch {
    Write-Host "  FAIL - Docker Desktop not running" -ForegroundColor Red
}

Write-Host ""
Write-Host "===============================" -ForegroundColor Cyan
Write-Host " Next Steps                    " -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""
Write-Host "UI: http://localhost:5175" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8100/docs" -ForegroundColor Cyan
Write-Host "Read UI_TEST_GUIDE.md for detailed instructions" -ForegroundColor Yellow
Write-Host ""
