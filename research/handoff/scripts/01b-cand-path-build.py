# -*- coding: utf-8 -*-
"""01 — 매수 후 일별 경로 자료 만들기 (토대).

지시서: research/handoff/tasks/01-path-build.md
사전등록: research/handoff/tasks/00-preregistration.md

확정 거래 3,681건 각각의 매수일부터 시계열 끝까지의 경로를 pdata 원본에서 만들어
.cache/bt5y/out/paths_YYYY.json 에 저장하고, 그 경로만으로 +20/-10 을 재계산해
bt_*.json 의 result·days_held·gain_at_resolve_pct 와 전건 일치하는지 확인한다.

★ 시계열 배율 주의
  pdata_series.build_series 는 '구간 마지막 실제 종가'에 배율을 맞춘다. 따라서
  하네스가 그 해를 돌릴 때 쓴 구간(warm = start-430일 ~ end+300일)과 똑같은 구간
  으로 다시 만들어야 entry_price 가 그대로 재현된다. 연도별로 따로 만드는 이유다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/01-path-build.py
난수: 사용하지 않음(seed 없음)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib.pdata_series import build_series  # noqa: E402

PDATA = ROOT / ".cache" / "pdata"
BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
OUT.mkdir(parents=True, exist_ok=True)

TARGET_PCT = 20.0
STOP_PCT = 10.0
# 경로 길이: 지시서는 '최대 300거래일'이었으나 상한을 두지 않는다.
#   (가) 확정 3,681건 중 1건(휠라홀딩스 2023-05-11)이 301거래일째 결착이라
#        300일 상한으로는 합격 관문을 통과할 수 없다.
#   (나) 12번 청산 격자의 기존 9칸에 최장 342거래일 보유가 있다.
#   → 하네스와 같은 구간(시계열 끝)까지 전부 싣는다.
MAX_PATH_DAYS = None
WARM_DAYS = 430          # 하네스 run(): warm_days = 430 (series_source == 'pdata')
RESOLVE_TAIL_DAYS = 300  # 하네스 series_load_end()
MA_WINDOW = 20

YEARS = [2021, 2022, 2023, 2024, 2025, 2026]


def iter_pdata(start: str, end: str, keep: set):
    """하네스 _iter_pdata 와 동일. 단 keep 종목만 남겨 메모리를 줄인다.
    build_series 는 종목별로 독립 계산이므로 걸러도 값이 달라지지 않는다."""
    s, e = start.replace("-", ""), end.replace("-", "")
    for p in sorted(PDATA.glob("price_*.json")):
        d = p.stem[6:]
        if not (s <= d <= e):
            continue
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        yield f"{d[:4]}-{d[4:6]}-{d[6:]}", {c: r for c, r in recs.items() if c in keep}


def series_load_end(end: str) -> str:
    d = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=RESOLVE_TAIL_DAYS)
    return d.strftime("%Y-%m-%d")


def warm_start(start: str) -> str:
    d = datetime.strptime(start, "%Y-%m-%d") - timedelta(days=WARM_DAYS)
    return d.strftime("%Y-%m-%d")


# ── 경로만으로 +T/-S 선착 재계산 (pivot_backtest.simulate_pivot_trade 와 동일) ──

def replay(h, l, c, base: float, target_pct: float, stop_pct: float) -> dict:
    """h/l/c (index 0 = 매수일)로 선착 판정. base = entry_price."""
    n = len(c)
    T = base * (1 + target_pct / 100)
    S = base * (1 - stop_pct / 100)

    def res(kind, i, reason):
        return {"result": kind, "days_held": i, "exit_reason": reason,
                "gain_at_resolve_pct": round((c[i] / base - 1) * 100, 2),
                "max_gain_pct": round((max(h[:i + 1]) / base - 1) * 100, 2),
                "max_dd_pct": round((min(l[:i + 1]) / base - 1) * 100, 2)}

    hit_t, hit_s = h[0] >= T, l[0] <= S
    if hit_t and hit_s:
        return res("ambiguous", 0, "both_same_day_breakout")
    if hit_t:
        return res("win", 0, "target")
    if hit_s:
        return res("ambiguous", 0, "stop_on_breakout_day")
    for i in range(1, n):
        hit_t, hit_s = h[i] >= T, l[i] <= S
        if hit_t and hit_s:
            return res("ambiguous", i, "both_same_day")
        if hit_t:
            return res("win", i, "target")
        if hit_s:
            return res("loss", i, "stop")
    return res("unresolved", n - 1, "open")


def main():
    # 1) 이벤트 수집 + 중복 제거
    raw_counts = {"win": 0, "loss": 0, "ambiguous": 0, "unresolved": 0}
    per_year_events: dict[int, list] = {}
    ranges: dict[int, tuple] = {}
    seen: set = set()
    n_dup = 0
    for y in YEARS:
        d = json.loads((BT / "rec" / ("bt_%d_rec.json" % y)).read_text(encoding="utf-8"))
        ranges[y] = (d["params"]["start"], d["params"]["end"])
        entered = {(e["scan_date"], e["code"], e["pattern"]): e for e in d["events"]}
        keep = []
        for e in d["candidates"]:
            # 실제로 진입한 건은 하네스 결과를 그대로 붙여 관문 대조에 쓴다.
            src = entered.get((e["scan_date"], e["code"], e["pattern"]))
            e["orig_event"] = src
            e["result"] = (src or {}).get("result", "blocked")
            raw_counts[e["result"]] = raw_counts.get(e["result"], 0) + 1
            # v2 개정(12번 0단계): 확정 3,681 뿐 아니라 현행 규칙 진입 3,776키 전부.
            #   ambiguous 74 · unresolved 21 이 12번 (i)고정 유니버스 판과
            #   당일 손절 처리(M1)에 쓰인다.
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen:
                n_dup += 1
                continue
            seen.add(k)
            keep.append(e)
        per_year_events[y] = keep
        print("bt_%d: 전체 %d · 경로대상(중복제거후) %d" % (y, len(d["events"]), len(keep)),
              flush=True)

    n_total = sum(len(v) for v in per_year_events.values())
    n_conf = sum(1 for v in per_year_events.values() for e in v
                 if e["result"] in ("win", "loss"))
    print("경로대상 합계 %d건 (확정 %d) · 중복제거 %d건" % (n_total, n_conf, n_dup), flush=True)

    # 2) 연도별 시계열 재현 → 경로 추출 → 관문 재계산
    FIELDS = ("result", "days_held", "gain", "max_gain", "max_dd", "entry_price")
    # 관문은 '확정(win/loss) 3,681건'이 정본. ambiguous·unresolved 는 따로 센다.
    gate = {g: {k: [0, 0] for k in FIELDS} for g in ("확정", "ambiguous", "unresolved", "blocked")}
    mismatches = []
    missing_series = []
    path_lens = []
    n_truncated = 0
    manifest = []

    for y in YEARS:
        evs = per_year_events[y]
        if not evs:
            continue
        start, end = ranges[y]
        w, le = warm_start(start), series_load_end(end)
        codes = {e["code"] for e in evs}
        print("[%d] 시계열 생성 %s ~ %s · 종목 %d …" % (y, w, le, len(codes)), flush=True)
        full = build_series(iter_pdata(w, le, codes))
        print("[%d]   시계열 보유 %d종목" % (y, len(full)), flush=True)

        out_paths = []
        for e in evs:
            code = e["code"]
            s = full.get(code)
            if not s or e["entry_date"] not in s["dates"]:
                missing_series.append({"code": code, "year": y, "name": e.get("name"),
                                       "entry_date": e["entry_date"],
                                       "reason": "시계열 없음" if not s else "매수일 없음"})
                continue
            ni = s["dates"].index(e["entry_date"])
            hi = len(s["dates"]) if MAX_PATH_DAYS is None                 else min(ni + MAX_PATH_DAYS, len(s["dates"]))
            if MAX_PATH_DAYS is not None and ni + MAX_PATH_DAYS < len(s["dates"]):
                n_truncated += 1
            dates = s["dates"][ni:hi]
            o = s["opens"][ni:hi]
            h = s["highs"][ni:hi]
            l = s["lows"][ni:hi]
            c = s["closes"][ni:hi]
            # 20일선: 매수일 이전 19일 포함해 계산, 배열은 매수일부터
            cl = s["closes"]
            ma20 = []
            for j in range(ni, hi):
                if j + 1 >= MA_WINDOW:
                    ma20.append(sum(cl[j + 1 - MA_WINDOW:j + 1]) / MA_WINDOW)
                else:
                    ma20.append(None)
            # 체결가: 하네스 entry_price(pivot, open) = max(pivot, 익일시가)
            #   pivot 은 이벤트에 소수 둘째자리로만 남아 있어 그대로 쓴다.
            epx = max(e["pivot"], o[0])   # 하네스 entry_price(pivot, 익일시가)와 같은 식
            # ★ 가격은 반올림하지 않는다.
            #   고가가 목표선과 '정확히' 같은 거래가 실제로 존재한다(원본 시·고·저가
            #   호가 단위라 고가/시가 = 1.15 같은 정확한 비가 나온다). 소수 넷째 자리로
            #   반올림하면 그런 건에서 선착 판정이 뒤집힌다(실측: t15s10 티에프이
            #   2025-11-25 win→loss). o/h/l/c/ma20/entry_price 는 원본 정밀도로 싣고,
            #   *_pct 는 눈으로 보는 용도라 넷째 자리로 반올림한다 —
            #   **판정 계산에는 반드시 o/h/l/c 를 쓴다.**
            p = {"code": code, "name": e.get("name"), "scan_date": e["scan_date"],
                 "entry_date": e["entry_date"], "pattern": e["pattern"],
                 "entry_price": epx, "pivot": e["pivot"],
                 "gap_up_pct": e["gap_up_pct"], "orig_result": e["result"],
                 "blocked_overlap": e["blocked_overlap"], "rs": e.get("rs"),
                 "turnover_eok": e.get("turnover_eok"),
                 "dates": dates,
                 "o": o, "h": h, "l": l, "c": c,
                 "ma20": ma20,
                 "o_pct": [round((v / epx - 1) * 100, 4) for v in o],
                 "h_pct": [round((v / epx - 1) * 100, 4) for v in h],
                 "l_pct": [round((v / epx - 1) * 100, 4) for v in l],
                 "c_pct": [round((v / epx - 1) * 100, 4) for v in c]}
            out_paths.append(p)
            path_lens.append(len(dates))

            # ── 관문 ── blocked 후보는 하네스 원본이 없어 대조 대상이 아니다
            r = replay(h, l, c, epx, TARGET_PCT, STOP_PCT)
            if e.get("orig_event") is None:
                gate["blocked"]["result"][0] += 1
                continue
            e = e["orig_event"]
            checks = {
                "result": (r["result"], e["result"]),
                "days_held": (r["days_held"], e["days_held"]),
                "gain": (r["gain_at_resolve_pct"], e["gain_at_resolve_pct"]),
                "max_gain": (r["max_gain_pct"], e["max_gain_pct"]),
                "max_dd": (r["max_dd_pct"], e["max_dd_pct"]),
                "entry_price": (round(epx, 2), e["entry_price"]),
            }
            grp = "확정" if e["result"] in ("win", "loss") else e["result"]
            bad = []
            for k, (mine, orig) in checks.items():
                if mine == orig:
                    gate[grp][k][0] += 1
                else:
                    gate[grp][k][1] += 1
                    bad.append({"field": k, "mine": mine, "orig": orig})
            if bad:
                mismatches.append({"code": code, "name": e.get("name"),
                                   "scan_date": e["scan_date"], "entry_date": e["entry_date"],
                                   "pattern": e["pattern"], "pivot": e["pivot"],
                                   "diffs": bad})

        fp = OUT / ("cand_paths_%d.json" % y)
        fp.write_text(json.dumps(
            {"built_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
             "year": y, "range": [start, end], "series_range": [w, le],
             "target_pct": TARGET_PCT, "stop_pct": STOP_PCT,
             "max_path_days": MAX_PATH_DAYS,
             "n_events": len(out_paths), "paths": out_paths},
            ensure_ascii=False), encoding="utf-8")
        manifest.append({"year": y, "file": fp.name, "n": len(out_paths),
                         "size_mb": round(fp.stat().st_size / 1e6, 1)})
        print("[%d]   저장 %s · %d건 · %.1fMB"
              % (y, fp.name, len(out_paths), fp.stat().st_size / 1e6), flush=True)
        del full

    path_lens.sort()
    summary = {
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "n_targets": n_total,
        "n_confirmed": n_conf,
        "n_paths": sum(m["n"] for m in manifest),
        "raw_result_counts": raw_counts,
        "n_dedup_removed": n_dup,
        "gate": {g: {k: {"match": v[0], "mismatch": v[1]} for k, v in f.items()}
                 for g, f in gate.items()},
        "n_mismatch_events": len(mismatches),
        "mismatch_examples": mismatches[:50],
        "missing_series": missing_series,
        "path_len": {"median": path_lens[len(path_lens) // 2] if path_lens else None,
                     "min": path_lens[0] if path_lens else None,
                     "max": path_lens[-1] if path_lens else None,
                     "n_truncated": n_truncated},
        "files": manifest,
    }
    (OUT / "01b-cand-path-build.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n=== 관문 ===")
    for g, f in gate.items():
        print(" [%s]" % g)
        for k, v in f.items():
            print("   %-12s 일치 %5d · 불일치 %5d" % (k, v[0], v[1]))
    print("불일치 이벤트 %d건 · 시계열 결측 %d건" % (len(mismatches), len(missing_series)))
    print("경로 길이 중앙 %s · 최대 %s · 300일 절단 %d건"
          % (summary["path_len"]["median"], summary["path_len"]["max"], n_truncated))


if __name__ == "__main__":
    main()
