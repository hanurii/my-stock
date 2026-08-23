# -*- coding: utf-8 -*-
"""14 — −10% 손절 우위 재확인 (12번보다 우선).

지시서: research/handoff/tasks/14-stop-loss-recheck.md

두 팔을 **01번 경로 자료의 고정 진입 3,776키** 위에서 새로 만든다(하네스 재실행 없음).
어느 쪽에서도 키를 빼지 않는다 — 이것이 이 재확인의 핵심이다.

| 팔 | 정의 |
|---|---|
| ① 현행     | +20% 목표 / −10% 손절 선착. 체결가는 **닿은 날 종가** |
| ② 목표만   | +20% 목표, **손절 없음** |
| ③ 둘 다 없음 | **끝까지 보유** — 목표도 손절도 없음 |

비교 셋: **①vs② = 손절의 몫(판정 대상)** · ②vs③ = 익절(+20% 고정)의 몫 ·
①vs③ = 지금까지 "손절이 수익원"으로 섞여 인용되던 값.

- 매수 당일 손절 터치도, 목표·손절 동시 접촉도 **그날 종가 체결**로 표본에 포함한다.
  (하네스는 이런 건을 ambiguous 로 지워 손절 팔에서만 74건이 사라졌다 — 그게 이 과제의 이유다.)
- 같은 날 둘 다 닿은 건은 어느 쪽이 먼저인지 모르지만 **체결가가 그날 종가로 같아** 손익은 같다.
  승/패 라벨은 두뇌 세션이 못 박은 규칙을 쓴다 —
  **목표 도달 = 승 / 손절 도달 = 패 / 같은날 동시 접촉 = 패(보수적) /
  마지막 종가 청산 = 손익 부호, 정확히 0.00%면 패(보수적)**.
  이러면 매수가 ±0.005 흔들기에 라벨이 바뀌지 않는다.
- 미결착(둘 다 미도달): 주 판정 = 마지막 종가 청산.
  민감도 ㉠ 종목 소멸 건을 두 팔 모두에서 제외 · ㉡ 종목 소멸 미결착 건을 −50% 청산.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/14-stop-loss-recheck.py
난수 seed: 수준 0~199 · 짝비교 0~399 (고정)
"""
from __future__ import annotations

import bisect
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
TARGET, STOP = 20.0, 10.0
N_LEVEL, N_PAIR = 200, 400
YEARS = ["2021", "2022", "2023", "2024", "2025", "2026"]
VANISH_EXIT = -50.0        # 민감도 ㉡ 정리매매 근사

net = slot_sim.net


def load_paths():
    P, year_last = {}, {}
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        last = ""
        for p in d["paths"]:
            h, l = p["h"], p["l"]
            rmax, rmin = [], []
            mh, ml = -1e30, 1e30
            for i in range(len(h)):
                if h[i] > mh:
                    mh = h[i]
                if l[i] < ml:
                    ml = l[i]
                rmax.append(mh)
                rmin.append(-ml)
            last = max(last, p["dates"][-1])
            P[(p["scan_date"], p["code"], p["pattern"])] = {
                "code": p["code"], "pattern": p["pattern"], "scan_date": p["scan_date"],
                "entry_date": p["entry_date"], "entry_price": p["entry_price"],
                "year": y, "end_date": p["dates"][-1], "dates": p["dates"],
                "c": p["c"], "rmax": rmax, "rmin_neg": rmin, "n": len(h)}
        year_last[y] = last
    for p in P.values():
        p["vanished"] = p["end_date"] < year_last[p["year"]]
    print("경로 %d건 · 종목 소멸 %d건 · 연도별 시계열 끝 %s"
          % (len(P), sum(1 for p in P.values() if p["vanished"]), year_last), flush=True)
    return P


