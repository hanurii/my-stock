"""[경로/고통] 위너 보유 여정 — 끝값이 아니라 *가는 길의 고통*.

문서·리포트는 위너의 *결과*(+376% 등)만 봤다. 사람은 그 길을
견뎌야 산다. 이 스크립트는 위너의 pivot(진입)→peak(고점) 경로에서:
 · MAE(진입대비 최대 역행)  = "내가 물려 있던 최대 깊이"
 · 최대 중간낙폭(달리는 고점대비) = "벌었다 토해낸 최대 폭"
 · 물밑(underwater) 최장일수 = "본전 밑에 잠겨 있던 최장 기간"
 · −20/−30/−40% 흔들림 횟수 = "도중에 몇 번 무서웠나"
 · −15% 재해손절·−8% 오닐손절이 *진짜 위너*를 몇 % 흔들어
   떨궜을까(= 손절규칙의 실제 비용, korea_exit_rules 직결)
 · 슈퍼위너 vs 소위너 — 큰 거일수록 더 아픈 길이었나

raw 분포만(등급·임의컷 없음)·결손은 결손대로·생존자(위너 전용
표본 — *그게 핵심*: 산 위너도 이만큼 아팠다)·사후·종가·2사이클.
근거 데이터: cycles/<win>/model_book.json + _universe_prices.json.
사용: python scripts/oneil_model_book/analyze_path_mae.py
      [--win c2024-12] [--tag ""]
"""
import argparse
import bisect
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CY = ROOT / "research" / "oneil-model-book" / "cycles"


def num(x):
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).replace("%", "").replace(",", ""))
    except ValueError:
        return None


def rows(cyc):
    p = CY / cyc / "model_book.json"
    return [r for r in json.loads(p.read_text(encoding="utf-8"))["rows"]
            if not r.get("error")]


def load_prices(cyc):
    for fn in ("_universe_prices.json", "_universe_prices_5y.json"):
        p = CY / cyc / fn
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


def nidx(d, ds):
    i = bisect.bisect_right(d, ds) - 1
    return i if i >= 0 else None


def q(v, f):
    if not v:
        return None
    s = sorted(v)
    return s[max(0, min(len(s) - 1, int(round(f * (len(s) - 1)))))]


def pct(v, lo):
    """v(음수 MAE list) 중 lo(예 −0.15) *이하로 빠진* 비율."""
    return (sum(1 for x in v if x <= lo) / len(v)) if v else None


def path_metrics(d, c, pdate, e, pkdate):
    """pivot(진입가 e)→peak 경로 지표. 반환 dict 또는 None(결손)."""
    if not pdate or not e or e <= 0:
        return None
    i = nidx(d, pdate)
    if i is None:
        return None
    j = nidx(d, pkdate) if pkdate else len(c) - 1
    if j is None or j <= i:
        j = len(c) - 1
    seg = c[i:j + 1]
    if len(seg) < 2:
        return None
    mae = min(seg) / e - 1                     # 진입대비 최대 역행
    run, max_dd = seg[0], 0.0                  # 달리는 고점대비 최대낙폭
    uw_cur = uw_max = 0
    for x in seg:
        run = max(run, x)
        max_dd = min(max_dd, x / run - 1)
        uw_cur = uw_cur + 1 if x < e else 0
        uw_max = max(uw_max, uw_cur)
    # 흔들림 횟수: 달리는 고점서 임계 이상 빠졌다 회복한 사건 수
    def shakes(thr):
        n, run2, armed = 0, seg[0], False
        for x in seg:
            run2 = max(run2, x)
            dd = x / run2 - 1
            if dd <= thr and not armed:
                n += 1
                armed = True
            if armed and x >= run2 * 0.97:     # 고점 근접 = 회복
                armed = False
        return n
    return {"mae": mae, "max_dd": max_dd, "uw_days": uw_max,
            "n_days": len(seg),
            "sh20": shakes(-0.20), "sh30": shakes(-0.30),
            "sh40": shakes(-0.40),
            "mult": max(seg) / e}                # 진입대비 고점배수


