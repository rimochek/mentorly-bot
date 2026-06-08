# Pre-deploy checks for mentorly-bot
# Usage: .\scripts\pre_deploy.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "==> Building bot image..."
docker compose build bot

Write-Host "==> Running unit tests..."
docker compose run --rm bot pytest -q

Write-Host "==> Starting services..."
docker compose up -d

Write-Host "==> Waiting for bot startup..."
Start-Sleep -Seconds 8

Write-Host "==> Bot logs (last 30 lines):"
docker compose logs bot --tail 30

Write-Host ""
Write-Host "Manual smoke (2 Telegram accounts):"
Write-Host "  A) Tutor: register IELTS profile, check stats"
Write-Host "  B) Student: search IELTS, browse, contact, repeat contact (no dup)"
Write-Host "  C) No-match search, support ticket, disable tutor profile"
Write-Host ""
Write-Host "Pre-deploy automated checks passed. Complete manual smoke before prod push."
