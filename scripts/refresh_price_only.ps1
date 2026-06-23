# refresh_price_only.ps1 — 가격 레인 (make-hero 빠른 일일 갱신)
#
# 펀더멘털(DART/Naver) 캐시를 일절 건드리지 않고 "가격에서 파생되는 데이터"만 갱신한다.
# 무효화(canslim_incremental_check)·풀스캔(canslim_parallel)·트렌드 C·code33 을 호출하지
# 않으므로 .cache/canslim_stocks·dart_*·naver_annual 캐시를 구조적으로 못 건드린다.
#
# 흐름:
#   1) OHLCV 행렬 증분 갱신 (+ pdata 미공개 당일은 FDR 보충)  — 캐시 삭제 0건
#   2) 트렌드 템플레이트 1단계 (행렬 읽기)
#   3) L 점수 (트렌드 RS lookup, 네트워크·캐시 0)
#   4) KIS 통합시세로 C 게이트 종목 current_price·신고가대비 정확화
#
# 사용법: .\scripts\refresh_price_only.ps1
#         .\scripts\refresh_price_only.ps1 -SkipKis      (KIS 키 없거나 장중이면 4 생략)
#         .\scripts\refresh_price_only.ps1 -Window 400
#
# 커밋은 하지 않는다 (make-hero 스킬 7단계가 담당). 산출까지만.
param(
    [int]$Window = 400,
    [switch]$SkipKis
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Set-Location $RepoRoot
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONUTF8 = '1'

$sw = [System.Diagnostics.Stopwatch]::StartNew()

# ── 1) OHLCV 행렬 증분 + FDR 보충 (캐시 삭제 없음) ──────────────
Write-Host ""
Write-Host "📦 [1/4] OHLCV 행렬 증분 갱신 (+FDR 당일 보충)"
python -u scripts/canslim_lib/ohlcv_matrix.py --update --window $Window --fill-fdr
if ($LASTEXITCODE -ne 0) { throw "[1/4] ohlcv_matrix 갱신 실패 (exit $LASTEXITCODE)" }

# ── 2) 트렌드 템플레이트 1단계 (행렬 읽기) ─────────────────────
Write-Host ""
Write-Host "🎯 [2/4] 트렌드 템플레이트 1단계"
python -u scripts/screen_trend_template.py --save
if ($LASTEXITCODE -ne 0) { throw "[2/4] screen_trend_template 실패 (exit $LASTEXITCODE)" }

# ── 3) L 점수 (트렌드 RS lookup) ───────────────────────────────
Write-Host ""
Write-Host "🏅 [3/4] L 점수 갱신"
python -u scripts/fetch_l_rs.py
if ($LASTEXITCODE -ne 0) { throw "[3/4] fetch_l_rs 실패 (exit $LASTEXITCODE)" }

# ── 4) KIS 통합시세로 현재가·신고가대비 정확화 ─────────────────
if ($SkipKis) {
    Write-Host ""
    Write-Host "⏭  [4/4] KIS 통합시세 생략 (-SkipKis) — KRX 종가 유지"
} else {
    Write-Host ""
    Write-Host "💎 [4/4] KIS 통합시세로 현재가 정확화"
    python -u scripts/refine_with_kis_nxt.py
    if ($LASTEXITCODE -ne 0) { throw "[4/4] refine_with_kis_nxt 실패 (exit $LASTEXITCODE)" }
}

$sw.Stop()
Write-Host ""
Write-Host ("✅ 가격 레인 완료 — 총 {0:N1}분 (펀더 캐시 무접촉)" -f ($sw.Elapsed.TotalMinutes))
