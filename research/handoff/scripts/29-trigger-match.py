# -*- coding: utf-8 -*-
"""🚫🚫 **철회됨 (2026-08-24, 두뇌 세션) — 값을 인용하지 말 것.**

산출물은 **재발 방지 기록으로 보존**한다. 지우지 않는다.

철회 사유 — **빼려던 660건이 「대조군이 누린 필터」가 아니라 «우리 방식이 정의상
더 싸게 사는 칸»이었다.** `16c` 머리말에 이미 증명돼 있었다:

    대안 미발동 ⟺ 전일고가 > 피벗  ⟹  빠지는 건 정확히 「우리가 더 싸게 사는 경우」

조건을 **주문 전에 아는 것**과 **장이 끝나야 아는 것**으로 가르면 드러난다:

| 조건 | 언제 아나 | n | 거래당 |
|---|---|---:|---:|
| 전일 고가 > 피벗 | **주문 전** | 1,805 | −0.3059 |
| 전일 고가 ≤ 피벗 | 주문 전 | 1,967 | +0.1230 |
| 진입일 고가 < 전일 고가 | **장 종료 후** | 596 | **−2.0675** |

**−2.07%는 사실상 전부 「사후에만 아는 부분」에 있다.** 그걸 빼는 것은 편향 보정이 아니라
**처치로 정의된 부분집합을 빼는 것**이다. → **C = −0.4364 는 그대로 유효하다.**

같은 이유로 이 파일이 준비하던 **「피벗 > 전일 고가」 열(4절 가설)도 종결**됐다 —
위 표의 +0.1230 vs −0.3059 가 곧 그 가설이고, 차이 0.4289%p 에 **MDE ≈ 2.8%p** 라
**관측이 MDE의 1/6.5**다. 판정불가.

아래 원 머리말은 **철회 당시 상태 그대로** 둔다.
────────────────────────────────────────────────────────────────────────────

ORIGINAL — 29 · **방아쇠 맞춤 이동폭** — 대조군(β1)만 누린 선택을 우리 팔에서도 걷어낸다 (M39-10).

무엇이 문제인가
---------------
대조군 β1 은 **전일 고가를 못 넘으면 아예 진입하지 않는다.** 즉 대조군 실현 거래의
**100%가 「전일 고가를 넘은 날」**이다. 우리 팔은 그렇지 않다 → `C = 우리 − 대조군` 에
**방아쇠 비대칭**이 섞인다.

그래서 재는 것
--------------
우리 팔을 「진입일 고가 > 전일 고가」와 그 여집합으로 갈라 **거래당 순수익**을 낸다.
**이동폭 = (넘은 건들의 거래당) − (전체 거래당)** 이고, 이것을 기존 C 에 더하면
방아쇠 맞춤 C 가 된다.

부등호는 **취향이 아니라 짝 규칙**이다. β1 정본(`16-selection-edge.py:113~122`):
```python
thr = max(h[di - N + 1:di + 1])          # N=1 이면 D 당일 고가
if h[ni] is None or h[ni] <= thr:        # ← **동점이면 진입하지 않는다**
    return None
epx = max(thr, o[ni] or thr)
```
→ **엄격한 `>`**. 이 파일도 `>` 를 쓴다. `h[ni] is None` 이면 대조군 세계에서도
진입 여부를 판정할 수 없으므로 **결측 팔로 따로 뺀다**(두뇌 세션 결정).

🚨 **헤드라인은 전체 집합 그대로 둔다.** 이 팔은 **점추정을 읽는 방식**을 고치는 것이지
   판정을 바꾸는 게 아니다. n 이 줄어 MDE 는 커진다 — 함께 적는다.

자료
----
- 한국: `.cache/pdata/price_*.json` 의 **원본 `hipr`**. ⚠️ 하네스는 **수정 고가**를 본다 —
  둘은 **기준가 변경일에만** 갈리므로 그 건수를 함께 센다.
- 미국: Sharadar `high`(분할 조정) — 하네스가 쓰는 바로 그 값이라 갈릴 일이 없다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/29-trigger-match.py kr|us
난수 seed: 부트스트랩 290824
"""
from __future__ import annotations

import csv
import io
import json
import random
import re
import statistics as st
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_BOOT = 1000
BOOT_SEED = 290824
BLOCK = (20, 40)
EXCLUDE = re.compile(
    "스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|[0-9]우$|우$|우\\(전환\\)|우B\\(전환\\)")
FOREIGN = re.compile("^9[0-9]{5}$")


