"""200 위너 — CAN SLIM 최초 충족일 vs 최적 진입(best_entry) 격차.

질문: 한국식 CAN SLIM(대표 게이트 L+M+I)을 *만족한 뒤* 들어가는 게 각
종목 자체의 최적 진입 대비 얼마나 늦은가? (위너 궤적 내 시점 비교 →
대조군 불필요·전 200 사용 → "표본 작음" 우려 해소.)

축별 point-in-time 최초 충족일(저점 이후):
  L  종가 252d수익률 ≥ 전종목 80분위(주봉 thr80 미러)
  M  지수(코스피/코스닥) 50>200·상승 (idx_uptrend_by_date)
  I  L&M 동시충족 후보일에서 외인 or 기관 60일 순매수>0 (네이버 frgn)
  C  그 날 point-in-time 분기 EPS YoY>0 (DART pit_qkey+yoy_pct) — 개별 보고만
대표 CAN SLIM 충족일 = L&M 최초일에 I 충족 시 그 날. I 결손/미충족=절단.
환각 금지: 결손은 추정 안 함.

사용:  python analyze_canslim_vs_optimal.py [--limit 200]
"""
import argparse
import json
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cyclecfg  # noqa: E402
from analyze_gated_timing import idx_uptrend_by_date  # noqa: E402
from check_named_stocks import pit_qkey  # noqa: E402
from collect_variables import yoy_pct  # noqa: E402
from canslim_lib.fetch import resolve_corp_code, load_corp_code_map  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

DIR = cyclecfg.DIR
HIST = cyclecfg.RESEARCH / "analysis_history.md"


