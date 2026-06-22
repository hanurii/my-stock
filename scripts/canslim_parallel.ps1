# canslim_parallel.ps1 — C 메인 풀스캔 병렬 실행 (make-hero 2단계)
#
# 흐름:
#   1) OHLCV 배치 행렬 증분 갱신 + 외인소진율(KIS) 갱신   — 단일 프로세스
#   2) N개 워커 병렬 Pass 1 (canslim_worker.ps1)          — 종목 슬라이스 분할
#   3) reduce 병합 + Pass 2 + can-slim-candidates.json 저장
#
# 사용법: .\scripts\canslim_parallel.ps1            (기본 10워커)
#         .\scripts\canslim_parallel.ps1 -Workers 8
#         .\scripts\canslim_parallel.ps1 -SkipForeign   (외인 갱신 생략, 기존 캐시 사용)
param(
    [int]$Workers = 10,
    [int]$MatrixWindow = 400,
    [double]$CacheTtlHours = 72,
    [switch]$SkipForeign
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Set-Location $RepoRoot
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONUTF8 = '1'

$sw = [System.Diagnostics.Stopwatch]::StartNew()

# ── 1) 행렬 + 외인 갱신 (단일 프로세스) ─────────────────────
Write-Host ""
Write-Host "📦 [1/4] OHLCV 행렬 + 외인 갱신 (단일 프로세스)"
if ($SkipForeign) {
    python -u scripts/canslim_lib/ohlcv_matrix.py --update --window $MatrixWindow
} else {
    python -u scripts/canslim_lib/ohlcv_matrix.py --update --window $MatrixWindow --foreign
}
if ($LASTEXITCODE -ne 0) { throw "ohlcv_matrix 갱신 실패 (exit $LASTEXITCODE)" }

# ── 1.5) 연간 재무 캐시 prewarm (단일 프로세스, Naver 동시성 회피) ──
Write-Host ""
Write-Host "🔥 [2/4] 연간 재무 캐시 prewarm (단일 프로세스)"
python -u scripts/screen_canslim.py --prewarm-annual
if ($LASTEXITCODE -ne 0) { Write-Host "⚠️  연간 prewarm 비정상 종료 — 워커가 개별 fetch (느려질 수 있음)" -ForegroundColor Yellow }

# ── 2) 워커 병렬 Pass 1 ─────────────────────────────────────
Write-Host ""
Write-Host "🚀 [3/4] $Workers 워커 병렬 Pass 1 시작"
$procs = @()
for ($i = 0; $i -lt $Workers; $i++) {
    $procs += Start-Process -FilePath "pwsh" `
        -ArgumentList "-NoProfile", "-File", "scripts/canslim_worker.ps1", "$i", "$Workers", "$CacheTtlHours" `
        -PassThru -NoNewWindow
}
$procs | Wait-Process
$failed = @($procs | Where-Object { $_.ExitCode -ne 0 })
if ($failed.Count -gt 0) {
    Write-Host "⚠️  워커 $($failed.Count)/$Workers 비정상 종료 — 가용한 워커 캐시만 병합" -ForegroundColor Yellow
}

# ── 3) reduce 병합 ──────────────────────────────────────────
Write-Host ""
Write-Host "🔀 [4/4] reduce 병합 + 저장"
python -u scripts/screen_canslim.py --reduce
if ($LASTEXITCODE -ne 0) { throw "reduce 실패 (exit $LASTEXITCODE)" }

$sw.Stop()
Write-Host ""
Write-Host ("✅ C 메인 병렬 완료 — 총 {0:N1}분" -f ($sw.Elapsed.TotalMinutes))