def load_events(mkt):
    ev = []
    if mkt == "kr":
        for y in range(2021, 2027):
            f = BT / ("bt_%d.json" % y)
            if f.exists():
                ev += json.loads(f.read_text(encoding="utf-8"))["events"]
    else:
        f = BT / "sub" / "us_full.json"
        if not f.exists():
            return None
        ev = json.loads(f.read_text(encoding="utf-8"))["events"]
    seen, out = set(), []
    for e in sorted(ev, key=lambda x: (x["entry_date"], x["code"], x.get("pattern", ""))):
        k = (e["scan_date"], e["code"], e.get("pattern", ""))
        if k in seen or e.get("gain_at_resolve_pct") is None:
            continue
        seen.add(k)
        out.append(e)
    return out


def highs_kr(need):
    """need = {(code, date)} 의 진입일 고가와 **직전 거래일** 고가. 원본 hipr."""
    PD = ROOT / ".cache" / "pdata"
    dates_needed = {d for _c, d in need}
    codes = {c for c, _d in need}
    prev, out, rebase = {}, {}, set()
    for p in sorted(PD.glob("price_*.json")):
        d = p.stem[6:]
        date = "%s-%s-%s" % (d[:4], d[4:6], d[6:])
        if date < "2020-06-01":
            continue
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        cur = {}
        for code, r in recs.items():
            if code not in codes:
                continue
            if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ") or FOREIGN.match(code):
                continue
            if EXCLUDE.search(r.get("itmsNm") or ""):
                continue
            try:
                h = float(r.get("hipr") or 0)
                c = float(r.get("clpr") or 0)
                f = r.get("fltRt")
                f = float(f) if f is not None else None
            except (TypeError, ValueError):
                continue
            if h <= 0:
                continue
            cur[code] = (h, c)
            if (code, date) in need:
                pv = prev.get(code)
                out[(code, date)] = (h, pv[0] if pv else None)
                # 기준가 변경 판정: 등락률과 비수정 종가비가 크게 어긋나면 원본 고가 비교가
                # 수정 고가 비교와 갈릴 수 있다.
                if pv and f is not None and pv[1]:
                    if abs((c / pv[1] - 1) - f / 100.0) > 0.10:
                        rebase.add((code, date))
        prev = cur
    return out, rebase


def highs_us(need):
    import us_loader as U
    dates = {d for _c, d in need}
    codes = {c for c, _d in need}
    ser = defaultdict(list)
    with zipfile.ZipFile(U.STOCKS_ZIP) as z:
        rd = csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"))
        next(rd)
        for row in rd:
            t, d = row[0], row[1]
            if t not in codes or d < "2020-09-01":
                continue
            ser[t].append((d, float(row[3])))          # high (분할 조정)
    out = {}
    for t, v in ser.items():
        v.sort()
        for i, (d, h) in enumerate(v):
            if (t, d) in need:
                out[(t, d)] = (h, v[i - 1][1] if i > 0 else None)
    return out, set()


def boot_mean(vals, keys, dates):
    """진입일 블록 재추출로 거래당 평균의 자료 축 구간."""
    byd = defaultdict(list)
    for v, d in zip(vals, dates):
        byd[d].append(v)
    ds = sorted(byd)
    n = len(ds)
    rnd = random.Random(BOOT_SEED)
    means = []
    for _ in range(N_BOOT):
        acc, cnt, tot = 0.0, 0, 0
        while tot < n:
            L = rnd.randint(*BLOCK)
            a = rnd.randint(0, max(0, n - L))
            for j in range(min(L, n - tot)):
                acc += sum(byd[ds[a + j]])
                cnt += len(byd[ds[a + j]])
            tot += L
        means.append(acc / cnt if cnt else 0.0)
    s = sorted(means)
    return (st.mean(vals), s[int(N_BOOT * .025)], s[int(N_BOOT * .975)],
            2.80 * st.pstdev(means))


