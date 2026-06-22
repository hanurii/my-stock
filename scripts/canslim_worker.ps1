# canslim_worker.ps1 — 단일 워커 실행
# 사용법: .\scripts\canslim_worker.ps1 0       (10개 워커 중 0번)
#         .\scripts\canslim_worker.ps1 3 12    (12개 워커 중 3번)
#         .\scripts\canslim_worker.ps1 0 10 72 (캐시 TTL 72h)
param(
    [Parameter(Mandatory=$true)][int]$WorkerIndex,
    [int]$WorkersTotal = 10,
    [double]$CacheTtlHours = 72
)

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Set-Location $RepoRoot

Write-Host ""
Write-Host "🚀 CAN SLIM 워커 $WorkerIndex / $WorkersTotal 시작"
Write-Host "   작업 디렉토리: $RepoRoot"
Write-Host "   초기화(DART corp_code 다운로드, Naver 종목 리스트 등)에 30~60초 걸릴 수 있습니다..."
Write-Host ""

$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'
python -u scripts/screen_canslim.py --worker $WorkerIndex --workers-total $WorkersTotal --cache-ttl-hours $CacheTtlHours
