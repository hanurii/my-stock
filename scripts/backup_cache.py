#!/usr/bin/env python
"""`.cache` 스냅샷 백업 — 로컬 + GitHub 릴리스 자산(오프사이트·버전관리).

캐시(OHLCV 시계열·pdata·DART/Naver 펀더)는 원본에서 재수집은 되나 콜드 재빌드가
느리고 API 한도가 걸리므로, "빠른 복구용" zip 스냅샷을 로컬과 GitHub에 둔다.
zip 은 GitHub 릴리스 **자산**으로 올려 git 트리·히스토리를 비대하게 만들지 않는다.

실행: python scripts/backup_cache.py
권장: 매일 update-data(시세 갱신) 직후 자동 실행(작업 스케줄러/파이프라인 훅).
"""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 캐시는 항상 주 작업트리(my-stock)에 있으므로 고정 경로를 쓴다(어느 워크트리에서 실행해도 동일 대상).
MAIN_REPO = Path(r"C:\Users\hanul\playground\my-stock")
CACHE = MAIN_REPO / ".cache"
LOCAL_DIR = Path(r"C:\Users\hanul\cache-backups")
REPO = "hanurii/my-stock-cache-backup"
KEEP = 7                       # 로컬·GitHub 각각 최근 N개 유지
MIN_SERIES = 2000              # 시계열이 이보다 적으면 미완/손상으로 보고 중단(부분 캐시 백업 방지)
KST = timezone(timedelta(hours=9))


def _stamp() -> str:
    return datetime.now(KST).strftime("%Y%m%d-%H%M")


def _series_count() -> int:
    d = CACHE / "ohlcv" / "series"
    return sum(1 for _ in d.glob("*.json")) if d.exists() else 0


def _make_zip(dest: Path) -> None:
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in CACHE.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(MAIN_REPO))


def _rotate_local() -> None:
    zips = sorted(LOCAL_DIR.glob("cache-*.zip"))
    for old in zips[:-KEEP]:
        old.unlink(missing_ok=True)
        print(f"  로컬 로테이션 삭제: {old.name}")


def _gh(*args: str, check: bool = True, capture: bool = False):
    return subprocess.run(["gh", *args], check=check, text=True,
                          capture_output=capture)


def _rotate_github() -> None:
    out = _gh("release", "list", "--repo", REPO, "--limit", "100",
              "--json", "tagName,createdAt", capture=True)
    rels = json.loads(out.stdout or "[]")
    rels.sort(key=lambda r: r["createdAt"])
    for r in rels[:-KEEP]:
        _gh("release", "delete", r["tagName"], "--repo", REPO,
            "--yes", "--cleanup-tag", check=False)
        print(f"  GitHub 로테이션 삭제: {r['tagName']}")


def main() -> None:
    if not CACHE.exists() or not any(CACHE.iterdir()):
        print(f"❌ 캐시 비어있음: {CACHE} — 백업 중단")
        sys.exit(1)
    n = _series_count()
    if n < MIN_SERIES:
        print(f"❌ 시계열 {n}개 < {MIN_SERIES} — 미완/손상 의심, 백업 중단(부분 캐시 방지)")
        sys.exit(1)

    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"cache-{_stamp()}"
    zpath = LOCAL_DIR / f"{tag}.zip"

    print(f"압축 중(시계열 {n}종목) → {zpath}")
    _make_zip(zpath)
    size_mb = zpath.stat().st_size / 1e6
    print(f"✓ 로컬 저장 {size_mb:.1f}MB")
    _rotate_local()

    print(f"GitHub 릴리스 업로드 → {REPO} {tag} …")
    _gh("release", "create", tag, str(zpath), "--repo", REPO,
        "--title", tag, "--notes", f".cache snapshot {tag} ({n} series, {size_mb:.1f}MB)")
    _rotate_github()
    print(f"✅ 백업 완료 — 로컬 {zpath.name} · GitHub {REPO}:{tag}")


if __name__ == "__main__":
    main()
