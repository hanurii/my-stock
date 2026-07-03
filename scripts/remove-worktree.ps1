# remove-worktree.ps1 — git worktree 안전 삭제 (.cache junction 먼저 해제)
#
# .cache 는 junction(링크)이라 그냥 지우면 링크를 따라가 *원본 캐시*까지
# 삭제될 위험이 있다. 이 스크립트는 junction 링크만 먼저 끊고(원본 보존),
# 그 다음 worktree 를 제거한다. .cache 가 링크가 아니면(=실제 폴더면)
# 안전을 위해 중단한다.
#
# 사용:
#   pwsh scripts/remove-worktree.ps1 <이름> [-Force]
#     <이름>  : ../my-stock-<이름>
#     -Force  : worktree에 미커밋 변경이 있어도 제거(git worktree remove --force)

param(
    [Parameter(Mandatory = $true)][string]$Name,
    [switch]$Force
)
$ErrorActionPreference = "Stop"

$mainWt = ((git worktree list --porcelain) -split "`n" `
    | Where-Object { $_ -like 'worktree *' } | Select-Object -First 1)
if (-not $mainWt) { throw "git 저장소가 아니거나 worktree를 찾을 수 없음" }
$mainWt = $mainWt.Substring(9).Trim()
$parent = Split-Path -Parent $mainWt
$wt = Join-Path $parent "my-stock-$Name"

if (-not (Test-Path $wt)) { throw "없음: $wt" }
if ((Resolve-Path $wt).Path -eq (Resolve-Path $mainWt).Path) {
    throw "메인 worktree는 삭제할 수 없음: $wt"
}

# 1) .cache junction 먼저 해제 (원본 캐시 보존)
$cache = Join-Path $wt ".cache"
if (Test-Path $cache) {
    $li = Get-Item $cache -Force
    if ($li.LinkType) {
        cmd /c rmdir "$cache"     # junction 링크만 제거, 대상(원본 캐시) 보존
        if ($LASTEXITCODE -ne 0) { throw ".cache junction 제거 실패" }
        Write-Host "  .cache junction 해제(원본 캐시 보존)"
    } else {
        throw ".cache 가 junction(링크)이 아니라 실제 폴더임 — 원본 캐시 삭제 방지 위해 중단. 수동 확인 요."
    }
}

# 2) worktree 제거
if ($Force) { git worktree remove --force $wt } else { git worktree remove $wt }
if ($LASTEXITCODE -ne 0) {
    throw "git worktree remove 실패(미커밋 변경이 있으면 -Force). junction은 이미 해제됨."
}
Write-Host "OK worktree 제거됨: $wt"
