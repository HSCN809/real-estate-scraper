# HepsiEmlak Gece Kazıma Başlatıcı Script
# Go Proxy'yi arka planda başlatır ve kazıma motorunu çalıştırır.

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  HepsiEmlak Gece Kazima Baslatici" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$proxyExe = Join-Path $scriptDir "Backend\go\proxy.exe"

$env:PROXY_API_KEY = "test-secret"

# 1. Proxy Sağlık Kontrolü
$proxyRunning = $false
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8080/" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($resp.status -eq "ok") {
        $proxyRunning = $true
        Write-Host "[OK] Go Proxy zaten 8080 portunda calisiyor." -ForegroundColor Green
    }
} catch {}

$proxyProcess = $null
if (-not $proxyRunning) {
    Write-Host "[*] Go Proxy arka planda baslatiliyor..." -ForegroundColor Yellow
    $proxyProcess = Start-Process -FilePath $proxyExe -PassThru -WindowStyle Hidden
    $proxyProcess.PriorityClass = 'BelowNormal'
    Start-Sleep -Seconds 2
}

try {
    Write-Host "[*] Gece kazima motoru baslatiliyor..." -ForegroundColor Green
    Write-Host "[*] Durdurmak icin istedigin an Ctrl+C yapabilirsin (Checkpoint otomatik kaydedilir)." -ForegroundColor Gray
    
    python "$scriptDir\run_overnight_scraper.py" --type kiralik --pages 15 --delay-min 4.0 --delay-max 7.0
} finally {
    if ($proxyProcess) {
        Write-Host "[*] Go Proxy kapatiliyor..." -ForegroundColor Yellow
        Stop-Process -Id $proxyProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
