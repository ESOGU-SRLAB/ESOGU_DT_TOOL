# STLC Manager - Hızlı Başlatma Scripti
# Tüm servisleri kontrol eder ve gerekirse başlatır

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  STLC Manager Servis Kontrolü  " -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 1. Backend Kontrolü
Write-Host "1️⃣  Backend kontrolü..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -Method Get -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ Backend çalışıyor (localhost:8000)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Backend çalışmıyor!" -ForegroundColor Red
    Write-Host "   ℹ️  Başlatmak için:" -ForegroundColor Yellow
    Write-Host "      cd <STLC-Manager>\backend" -ForegroundColor Gray
    Write-Host "      python -m uvicorn app:app --reload --host localhost --port 8000" -ForegroundColor Gray
}
Write-Host ""

# 2. Frontend Kontrolü
Write-Host "2️⃣  Frontend kontrolü..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5173" -Method Get -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ Frontend çalışıyor (localhost:5173)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Frontend çalışmıyor!" -ForegroundColor Red
    Write-Host "   ℹ️  Başlatmak için:" -ForegroundColor Yellow
    Write-Host "      cd <STLC-Manager>\frontend" -ForegroundColor Gray
    Write-Host "      npm run dev" -ForegroundColor Gray
}
Write-Host ""

# 3. LM Studio Kontrolü
Write-Host "3️⃣  LM Studio kontrolü..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -Method Get -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ LM Studio çalışıyor" -ForegroundColor Green
} catch {
    Write-Host "   ❌ LM Studio çalışmıyor!" -ForegroundColor Red
    Write-Host "   ℹ️  LM Studio uygulamasını manuel başlatın" -ForegroundColor Yellow
}
Write-Host ""

# 4. MongoDB Kontrolü
Write-Host "4️⃣  MongoDB kontrolü..." -ForegroundColor Yellow
$mongoProcess = Get-Process -Name mongod -ErrorAction SilentlyContinue
if ($mongoProcess) {
    Write-Host "   ✅ MongoDB çalışıyor" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  MongoDB process bulunamadı" -ForegroundColor Yellow
}
Write-Host ""

# 5. Docker Desktop Kontrolü
Write-Host "5️⃣  Docker Desktop kontrolü..." -ForegroundColor Yellow
try {
    $dockerVersion = docker version 2>$null
    if ($dockerVersion) {
        Write-Host "   ✅ Docker Desktop çalışıyor" -ForegroundColor Green
    }
} catch {
    Write-Host "   ❌ Docker Desktop çalışmıyor!" -ForegroundColor Red
}
Write-Host ""

# Özet
Write-Host "================================" -ForegroundColor Cyan
Write-Host "  Sonraki Adımlar               " -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Detaylı UI test rehberi için:" -ForegroundColor Yellow
Write-Host "   UI_TEST_GUIDE.md dosyasını okuyun" -ForegroundColor Gray
Write-Host ""
Write-Host "🌐 UI'ya erişim:" -ForegroundColor Yellow
Write-Host "   http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "📚 Backend API Docs:" -ForegroundColor Yellow
Write-Host "   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