def summarize(rs, label):
    def col(k):
        return [r[k] for r in rs if r.get(k) is not None]
    mae = col("mae")
    dd = col("max_dd")
    uw = col("uw_days")
    mult = col("mult")
    L = [f"■ {label}  n={len(rs)}"]
    if not mae:
        return L + ["   (유효 경로 0 — 결손)"]
    L += [
        f"  MAE(진입대비 최대 물림): 중앙{q(mae,.5)*100:+.1f}% "
        f"(Q1{q(mae,.25)*100:+.1f}~Q3{q(mae,.75)*100:+.1f}) "
        f"최악{min(mae)*100:+.0f}%",
        f"   └ 진입후 한 번이라도: −8%↓ {pct(mae,-.08)*100:.0f}% · "
        f"−15%↓ {pct(mae,-.15)*100:.0f}% · −30%↓ {pct(mae,-.30)*100:.0f}% "
        f"· −50%↓ {pct(mae,-.50)*100:.0f}%",
        f"  최대 중간낙폭(벌었다 토해낸 폭): 중앙{q(dd,.5)*100:.1f}% "
        f"(Q1{q(dd,.25)*100:.1f}~Q3{q(dd,.75)*100:.1f}) 최악{min(dd)*100:.0f}%",
        f"  물밑(본전 밑 잠긴) 최장: 중앙{q(uw,.5):.0f}일 "
        f"(Q3{q(uw,.75):.0f}일) 최장{max(uw):.0f}일",
        f"  도중 흔들림 평균 횟수: −20%급 {st.mean(col('sh20')):.1f}회 · "
        f"−30%급 {st.mean(col('sh30')):.1f}회 · "
        f"−40%급 {st.mean(col('sh40')):.1f}회",
        f"  진입대비 고점배수: 중앙 ×{q(mult,.5):.1f} "
        f"(Q1×{q(mult,.25):.1f}~Q3×{q(mult,.75):.1f})",
    ]
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", default="c2024-12")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    W = rows(a.win)
    PX = load_prices(a.win)
    recs = []
    miss = 0
    for r in W:
        s = PX.get(r["code"])
        if not s or not s.get("d") or not s.get("c"):
            miss += 1
            continue
        m = path_metrics(s["d"], s["c"], r.get("pivot_date"),
                         num(r.get("pivot_close")), r.get("peak_date"))
        if m is None:
            miss += 1
            continue
        m["code"], m["name"] = r["code"], r.get("name")
        recs.append(m)

    L = [f"[경로/고통] 위너 보유 여정 [{a.win}] — 끝값 아닌 *가는 길*",
         f"위너 n={len(W)} · 유효경로 {len(recs)} · 결손 {miss} "
         "(가격/날짜 결손=추정 안 함)",
         "진입=pivot_close, 경로=pivot_date→peak_date. "
         "*사후·종가·위너전용표본(산 위너도 이만큼 아팠다)·2사이클.*",
         "=" * 68]
    L += summarize(recs, "전체 위너")

    # 슈퍼위너 vs 소위너 (진입대비 고점배수 3분위)
    sm = sorted(recs, key=lambda x: x["mult"])
    t = len(sm) // 3
    if t >= 3:
        L += ["-" * 68, "■ 크기별 — 큰 위너일수록 더 아픈 길이었나?"]
        for lab, grp in [("소위너(하위1/3)", sm[:t]),
                         ("중위너(중간1/3)", sm[t:2 * t]),
                         ("슈퍼위너(상위1/3)", sm[2 * t:])]:
            L += summarize(grp, lab)

    # 손절규칙의 실제 비용
    mae = [r["mae"] for r in recs if r.get("mae") is not None]
    if mae:
        L += ["-" * 68,
              "■ 손절규칙이 *진짜 위너*를 흔들어 떨군 비율 "
              "(MAE가 그 선 밑으로 내려간 위너 = 그 손절이면 탈락)",
              f"  −8%(오닐): {pct(mae,-.08)*100:.0f}% 탈락 → "
              "오닐 손절은 한국 위너 대부분을 죽임(korea_exit_rules 부합)",
              f"  −15%(시스템 재해): {pct(mae,-.15)*100:.0f}% 탈락 → "
              "이 비율이 −15%선의 *위너 손실 비용*(생존자 보정에서 "
              "전손 방어와 맞바꾼 대가)",
              f"  −20%: {pct(mae,-.20)*100:.0f}% · "
              f"−25%: {pct(mae,-.25)*100:.0f}%"]

    L += ["=" * 68,
          "해석: MAE −15%↓ 비율이 크면 시스템 −15% 손절이 *진짜 위너도*",
          "그만큼 잘라낸다는 뜻 — 도플갱어(전손방어)와의 trade-off 의",
          "위너側 비용. 물밑일수·흔들림횟수가 8주(≈40거래일)보다 길면",
          "'분기A 8주룰'·보수익절이 심리적으로 빡센 길임을 시사.",
          "한계: 사후·종가·위너전용(생존자 — 떨어진 위너 경로는 위너로",
          "안 잡힘)·일별·거래비용무관·2사이클·진입가=pivot_close 가정."]

    txt = "\n".join(L)
    out = ROOT / "research" / "oneil-model-book" / f"_path_mae{a.tag}.txt"
    out.write_text(txt, encoding="utf-8")
    (CY / a.win / "path_mae_rows.json").write_text(
        json.dumps({"win": a.win, "n": len(recs), "rows": recs},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    hist = ROOT / "research" / "oneil-model-book" / "analysis_history.md"
    with hist.open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 경로/고통 지표(MAE) [{a.win}] 위너{len(W)}\n\n"
                f"```\n{txt}\n```\n")
    print(f"saved: {out} (+path_mae_rows.json, analysis_history.md append)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
