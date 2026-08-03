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

# claude 출력은 UTF-8 — PS 5.1 기본(CP949)으로 받으면 로그가 깨진다
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

# 헤드리스 지시문: -p 프로세스는 대답이 끝나는 즉시 종료되므로, 백그라운드에
# 작업을 걸어둔 채 턴을 끝내면 작업이 전부 죽는다(2026-08-03 실사고 — 2분 만에
# "성공" 종료, 실제로는 아무것도 안 돎). 커밋까지 턴 안에서 끝내라고 못박는다.
$prompt = "/sepa 헤드리스 실행 주의: 이 프로세스는 네 대답이 끝나는 즉시 종료된다. " +
    "백그라운드 작업이 남아 있는 채로 턴을 끝내면 작업이 전부 죽는다. " +
    "백그라운드로 띄운 작업은 반드시 이 턴 안에서 완료를 기다려 취합하고, " +
    "통합 요약과 결과 파일 커밋·push·master 반영까지 전부 마친 뒤에만 턴을 끝낼 것. " +
    "'끝나면 알림받고 보고하겠다'는 식의 예고로 턴을 끝내는 것은 금지."

$startTime = Get-Date
& $claude.Source -p $prompt --dangerously-skip-permissions 2>&1 |
    Out-File -FilePath $logFile -Append -Encoding utf8
$code = $LASTEXITCODE

# 성공 판정: exit 0 만 믿지 않는다 — 결과 파일이 실행 시작 이후 실제로
# 갱신됐는지 확인(2단계 추세 관문이 항상 쓰는 파일이라 파이프라인이 실제로
# 돌았는지의 최소 증거). exit 0 인데 미갱신이면 거짓 성공 → 마커 미기록.
$probe = Join-Path $repo "public\data\sepa-trend-candidates.json"
$updated = (Test-Path $probe) -and ((Get-Item $probe).LastWriteTime -gt $startTime)

if ($code -eq 0 -and $updated) {
    New-Item -ItemType File -Path $marker -Force | Out-Null
    Write-Log "SEPA 파이프라인 성공 종료 (결과 파일 갱신 확인됨)"
} elseif ($code -eq 0) {
    Write-Log "거짓 성공 감지: exit 0 이지만 결과 파일이 갱신되지 않음 — 마커 미기록. 헤드리스 Claude 가 일을 안 하고 종료했을 가능성(로그의 Claude 출력 확인)"
    $code = 1
} else {
    Write-Log "SEPA 파이프라인 실패 (exit=$code) — 로그 확인 필요. 마커 미기록(재부팅 시 재시도됨)"
}
exit $code