def med(xs):
    xs = sorted(x for x in xs if isinstance(x, (int, float)))
    return round(xs[len(xs) // 2], 1) if xs else None


def q(xs, p):
    xs = sorted(x for x in xs if isinstance(x, (int, float)))
    return round(xs[int(p * (len(xs) - 1))], 1) if xs else None


def nidx(d, dstr):
    """d(오름차순 날짜) 에서 <=dstr 인 마지막 인덱스."""
    cand = [k for k in range(len(d)) if d[k] <= dstr]
    return cand[-1] if cand else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    U = json.loads((DIR / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    mb = json.loads((DIR / "model_book.json").read_text(encoding="utf-8"))["rows"]
    bt = json.loads((DIR / "buy_timing_rows.json").read_text(encoding="utf-8"))
    btmap = {r["code"]: r for r in bt["rows"] if not r.get("error")}
    wf = json.loads((DIR / "winners_final.json").read_text(encoding="utf-8"))
    pkmap = {x["code"]: x for x in wf["winners"]}
    corp_map = load_corp_code_map()
    last_cache = U[list(U)[0]]["d"][-1]

    # ── L: 주봉 thr80 (analyze_gated_timing main() 인라인 미러) ───────
    any_d = U[list(U)[0]]["d"]
    grid = list(range(252, len(any_d), 5))
    thr80 = {}
    for gi in grid:
        gd = any_d[gi]
        rr = []
        for s in U.values():
            d, c = s.get("d"), s.get("c")
            if not d or not c:
                continue
            j = gi if (gi < len(d) and d[gi] == gd) else nidx(d, gd)
            if j is None or j < 252 or c[j - 252] <= 0:
                continue
            rr.append(c[j] / c[j - 252] - 1)
        rr.sort()
        thr80[gd] = rr[int(0.8 * (len(rr) - 1))] if rr else None
    gdates = sorted(thr80)

    def thr_at(ds):
        cand = [x for x in gdates if x <= ds]
        return thr80[cand[-1]] if cand else None

    ks = idx_uptrend_by_date("%5EKS11")
    kq = idx_uptrend_by_date("%5EKQ11")

    rows = mb[:args.limit]
    out = []
    cnt = {"joined": 0, "no_bt": 0, "no_px": 0, "L_never": 0, "M_never": 0,
           "I_missing": 0, "I_fail": 0, "C_missing": 0, "usable": 0}

    for i, m in enumerate(rows, 1):
        code, name, mkt = m["code"], m["name"], m["market"]
        print(f"  [{i}/{len(rows)}] {name}", file=sys.stderr)
        btr = btmap.get(code)
        if not btr or not btr.get("best_entry_date"):
            cnt["no_bt"] += 1
            continue
        s = U.get(code)
        if not s or len(s.get("c", [])) < 300:
            cnt["no_px"] += 1
            continue
        cnt["joined"] += 1
        d, c = s["d"], s["c"]
        ti = nidx(d, m["trough_date"])
        bi = nidx(d, btr["best_entry_date"])
        pkd = pkmap.get(code, {}).get("peak_date") or m.get("peak_date")
        pk = nidx(d, pkd)
        if ti is None or bi is None or pk is None:
            cnt["no_px"] += 1
            cnt["joined"] -= 1
            continue
        reg = ks if mkt == "KOSPI" else kq

        L_i = M_i = lm_i = None
        for x in range(max(ti, 252), len(c)):
            if c[x - 252] <= 0:
                continue
            th = thr_at(d[x])
            L_ok = th is not None and (c[x] / c[x - 252] - 1) >= th
            M_ok = bool(reg.get(d[x], False))
            if L_ok and L_i is None:
                L_i = x
            if M_ok and M_i is None:
                M_i = x
            if L_ok and M_ok and lm_i is None:
                lm_i = x
                break
        if L_i is None:
            cnt["L_never"] += 1
        if M_i is None:
            cnt["M_never"] += 1

        rec = {"code": code, "name": name, "market": mkt,
               "trough_date": m["trough_date"],
               "best_entry_date": btr["best_entry_date"],
               "best_idx_close": round(c[bi], 1),
               "L_first": d[L_i] if L_i is not None else None,
               "M_first": d[M_i] if M_i is not None else None,
               "L_lag_days": (L_i - bi) if L_i is not None else None,
               "M_lag_days": (M_i - bi) if M_i is not None else None}

        I_ok = C_ok = None
        cval = None
        if lm_i is not None:
            T = d[lm_i]
            rec["lm_first"] = T
            rec["lm_lag_days"] = lm_i - bi
            dgap = (_date.fromisoformat(last_cache) - _date.fromisoformat(T)).days
            pages = min(90, max(8, dgap // 28 + 6))
            try:
                fr = fetch_naver_org_flow(code, pages=pages, sleep_ms=180)
                sel = [r for r in fr if r["date"] <= T][:60]
                if len(sel) >= 30:
                    fg = sum(r.get("fgn_net") or 0 for r in sel)
                    og = sum(r.get("org_net") or 0 for r in sel)
                    I_ok = (fg > 0) or (og > 0)
                    rec["I_fgn60"], rec["I_org60"] = fg, og
            except Exception:
                pass
            cq = pit_qkey(T)
            if cq:
                corp = m.get("corp_code") or resolve_corp_code(code, corp_map)[0]
                if corp:
                    cval, csrc = yoy_pct(corp, cq, "eps", code)
                    rec["C_qkey"], rec["C_eps_yoy"], rec["C_src"] = cq, cval, csrc
                    if isinstance(cval, (int, float)):
                        C_ok = cval > 0
        rec["I_ok"], rec["C_ok"] = I_ok, C_ok

        # 대표 CAN SLIM 충족일 = L&M 최초 + 그 날 I 충족
        if lm_i is not None and I_ok is True:
            ci = lm_i
            rec["canslim_date"] = d[ci]
            rec["gap_days"] = ci - bi                  # 양수=충족이 늦음
            rec["price_premium_pct"] = round((c[ci] / c[bi] - 1) * 100, 1)
            r_best = c[pk] / c[bi] - 1
            r_cs = c[pk] / c[ci] - 1
            rec["residual_forgone_pp"] = round((r_best - r_cs) * 100, 1)
            rec["resid_at_best_pct"] = round(r_best * 100, 1)
            rec["resid_at_canslim_pct"] = round(r_cs * 100, 1)
            cnt["usable"] += 1
        else:
            rec["canslim_date"] = None
            if lm_i is None:
                rec["censor"] = "L&M 창내 미충족"
            elif I_ok is None:
                rec["censor"] = "I 결손(frgn 미도달 — 추정 안 함)"
                cnt["I_missing"] += 1
            else:
                rec["censor"] = "I 미충족(외인·기관 순매도)"
                cnt["I_fail"] += 1
            if lm_i is not None and C_ok is None:
                cnt["C_missing"] += 1
        out.append(rec)

    use = [r for r in out if r.get("gap_days") is not None]
    gd = [r["gap_days"] for r in use]
    pp = [r["price_premium_pct"] for r in use]
    rf = [r["residual_forgone_pp"] for r in use]

    # 구속축: 가장 늦게 켜진 축(대표 게이트 lm 기준 — L vs M 중 지연 큰 쪽)
    bind = {"L": 0, "M": 0, "동시": 0}
    for r in use:
        ll, ml = r.get("L_lag_days"), r.get("M_lag_days")
        if ll is None or ml is None:
            continue
        bind["L" if ll > ml else "M" if ml > ll else "동시"] += 1

    n = cnt["joined"]
    L = [f"[{cyclecfg.CYCLE_ID}] CAN SLIM 최초충족 vs 최적진입 — 위너 N={n}",
         f"(생성 {_date.today()}; 대표 게이트=L+M+I, C는 개별 보고)",
         "방법론: 위너 궤적 내 '그 종목 최적진입 vs CAN SLIM 최초충족' 시점",
         "비교 → 대조군 불필요. 양수 gap = 충족이 최적보다 늦음(가설지지).",
         "",
         f"조인 {n} | 사용가능(대표충족) {cnt['usable']} | "
         f"L 미도달 {cnt['L_never']} | M 미도달 {cnt['M_never']} | "
         f"I 결손 {cnt['I_missing']} | I 미충족 {cnt['I_fail']} | "
         f"buy_timing無 {cnt['no_bt']} | 시세부족 {cnt['no_px']}",
         "",
         "== 격차 (사용가능 N, 중앙 / Q1~Q3) ==",
         f"gap_days(최적→CAN SLIM 거래일) : {med(gd)} "
         f"({q(gd,.25)}~{q(gd,.75)})",
         f"  gap>0 비율 : {round(100*sum(1 for x in gd if x>0)/len(gd)) if gd else 0}% "
         f"| gap>20거래일(~1개월↑) : {round(100*sum(1 for x in gd if x>20)/len(gd)) if gd else 0}%",
         f"가격 프리미엄 %(충족가/최적가−1) : {med(pp)} "
         f"({q(pp,.25)}~{q(pp,.75)})",
         f"포기 잔존상승 pp(최적−충족) : {med(rf)} "
         f"({q(rf,.25)}~{q(rf,.75)})",
         f"  최적 잔존 중앙 {med([r['resid_at_best_pct'] for r in use])}% → "
         f"충족 잔존 중앙 {med([r['resid_at_canslim_pct'] for r in use])}%",
         "",
         f"== 구속축(어느 축이 더 늦게 켜져 지연 유발) ==",
         f"L 지연 우세 {bind['L']} | M 지연 우세 {bind['M']} | 동시 {bind['동시']}",
         f"  L_lag 중앙 {med([r.get('L_lag_days') for r in use])}거래일 | "
         f"M_lag 중앙 {med([r.get('M_lag_days') for r in use])}거래일",
         "",
         "== 정직한 한계 ==",
         "위너만(생존자)이나 '그 종목 자체 최적 대비 늦음'은 궤적 내 비교라",
         "대조군 불요. L=close-only 252d 백분위, I=네이버 frgn 깊이한계",
         "(결손 비임퓨트), C=DART. 사이클내 사후·상폐제외. I·C는 L&M",
         "최초일에서 평가(롤링 아님 — 문서화된 선택).",
         ]
    block = "\n".join(L)
    (DIR / f"_canslim_gap_N{n}.txt").write_text(block, encoding="utf-8")
    (DIR / "canslim_gap_rows.json").write_text(
        json.dumps({"cycle": cyclecfg.CYCLE_ID, "n": n, "counts": cnt,
                     "rows": out}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    with HIST.open("a", encoding="utf-8") as f:
        f.write(f"\n\n## CAN-SLIM vs 최적진입 [{cyclecfg.CYCLE_ID}] N={n}"
                f"\n\n```\n{block}\n```\n")
    print(f"saved: _canslim_gap_N{n}.txt + canslim_gap_rows.json "
          f"(usable {cnt['usable']}/{n})", file=sys.stderr)


if __name__ == "__main__":
    main()
