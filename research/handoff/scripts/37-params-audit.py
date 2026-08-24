# -*- coding: utf-8 -*-
"""37 · **파일 이름을 믿지 말고 산출물의 `params` 를 읽는다** — 입력 전수 대조.

왜
--
오늘 「이름은 `ge` 인데 내용은 `strict`」 사고가 났다. `_gate_run.sh` 에서
`--gate-tie "$TIE"` 가 빠져 있었는데 **파일 이름만 `SFX` 로 갈렸다.**
→ 항등 검산이 잡았지만, **그건 결과를 만든 뒤에 잡는다.**
   `params` 대조는 **읽는 순간에** 잡는다.

🚨 **그리고 이 버그는 「우리가 기대하던 답」을 냈다** — 「두 판이 완전히 같다」는
   우리가 «강한 결과»라고 미리 적어 둔 문장이다. **가장 위험한 버그는 기대하던 답을 내는 버그다.**

무엇을 대조하나
---------------
파일 이름·문서 서술에서 **기대하는 값**과 산출물 `params` 의 **실제 값**:
  `market` · `arm` · `gate_tie` · `series_source` · `start` · `end` · `warm_days`
⚠️ **`market`·`warm_days` 는 오늘 오후에야 기록하기 시작했다.** 그 전 파일은 **「미기록」**이고,
   그 경우 `series_source` 와 **하루 유니버스 규모**(한국 ~2,400 · 미국 ~4,400)로 **간접 확인**한다.
   **간접 확인은 직접 확인이 아니다.** 그 사실을 그대로 찍는다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/37-params-audit.py
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"

# (경로, 기대 market, 기대 arm, 기대 gate_tie, 기대 series_source, 기대 연도)
EXPECT = []
for y in range(2021, 2027):
    EXPECT.append((BT / ("bt_%d.json" % y), "kr", "pattern", "strict", "pdata", y))
    EXPECT.append((BT / "sub" / ("us_%d.json" % y), "us", "pattern", "strict", "cache", y))
    EXPECT.append((BT / "sub" / ("kr_gate_%d.json" % y), "kr", "gate", "strict", "pdata", y))
    EXPECT.append((BT / "sub" / ("kr_gatege_%d.json" % y), "kr", "gate", "ge", "pdata", y))
    EXPECT.append((BT / "sub" / ("us_gate_%d.json" % y), "us", "gate", "strict", "cache", y))
    EXPECT.append((BT / "sub" / ("us_gatege_%d.json" % y), "us", "gate", "ge", "cache", y))

UNI = {"kr": (1800, 3200), "us": (3500, 5600)}     # (옛) 하루 유니버스 규모 — «간접»
CODE_RE = {"kr": __import__("re").compile("^[0-9]{6}$"),
           "us": __import__("re").compile("^[A-Z][A-Z0-9.-]*$")}
# 🚨 **간접을 «직접»으로 바꾼다.** `events` 의 종목 코드 형식은 섞일 수 없다 —
#    한국은 6자리 숫자(`005930`), 미국은 영문 티커(`AAPL`).
#    유니버스 «규모»는 우연히 비슷할 수 있지만 **코드 형식은 그럴 수 없다.**


def check(path, mkt, arm, tie, ser, year):
    if not path.exists():
        return {"file": path.name, "status": "없음"}
    d = json.loads(path.read_text(encoding="utf-8"))
    p = d.get("params") or {}
    bad, ind = [], []
    def eq(key, want, default=None):
        got = p.get(key, default)
        if got is None:
            return None
        if got != want:
            bad.append("%s: 기대 %r · 실제 %r" % (key, want, got))
        return got
    # ── 시장 확인: `market` 필드가 없어도 **코드 형식으로 «직접»** 확인한다 ──
    codes = {e.get("code") for e in (d.get("events") or [])}
    codes.discard(None)
    rx = CODE_RE[mkt]
    other = sorted(c for c in codes if not rx.match(c))
    if codes:
        if other:
            bad.append("코드 형식: %s 형식이 아닌 코드 %d개 (예 %s)"
                       % (mkt, len(other), ", ".join(other[:5])))
        else:
            ind.append("코드 %d개 전부 %s 형식 → **직접** 확인" % (len(codes), mkt))
    got_mkt = p.get("market")
    if got_mkt is None:
        if not codes:
            per = d.get("per_date") or []
            u = st.median([x.get("n_universe") or 0 for x in per]) if per else 0
            lo, hi = UNI[mkt]
            if not (lo <= u <= hi):
                bad.append("market 미기록 · 코드 없음 · 간접(유니버스 %.0f)도 밖" % u)
            else:
                ind.append("market 미기록 · 코드 없음 → 유니버스 %.0f 로 «간접»" % u)
        else:
            ind.append("`market` 필드는 미기록(오늘 오후부터 기록)")
    elif got_mkt != mkt:
        bad.append("market: 기대 %r · 실제 %r" % (mkt, got_mkt))
    eq("arm", arm, "pattern")
    eq("gate_tie", tie, "strict")
    eq("series_source", ser)
    eq("start", "%d-01-01" % year if year != 2021 else "2021-02-01")
    eq("end", "%d-12-31" % year if year != 2026 else "2026-08-21")
    w = p.get("warm_days")
    if w is None:
        ind.append("warm_days 미기록")
    elif w != 430:
        bad.append("warm_days: 기대 430 · 실제 %r" % w)
    return {"file": path.name, "status": "불일치" if bad else "일치",
            "bad": bad, "indirect": ind}


def main():
    rows = [check(*e) for e in EXPECT]
    have = [r for r in rows if r["status"] != "없음"]
    bad = [r for r in have if r["status"] == "불일치"]
    ind = [r for r in have if r.get("indirect")]
    print("=" * 84, flush=True)
    print("입력 `params` 전수 대조 — **파일 이름을 믿지 않는다**", flush=True)
    print("=" * 84, flush=True)
    print("  대상 %d개 중 **존재 %d개** · 없음 %d개"
          % (len(rows), len(have), len(rows) - len(have)), flush=True)
    miss = [r["file"] for r in rows if r["status"] == "없음"]
    if miss:
        print("  (없음: %s)" % ", ".join(miss), flush=True)
    if bad:
        print("", flush=True)
        print("  🚨 **불일치 %d개**" % len(bad), flush=True)
        for r in bad:
            print("    - %-24s %s" % (r["file"], " · ".join(r["bad"])), flush=True)
    else:
        print("", flush=True)
        print("  ✅ **전수 대조 0건 불일치**", flush=True)
    if ind:
        print("", flush=True)
        print("  참고 — 확인 경로 (%d개 파일):" % len(ind), flush=True)
        for r in ind[:8]:
            print("    - %-24s %s" % (r["file"], " · ".join(r["indirect"])), flush=True)
        if len(ind) > 8:
            print("    … 외 %d개 (전부 같은 사유)" % (len(ind) - 8), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "37-params-audit.json").write_text(
        json.dumps({"n_expected": len(rows), "n_present": len(have),
                    "n_mismatch": len(bad), "rows": rows},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/37-params-audit.json", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
