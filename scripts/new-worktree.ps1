# new-worktree.ps1 — 새 git worktree + .env 복사 + .cache junction(기존 캐시 공유)
#
# 다른 세션과 git 충돌을 막기 위해 작업 스트림마다 독립 worktree를 만든다.
# .env 는 복사, .cache 는 메인(정규) worktree로 junction 링크 → 기존 캐시를
# 새로 만들지 않고 읽기 공유한다.
#
# 사용:
#   pwsh scripts/new-worktree.ps1 <이름> [브랜치]
#     <이름>  : 폴더 접미사 → ../my-stock-<이름>
#     [브랜치]: 체크아웃할 *기존* 브랜치. 생략 시 feat/<이름> 새 브랜치를 master에서 생성.
#
# 예:
#   pwsh scripts/new-worktree.ps1 power feat/find-power-play   # 기존 브랜치
#   pwsh scripts/new-worktree.ps1 flag                          # feat/flag 새로 생성(master 기준)
#
# 주의: 캐시는 공유되므로 update-data(시세 갱신)는 한 곳에서만 돌릴 것.
#       삭제는 반드시 remove-worktree.ps1 로 (junction 안전 해제).

param(
    [Parameter(Mandatory = $true)][string]$Name,
    [string]$Branch
)
$ErrorActionPreference = "Stop"

# 정규(메인) worktree = `git worktree list` 첫 항목
$mainWt = ((git worktree list --porcelain) -split "`n" `
    | Where-Object { $_ -like 'worktree *' } | Select-Object -First 1)
if (-not $mainWt) { throw "git 저장소가 아니거나 worktree를 찾을 수 없음" }
$mainWt = $mainWt.Substring(9).Trim()
$parent = Split-Path -Parent $mainWt
$wt = Join-Path $parent "my-stock-$Name"

if (Test-Path $wt) { throw "이미 존재함: $wt" }

# 1) worktree 생성
if ($Branch) {
    git worktree add $wt $Branch
} else {
    git worktree add $wt -b "feat/$Name" master
}
if ($LASTEXITCODE -ne 0) { throw "git worktree add 실패 (exit $LASTEXITCODE)" }

# 2) .env 복사
$srcEnv = Join-Path $mainWt ".env"
if (Test-Path $srcEnv) {
    Copy-Item $srcEnv (Join-Path $wt ".env")
    Write-Host "  .env 복사됨"
} else {
    Write-Host "  WARN: 메인에 .env 없음 — 건너뜀"
}

# 3) .cache junction (기존 캐시 읽기 공유, 새로 안 만듦)
$link = Join-Path $wt ".cache"
$target = Join-Path $mainWt ".cache"
if (Test-Path $target) {
    New-Item -ItemType Junction -Path $link -Target $target | Out-Null
    Write-Host "  .cache junction -> $target"
} else {
    Write-Host "  WARN: 메인에 .cache 없음 — junction 건너뜀(필요 시 update-data)"
}

Write-Host "OK worktree 준비됨: $wt"
Write-Host "   삭제: pwsh scripts/remove-worktree.ps1 $Name"