def resolve(p, arm: str, vanish: str = "last_close"):
    """한 거래의 결과. arm: '①'(목표+손절) | '②'(목표만) | '③'(끝까지 보유).
    vanish: 'last_close' | 'drop' | 'liquidate'.

    반환 None = 그 판에서 표본에서 뺀 건(민감도 ㉠만 발생).
    """
    e = p["entry_price"]
    n = p["n"]
    ti = si = None
    if arm in ("①", "②"):
        T = e * (1 + TARGET / 100)
        ti = bisect.bisect_left(p["rmax"], T)
        ti = ti if ti < n else None
    if arm == "①":
        S = e * (1 - STOP / 100)
        si = bisect.bisect_left(p["rmin_neg"], -S)
        si = si if si < n else None

    if ti is None and si is None:                       # 미결착
        if p["vanished"]:
            if vanish == "drop":
                return None
            if vanish == "liquidate":
                return {"gain": VANISH_EXIT, "days": n - 1,
                        "resolve_date": p["dates"][-1], "reason": "vanish_liquidate"}
        i = n - 1
        return {"gain": (p["c"][i] / e - 1) * 100, "days": i,
                "resolve_date": p["dates"][i],
                "reason": "unres_vanished" if p["vanished"] else "unres_windowend"}
    if si is None:
        i, why = ti, "target"
    elif ti is None:
        i, why = si, "stop"
    elif ti < si:
        i, why = ti, "target"
    elif si < ti:
        i, why = si, "stop"
    else:
        i, why = ti, "both_same_day"
    return {"gain": (p["c"][i] / e - 1) * 100, "days": i,
            "resolve_date": p["dates"][i], "reason": why}


def label(r):
    """승/패 라벨 — 청산 사유로 정한다(두뇌 세션 확정).
    목표=승 · 손절=패 · 동시접촉=패(보수) · 마지막 종가=손익 부호(0.00%면 패)."""
    if r["reason"] == "target":
        return "win"
    if r["reason"] in ("stop", "both_same_day", "vanish_liquidate"):
        return "loss"
    return "win" if r["gain"] > 0 else "loss"


def build_arm(P, arm_name, vanish, keys=None):
    out = []
    for k, p in P.items():
        if keys is not None and k not in keys:
            continue
        r = resolve(p, arm_name, vanish)
        if r is None:
            continue
        out.append({"key": k, "code": k[1], "pattern": k[2], "scan_date": k[0],
                    "entry_date": p["entry_date"], "resolve_date": r["resolve_date"],
                    "gain": r["gain"], "days": r["days"], "reason": r["reason"],
                    "year": k[0][:4],
                    "result": label(r)})
    return out


def summarize(ts):
    v = [net(t["gain"]) for t in ts]
    # 승률·본전 승률은 라벨(청산 사유) 기준. 평균 손익 계산도 같은 라벨로 가른다.
    w = [net(t["gain"]) for t in ts if t["result"] == "win"]
    l = [net(t["gain"]) for t in ts if t["result"] == "loss"]
    wr = len(w) / len(v) * 100 if v else 0.0
    be = (abs(st.mean(l)) / (st.mean(w) + abs(st.mean(l))) * 100) if w and l else None
    return {"n": len(v), "win_rate": wr, "breakeven": be,
            "edge": (wr - be) if be is not None else None,
            "mean_net": st.mean(v) if v else 0.0,
            "n_target": sum(1 for t in ts if t["reason"] == "target"),
            "n_stop": sum(1 for t in ts if t["reason"] == "stop"),
            "n_both": sum(1 for t in ts if t["reason"] == "both_same_day"),
            "n_unres_van": sum(1 for t in ts if t["reason"] == "unres_vanished"),
            "n_unres_win": sum(1 for t in ts if t["reason"] == "unres_windowend"),
            "n_liquidate": sum(1 for t in ts if t["reason"] == "vanish_liquidate"),
            "median_days": st.median([t["days"] for t in ts]) if ts else None}


def drop_top(ts, k=5):
    idx = set(sorted(range(len(ts)), key=lambda i: -net(ts[i]["gain"]))[:k])
    return [t for i, t in enumerate(ts) if i not in idx]


