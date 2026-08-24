# -*- coding: utf-8 -*-
"""**요약 산출물 스냅샷** — 「숫자 → 요약 JSON → 스크립트」 고리를 저장소 안에서 닫는다.

왜
--
`.cache/` 는 통째로 `.gitignore:8` 에 걸린다. 그래서 지금까지 커밋된 것은
**스크립트와 결과 문서뿐**이고 **숫자를 만든 중간 파일은 저장소에 없었다.**
21번 감사의 **「코드 없음 9행」이 정확히 이 구조**에서 났다 —
**입력이 사라지면 스크립트가 있어도 재현이 안 된다.**

규칙
----
- `.cache/bt5y/out/*.json` 중 **개당 5MB 이하**만 `results/data/` 로 복사한다
- **5MB를 넘는 것은 「무엇이 얼마나 커서 안 넣었는지」를 목록으로 남긴다** (무언의 절단 금지)
- 파일마다 **어느 스크립트가 만들었는지** 한 줄
- 🚨 **`.cache/sharadar/` 는 절대 손대지 않는다** — 라이선스상 재배포 금지

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/_snapshot_data.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / ".cache" / "bt5y" / "out"
DST = ROOT / "research" / "handoff" / "results" / "data"
LIMIT = 5 * 1024 * 1024

# 산출 스크립트 — 파일 이름 앞부분으로 찾는다
MADE_BY = [
    ("25-split-factors", "research/handoff/scripts/25-split-check.py"),
    ("25-split-impact", "research/handoff/scripts/25-split-impact.py"),
    ("25-g3prime", "research/handoff/scripts/25-g3prime.py"),
    ("26-eqw", "research/handoff/scripts/26-eqw.py"),
    ("27-kr-extreme-audit", "research/handoff/scripts/27-kr-extreme-audit.py"),
    ("28-headline", "research/handoff/scripts/28-headline.py"),
    ("29-trigger-match", "research/handoff/scripts/29-trigger-match.py  ⚠️철회됨"),
    ("29-cols", "research/handoff/scripts/29-trigger-match.py  ⚠️철회됨"),
    ("30-arm25", "research/handoff/scripts/30-arm25.py"),
    ("31-slot-diagnosis", "research/handoff/scripts/31-slot-diagnosis.py"),
    ("32-funnel-why", "research/handoff/scripts/32-funnel-why.py"),
    ("33-unresolved", "research/handoff/scripts/33-unresolved-and-extremes.py"),
    ("34-turnover", "research/handoff/scripts/34-turnover-concentration.py"),
    ("23-", "research/handoff/scripts/23-stage0-ratchet.py 외 23* 계열"),
    ("22-", "research/handoff/scripts/22-gapup-volume.py"),
]


SCRIPTS = ROOT / "research" / "handoff" / "scripts"


def _grep_writers():
    """🚨 **추정이 아니라 확인이다.** 스크립트 본문에 그 JSON 파일 이름이
    «문자열로 들어 있는지»를 본다 — 들어 있으면 그 스크립트가 그 파일을 쓴다.
    이름이 비슷하다는 이유로 짝지으면 21번 감사가 잡은 것과 같은 병이 된다."""
    src = {}
    for f in sorted(SCRIPTS.glob("*.py")):
        try:
            src[f.name] = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    return src


_SRC = None


def made_by(name):
    global _SRC
    for pre, path in MADE_BY:
        if name.startswith(pre):
            return path
    if _SRC is None:
        _SRC = _grep_writers()
    # 확장자를 뗀 이름이 스크립트 본문에 있으면 그 스크립트가 쓴 것이다
    stem = name[:-5] if name.endswith(".json") else name
    # 이름이 «나오는» 것과 «쓰는» 것은 다르다 — 다른 스크립트의 산출을 «읽는» 경우가 있다.
    # 그래서 그 이름이 나온 줄 주변 3줄에 write_text / json.dump 가 있는지까지 본다.
    hits = []
    for k, v in _SRC.items():
        if stem not in v:
            continue
        rows = v.split(chr(10))
        writes = False
        for idx, line in enumerate(rows):
            if stem in line:
                near = chr(10).join(rows[max(0, idx - 3):idx + 4])
                if "write_text" in near or "json.dump" in near or "open(" in near:
                    writes = True
                    break
        if writes:
            hits.append(k)
    if len(hits) == 1:
        return "research/handoff/scripts/%s  (본문 대조 확인)" % hits[0]
    if len(hits) > 1:
        return "research/handoff/scripts/{%s}  (본문 대조 · **여러 개 — 확정 필요**)" % ", ".join(hits)
    return "**미상 — 적을 것**"

def main():
    DST.mkdir(parents=True, exist_ok=True)
    kept, skipped = [], []
    for f in sorted(SRC.glob("*.json")):
        sz = f.stat().st_size
        if sz <= LIMIT:
            shutil.copy2(f, DST / f.name)
            kept.append((f.name, sz))
        else:
            skipped.append((f.name, sz))
    lines = [
        "# 요약 산출물 스냅샷 (`results/data/`)",
        "",
        "> 만든 것: `research/handoff/scripts/_snapshot_data.py`",
        "> 원본 위치: `.cache/bt5y/out/` — **`.gitignore:8` 의 `.cache/` 에 걸려 추적되지 않는다.**",
        "> 그래서 **숫자를 만든 중간 파일이 저장소에 없었고**, 그게 21번 감사의",
        "> 「코드 없음 9행」이 난 구조다. **입력이 사라지면 스크립트가 있어도 재현이 안 된다.**",
        "> 이 폴더가 그 고리를 닫는다: **숫자 → 요약 JSON → 스크립트.**",
        "",
        "🚨 **`.cache/sharadar/` 는 여기에 절대 넣지 않는다** — 라이선스상 재배포 금지 ·",
        "해지 후 삭제 의무. 이 스냅샷은 **파생 집계만** 담는다.",
        "",
        "@@UNKNOWN@@",
        "## 넣은 것 (개당 5MB 이하)",
        "",
        "| 파일 | 크기 | 만든 스크립트 |",
        "|---|---:|---|",
    ]
    for n, sz in kept:
        lines.append("| `%s` | %.1f KB | `%s` |" % (n, sz / 1024, made_by(n)))
    lines += ["", "## 🚨 안 넣은 것 — **무언의 절단이 아니다. 크기와 함께 적는다**", ""]
    if skipped:
        lines += ["| 파일 | 크기 | 만든 스크립트 |", "|---|---:|---|"]
        for n, sz in skipped:
            lines.append("| `%s` | **%.1f MB** | `%s` |" % (n, sz / 1024 / 1024, made_by(n)))
    else:
        lines.append("**없음 — 5MB를 넘는 요약 산출물이 하나도 없다.**")
    lines += [
        "",
        "## 여기에 없는 것 (설계상)",
        "",
        "- **이벤트 목록 원본** (`.cache/bt5y/sub/*.json`, `bt_*.json`) — 개당 0.3~5MB이고",
        "  2.5단계 관문만 팔은 150~200MB로 예상된다. **결과 문서의 숫자는 전부 요약 JSON에서",
        "  나오므로 재현에 필요한 것은 위 표로 충분하다.**",
        "- **가격 원본** (`.cache/pdata/`, `.cache/sharadar/`) — 전자는 용량, 후자는 라이선스.",
        "",
        "총 %d개 넣음 · %d개 제외." % (len(kept), len(skipped)),
    ]
    unknown = [n for n, _ in kept if made_by(n).startswith("**미상")]
    if unknown:
        blk = ([
            "## 🚨 **미해결 과제 — 산출 스크립트 «미상» %d파일**" % len(unknown), "",
            "**「정의 미상」으로 분류했으면 정의를 찾는 것이 과제다. 목록이 없으면 아무도 안 찾는다.**", "",
            "🚨 **채울 때 규칙: 「추정」이 아니라 「파일 내용과 스크립트 출력이 «일치함을 확인»」으로만.**",
            "추정으로 채우면 21번 감사가 잡은 것과 **같은 병**이다.", "",
        ] + ["- [ ] `%s`" % n for n in unknown] + [""])
    else:
        blk = ["## 미해결 과제", "", "**없음 — 모든 파일의 산출 스크립트가 확인됐다.**", ""]
    body = chr(10).join(lines).replace("@@UNKNOWN@@", chr(10).join(blk))
    (DST / "MANIFEST.md").write_text(body, encoding="utf-8")
    print("산출 스크립트 «미상» %d파일 — MANIFEST 맨 위에 과제로 올림" % len(unknown))
    print("넣음 %d개 · 제외 %d개" % (len(kept), len(skipped)))
    for n, sz in kept:
        print("  + %-42s %8.1f KB" % (n, sz / 1024))
    for n, sz in skipped:
        print("  - %-42s %8.1f MB  ← 제외" % (n, sz / 1024 / 1024))
    print("MANIFEST: research/handoff/results/data/MANIFEST.md")


if __name__ == "__main__":
    main()