def main():
    mkt = sys.argv[1] if len(sys.argv) > 1 else "kr"
    ev = load_events(mkt)
    if ev is None:
        print("🚨 미국 본 실행 산출물이 아직 없다.", flush=True)
        return
    need = {(e["code"], e["entry_date"]) for e in ev}
    print("%s 진입 %d건 · 필요한 (종목,진입일) %d쌍" % (mkt.upper(), len(ev), len(need)),
          flush=True)
    hi, rebase = (highs_kr if mkt == "kr" else highs_us)(need)
    print("고가 복원 %d쌍 (결측 %d) · 기준가 변경 의심 %d쌍"
          % (len(hi), len(need) - len(hi), len(rebase)), flush=True)

    above, below, missing = [], [], []
    cols = []          # 4절 자료 준비 — 피벗 vs 전일 고가 (판정하지 않는다)
    for e in ev:
        k = (e["code"], e["entry_date"])
        v = hi.get(k)
        net = slot_sim.net(e["gain_at_resolve_pct"])
        rec = (net, e["entry_date"], e["result"])
        if not v or v[1] is None:
            missing.append(rec)
        elif v[0] > v[1]:
            above.append(rec)
        else:
            below.append(rec)
        cols.append({"code": e["code"], "entry_date": e["entry_date"],
                     "pivot": e.get("pivot"), "entry_price": e.get("entry_price"),
                     "high_entry": v[0] if v else None,
                     "high_prev": v[1] if v else None,
                     "pattern": e.get("pattern"), "result": e["result"]})
    allr = above + below + missing
    print("", flush=True)
    print("=" * 74, flush=True)
    print("방아쇠(전일 고가 돌파) 여부별 거래당 순수익", flush=True)
    print("=" * 74, flush=True)
    rows = {}
    for lab, xs in (("전체", allr), ("**전일 고가 넘음**", above),
                    ("못 넘음", below), ("고가 결측", missing)):
        if not xs:
            print("  %-16s n=0" % lab, flush=True)
            continue
        m, lo, h2, mde = boot_mean([x[0] for x in xs], None, [x[1] for x in xs])
        wr = sum(1 for x in xs if x[2] == "win") / len(xs) * 100
        rows[lab] = {"n": len(xs), "per_trade": m, "lo": lo, "hi": h2,
                     "mde": mde, "win_rate": wr}
        print("  %-16s n=%5d · 거래당 **%+.4f%%** (95%% %+.4f ~ %+.4f · MDE %.4f) · 승률 %.2f%%"
              % (lab, len(xs), m, lo, h2, mde, wr), flush=True)
    if "**전일 고가 넘음**" in rows and "전체" in rows:
        shift = rows["**전일 고가 넘음**"]["per_trade"] - rows["전체"]["per_trade"]
        keep = rows["**전일 고가 넘음**"]["n"] / rows["전체"]["n"] * 100
        print("", flush=True)
        print("  🚨 **이동폭 = %+.4f%%p** (넘은 건 − 전체) · 남는 표본 **%.1f%%**"
              % (shift, keep), flush=True)
        print("     기존 C 에 이 값을 더한 것이 방아쇠 맞춤 C 다.", flush=True)
        print("     n 이 줄어 MDE 는 커진다: 전체 %.4f → 맞춤 %.4f %%p"
              % (rows["전체"]["mde"], rows["**전일 고가 넘음**"]["mde"]), flush=True)
        rows["_shift_pct_p"] = shift
        rows["_keep_pct"] = keep
    rows["_rebase_suspect_pairs"] = len(rebase)

    # ── 4절 자료 준비 (두뇌 세션) — **비율만 본다. 거래당·승률은 계산하지 않는다.** ──
    # ⚠️ 이 가설은 **같은 자료에서 발견해 같은 자료로 재려는 것**이다. 사후 가설임을
    #    처음부터 기록에 단다. 검정은 검증 세션이 사전등록을 끝낸 뒤에 한다.
    ok = [c for c in cols if c["pivot"] is not None and c["high_prev"] is not None]
    npv = sum(1 for c in ok if c["pivot"] > c["high_prev"])
    print("", flush=True)
    print("  [4절 자료] **피벗 > 전일 고가** 인 진입: **%d / %d = %.1f%%**"
          % (npv, len(ok), npv / len(ok) * 100 if ok else 0), flush=True)
    print("     (수학적으로 이 집합은 「전일 고가 넘음」의 **부분집합**이고,"
          " **장 시작 전에 알 수 있다**.)", flush=True)
    print("     [종결] 2026-08-24. 사유는 «룩어헤드»가 아니라 «검정력 부족»이다.", flush=True)
    print("        차이 0.4289%p 에 MDE 약 2.8%p (관측이 MDE의 1/6.5) · 거래는 52%로 반토막.",
          flush=True)
    print("        가설 자체는 실행 가능하다(피벗·전일 고가 둘 다 장 전에 안다). 못 가릴 뿐이다.",
          flush=True)
    rows["_pivot_gt_prevhigh"] = {"n": npv, "n_evaluable": len(ok),
                                  "pct": npv / len(ok) * 100 if ok else None,
                                  "note": "사후 가설 · 검정력 부족으로 종결(2026-08-24) · 재검정 금지"}
    (OUT / ("29-cols-%s.json" % mkt)).write_text(
        json.dumps(cols, ensure_ascii=False), encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("29-trigger-match-%s.json" % mkt)).write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/29-trigger-match-%s.json" % mkt, flush=True)


if __name__ == "__main__":
    main()