def old_approx(P):
    """옛 '무손절 근사'(analyze2.py ⑤절) 재현 — 왜 비교가 어긋났는지 보이기 위해서만."""
    ev = {}
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            ev[(e["scan_date"], e["code"], e["pattern"])] = e
    conf = [e for e in ev.values() if e["result"] in ("win", "loss")]
    rows = {}
    for y in YEARS:
        g = [e for e in conf if e["scan_date"][:4] == y]
        real = st.mean([net(e["gain_at_resolve_pct"]) for e in g])
        nost = st.mean([net(e["gain_at_resolve_pct"] if e["result"] == "win"
                            else e["max_dd_pct"]) for e in g])
        rows[y] = {"n": len(g), "rule": real, "nostop": nost, "diff": real - nost}
    losses = [e for e in conf if e["result"] == "loss"]
    gaps = [net(e["gain_at_resolve_pct"]) - net(e["max_dd_pct"]) for e in losses]
    n_worse = sum(1 for e in losses if e["max_dd_pct"] > e["gain_at_resolve_pct"])
    share = len(losses) / len(conf) * 100
    dom = {"n_loss": len(losses), "n_worse": n_worse,
           "pct_worse": n_worse / len(losses) * 100 if losses else 0.0,
           "mean_gap": st.mean(gaps) if gaps else 0.0,
           "loss_share": share,
           "expected_diff": (share / 100) * (st.mean(gaps) if gaps else 0.0)}
    return rows, len(conf), dom


ARMS = ["①", "②", "③"]
ARM_LABEL = {"①": "① 현행 +20/−10", "②": "② 목표만(+20, 손절 없음)",
             "③": "③ 둘 다 없음(끝까지 보유)"}
PAIRS = [("①vs② 손절의 몫", "①", "②"),
         ("②vs③ 익절의 몫", "②", "③"),
         ("①vs③ 섞인 값", "①", "③")]
WINDOWS = [("전체", None), ("2026-02-21 이후 진입 제외", "2026-02-21")]
VANISH_PLANS = [("주판정 · 마지막 종가", "last_close"),
                ("㈠ 종목 소멸 제외", "drop"),
                ("㈡ 종목 소멸 −50% 청산", "liquidate")]


