<#
SEPA 파이프라인 야간 자동 실행 래퍼 — Windows 작업 스케줄러용.

동작: 헤드리스 Claude 가 /sepa 스킬을 실행한다(수동 실행과 동일한 오케스트레이션 —
실패 시 커밋 중단, 통합 요약, master 반영, 캐시 백업까지).

스케줄: 작업 스케줄러 "SEPA-Daily" 작업이 평일 20:00 에 이 스크립트를 부른다.
20:00 에 컴퓨터가 꺼져 있었으면 다음 부팅/로그인 때 실행된다(StartWhenAvailable).
그 경우에도 아래 가드가 "돌려도 되는 시각인지" 다시 판단한다.

가드(순서대로):
  1. 주말 스킵 — 새 거래일이 없다.
  2. 20:00 이전 스킵 — 장중 실행하면 FDR 이 미완성 당일봉을 캐시에 넣을 수 있다.
     (예: 금요일 20:00 을 놓치고 월요일 아침에 부팅 → 이 가드가 막고, 금요일
     데이터는 월요일 20:00 정규 실행이 증분으로 따라잡는다. 손실 없음.)
  3. 오늘 이미 성공했으면 스킵 — 중복 실행 방지(마커 파일).

로그: %USERPROFILE%\sepa-logs\sepa-YYYYMMDD.log (아침에 요약 확인용)
마커: %USERPROFILE%\sepa-logs\done-YYYYMMDD  (성공 시에만 기록)

수동 테스트:
  powershell -File scripts\run_sepa_daily.ps1 -DryRun -Force   # 판단만, 실행 안 함
  powershell -File scripts\run_sepa_daily.ps1 -Force            # 가드 무시 즉시 실행

작업 등록/해제(1회):
  등록은 저장소 문서 참조(Register-ScheduledTask), 해제는
  Unregister-ScheduledTask -TaskName "SEPA-Daily"
#>
param(
    [switch]$Force,     # 가드 전부 무시(수동 테스트용)
    [switch]$DryRun     # 실행 판단까지만 하고 claude 는 부르지 않음
)

$ErrorActionPreference = "Continue"
$repo = Split-Path $PSScriptRoot -Parent
$logDir = Join-Path $env:USERPROFILE "sepa-logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$today = Get-Date -Format "yyyyMMdd"
$logFile = Join-Path $logDir "sepa-$today.log"
$marker = Join-Path $logDir "done-$today"

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    $line | Out-File -FilePath $logFile -Append -Encoding utf8
    Write-Host $line
}

# ── 가드 ─────────────────────────────────────────────────────
if (-not $Force) {
    $now = Get-Date
    if ($now.DayOfWeek -in @([DayOfWeek]::Saturday, [DayOfWeek]::Sunday)) {
        Write-Log "스킵: 주말($($now.DayOfWeek)) — 새 거래일 없음"
        exit 0
    }
    if ($now.Hour -lt 20) {
        Write-Log "스킵: 20시 이전($($now.ToString('HH:mm'))) — 장중 실행 방지(미완성 당일봉 오염). 오늘 20시에 정규 실행됨"
        exit 0
    }
    if (Test-Path $marker) {
        Write-Log "스킵: 오늘 이미 성공 실행됨(마커 존재)"
        exit 0
    }
}

# ── claude CLI 확인 ──────────────────────────────────────────
$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
    Write-Log "오류: claude CLI 를 찾을 수 없음 (PATH 확인)"
    exit 1
}

if ($DryRun) {
    Write-Log "DryRun: 가드 통과 — 실제라면 여기서 'claude -p /sepa' 실행 (repo=$repo)"
    exit 0
}

# ── 실행 ─────────────────────────────────────────────────────
Write-Log "SEPA 파이프라인 시작 (헤드리스 /sepa)"
Set-Location $repo
& $claude.Source -p "/sepa" --dangerously-skip-permissions 2>&1 |
    Out-File -FilePath $logFile -Append -Encoding utf8
$code = $LASTEXITCODE

if ($code -eq 0) {
    New-Item -ItemType File -Path $marker -Force | Out-Null
    Write-Log "SEPA 파이프라인 성공 종료"
} else {
    Write-Log "SEPA 파이프라인 실패 (exit=$code) — 로그 확인 필요. 마커 미기록(재부팅 시 재시도됨)"
}
exit $code
