# canslim_reduce.ps1 — 모든 워커 캐시 병합 + 최종 JSON 저장
# 사용법: .\scripts\canslim_reduce.ps1

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Set-Location $RepoRoot

Write-Host ""
Write-Host "🔀 CAN SLIM Reduce 시작"
Write-Host "   작업 디렉토리: $RepoRoot"
Write-Host ""

$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'
python -u scripts/screen_canslim.py --reduce