def main():
    P = load_paths()
    res = {"n_universe": len(P),
           "n_vanished": sum(1 for p in P.values() if p["vanished"]),
           "n_level_runs": N_LEVEL, "n_pair_runs": N_PAIR, "runs": {}}

    for wname, cut in WINDOWS:
        base_keys = ({k for k, p in P.items() if p["entry_date"] <= cut}
                     if cut else set(P))
        for vname, vanish in VANISH_PLANS:
            keys = base_keys
            if vanish == "drop":
                keys = {k for k in base_keys if not P[k]["vanished"]}
            arms = {a: build_arm(P, a, vanish, keys) for a in ARMS}
            ksets = {a: {t["key"] for t in arms[a]} for a in ARMS}
            same = ksets["①"] == ksets["②"] == ksets["③"]
            tag = "%s | %s" % (wname, vname)
            print("\n===== %s =====" % tag, flush=True)
            # ★ 첫 산출물 — 세 팔의 진입 수가 같아야 진행한다 (두뇌 세션 관문)
            print("%-26s %8s %8s %11s %10s %9s"
                  % ("팔", "진입", "확정", "ambiguous", "미결착소멸", "미결착끝"), flush=True)
            gate = {}
            for a in ARMS:
                s2 = summarize(arms[a])
                conf = s2["n_target"] + s2["n_stop"] + s2["n_both"]
                amb = len(keys) - len(arms[a])
                gate[a] = {"n_entry": len(arms[a]), "n_confirmed": conf,
                           "n_ambiguous": amb,
                           "n_unres_van": s2["n_unres_van"] + s2["n_liquidate"],
                           "n_unres_win": s2["n_unres_win"]}
                print("%-26s %8d %8d %11d %10d %9d"
                      % (ARM_LABEL[a], len(arms[a]), conf, amb,
                         gate[a]["n_unres_van"], s2["n_unres_win"]), flush=True)
            print("표본 동일? %s (유니버스 %d)" % ("예" if same else "아니오", len(keys)),
                  flush=True)

            summ = {a: summarize(arms[a]) for a in ARMS}
            yearly = {a: {y: summarize([t for t in arms[a] if t["year"] == y])
                          for y in YEARS} for a in ARMS}
            print("%-8s %11s %11s %11s |%9s" % ("연도", "①현행", "②목표만",
                                                "③끝까지", "n"), flush=True)
            for y in YEARS:
                print("%-8s %+10.2f%% %+10.2f%% %+10.2f%% |%9d"
                      % (y, yearly["①"][y]["mean_net"], yearly["②"][y]["mean_net"],
                         yearly["③"][y]["mean_net"], yearly["①"][y]["n"]), flush=True)
            print("%-8s %+10.2f%% %+10.2f%% %+10.2f%% |%9d"
                  % ("전체", summ["①"]["mean_net"], summ["②"]["mean_net"],
                     summ["③"]["mean_net"], summ["①"]["n"]), flush=True)
            for a in ARMS:
                s2 = summ[a]
                print("  %-24s 승률 %5.2f%% 본전 %5.2f%% 여유 %+5.2f%%p · 목표 %4d 손절 %4d "
                      "미결착 소멸 %3d/구간끝 %4d 정리매매 %3d · 보유일 중앙 %s"
                      % (ARM_LABEL[a], s2["win_rate"], s2["breakeven"], s2["edge"],
                         s2["n_target"], s2["n_stop"], s2["n_unres_van"],
                         s2["n_unres_win"], s2["n_liquidate"], s2["median_days"]),
                      flush=True)

            pairs = {}
            for pname, A, B in PAIRS:
                dy = {y: yearly[A][y]["mean_net"] - yearly[B][y]["mean_net"] for y in YEARS}
                signs = [1 if dy[y] > 0 else -1 for y in YEARS]
                pr = slot_sim.paired(arms[A], arms[B], n_runs=N_PAIR)
                pairs[pname] = {
                    "yearly_diff": dy, "signs": signs,
                    "all_diff": summ[A]["mean_net"] - summ[B]["mean_net"],
                    "six_year_sign_ok": all(x > 0 for x in signs),
                    "n_positive_years": sum(1 for x in signs if x > 0),
                    "slot5_paired": pr}
                print("  [%s] 전체 %+.2f%%p · 연도별 %s · 부호 %d/6 %s | 슬롯5 우세율 %.1f%% "
                      "차이중앙 %+.1f%%p"
                      % (pname, pairs[pname]["all_diff"],
                         " ".join("%+.2f" % dy[y] for y in YEARS),
                         pairs[pname]["n_positive_years"],
                         "(전부 +)" if pairs[pname]["six_year_sign_ok"] else "",
                         pr["win_rate_pct"], pr["diff_median"]), flush=True)

            slot = {}
            for a in ARMS:
                b = slot_sim.band(arms[a], n_runs=N_LEVEL)
                b5 = slot_sim.band(drop_top(arms[a]), n_runs=N_LEVEL)
                slot[a] = {"median": b["median"], "p5": b["p5"], "p95": b["p95"],
                           "median_drop5": b5["median"], "n_filled": b["n_filled"]}
                print("  슬롯5(참고) %-24s 중앙 %+7.1f%% (상위5제거 %+7.1f%%) "
                      "5~95%% %+7.1f~%+7.1f · 체결 %.0f"
                      % (ARM_LABEL[a], b["median"], b5["median"], b["p5"], b["p95"],
                         b["n_filled"]), flush=True)

            res["runs"][tag] = {"same_sample": same, "gate": gate,
                                "n": {a: len(arms[a]) for a in ARMS},
                                "summary": summ, "yearly": yearly,
                                "pairs": pairs, "slot5": slot}

    old, n_conf, dom = old_approx(P)
    res["old_maxdd_approx"] = {"n_confirmed": n_conf, "yearly": old, "domination": dom}
    print("\n[옛 근사는 정의상 항등식] 패 %d건 중 max_dd_pct > gain_at_resolve_pct 인 건 "
          "%d건 · 패 1건당 차이 평균 %.2f%%p · 패 비율 %.1f%% → 예상 차이 %.2f%%p"
          % (dom["n_loss"], dom["n_worse"], dom["mean_gap"], dom["loss_share"],
             dom["expected_diff"]), flush=True)
    for y in YEARS:
        o = old[y]
        print("  %s n=%4d  규칙 %+6.2f%%  무손절근사 %+6.2f%%  차이 %+6.2f%%p"
              % (y, o["n"], o["rule"], o["nostop"], o["diff"]), flush=True)

    (OUT / "14-stop-loss-recheck.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/14-stop-loss-recheck.json")


if __name__ == "__main__":
    main()
