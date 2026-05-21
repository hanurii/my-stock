"""[수익보호] 본전/이익보호 손절 규칙 EV — 문서가 자백한 미해결 구멍.

korea_exit_rules.md 가 인정한 빈칸: "+20% 못 가고 페이드 시 −15%까지
손해·수익 0"(살짝 올랐다 다 토해내는 경우). 사용자 질문 = "수익실현/
보호 규칙을 정해둬야 하지 않나?". 이 스크립트가 데이터로 답한다.

비교(같은 진입=pivot_close @ pivot_date, 앞으로 데이터끝까지):
  BASE     ③진입대비-15% 재해 + ④고점대비-20% 트레일 + ★약세
  BE@X     +X% 도달하면 손절선을 *본전(0%)* 으로 올림(그 외 BASE)
  LOCK@X→Y +X% 도달하면 손절선을 *+Y%* 로 올림(작은 이익 확정)
  SCALE@X  +X% 에서 *절반 익절*, 나머지는 BASE (보수 분기)

두 모집단에 동시 적용 →
  · 위너: 규칙이 *진짜 위너를 일찍 털어* EV 를 얼마나 깎나(비용)
  · 도플갱어(안오름 중 스크린통과=위너처럼 보였다 페이드): 페이드
    손실을 얼마나 막나(편익) — 사용자가 말한 바로 그 케이스
지표: 중앙·평균·최악10%·손실로끝난비율·상승폭포착률(capture).
*사후·종가·확률·2사이클·거래비용무관. 단순 조기익절은 위너 죽임이
이미 입증(+20% 정적매도 포착 8%) → 부분/조건부만 후보.*

사용: python scripts/oneil_model_book/analyze_profit_protect.py
      [--win c2024-12] [--ctl c2024-12-ctrl500] [--tag ""]
"""
import argparse
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import analyze_doppelganger as AD                       # noqa: E402

ROOT = HERE.parents[1]
CY = ROOT / "research" / "oneil-model-book" / "cycles"


def simulate(d, c, ei, e, kbear, hard=-0.15, trail=-0.20,
             be_at=None, lock_at=None, lock_floor=0.0,
             scale_at=None, scale_frac=0.5):
    """일반 출구 시뮬. 반환 (실현수익, 사유). 진입 e, ei=진입인덱스.
    BASE = hard(진입대비)·trail(고점대비). be_at/lock_at = 이익도달
    시 손절선 상향. scale_at = 절반 익절 후 잔여 BASE."""
    if ei is None or ei >= len(c) - 1 or e <= 0:
        return None
    peak = e
    realized = 0.0
    rem = 1.0
    why = "보유끝"
    for k in range(ei + 1, len(c)):
        x = c[k]
        peak = max(peak, x)
        g = x / e - 1
        gp = peak / e - 1
        # 부분 익절
        if scale_at is not None and rem == 1.0 and g >= scale_at:
            realized += scale_frac * g
            rem = 1.0 - scale_frac
        # 손절 바닥(진입대비): 기본 hard, 이익 도달 시 상향
        floor = hard
        if be_at is not None and gp >= be_at:
            floor = max(floor, 0.0)
        if lock_at is not None and gp >= lock_at:
            floor = max(floor, lock_floor)
        if g <= floor:
            return realized + rem * g, "손절/보호선"
        if x <= peak * (1 + trail):
            return realized + rem * (x / e - 1), "트레일"
        if kbear and kbear(d[k]):
            return realized + rem * (x / e - 1), "★약세"
    return realized + rem * (c[-1] / e - 1), why


VARIANTS = [
    ("BASE(-15재해/-20트레일)", {}),
    ("BE@+20(본전스톱)", {"be_at": 0.20}),
    ("BE@+30", {"be_at": 0.30}),
    ("BE@+50", {"be_at": 0.50}),
    ("LOCK@+30→+10", {"lock_at": 0.30, "lock_floor": 0.10}),
    ("LOCK@+50→+20", {"lock_at": 0.50, "lock_floor": 0.20}),
    ("SCALE@+25(절반익절)", {"scale_at": 0.25}),
]


def stat(v):
    if not v:
        return None
    s = sorted(v)

    def qq(f):
        return s[max(0, min(len(s) - 1, int(round(f * (len(s) - 1)))))]
    k = max(1, len(s) // 10)
    return {"n": len(v), "med": qq(.5), "mean": st.mean(v),
            "w10": sum(s[:k]) / k, "loss%": 100 * sum(1 for x in v if x < 0) / len(v)}


def run_pop(entries, pmap, kbear):
    """entries: [(code, pdate, e)] → 변형별 실현수익 리스트 + capture."""
    out = {nm: [] for nm, _ in VARIANTS}
    cap = {nm: [] for nm, _ in VARIANTS}
    for code, pdate, e in entries:
        s = pmap.get(code)
        if not s or not s.get("d") or not pdate or not e or e <= 0:
            continue
        d, c = s["d"], s["c"]
        ei = AD.nidx(d, pdate)
        if ei is None or ei >= len(c) - 1:
            continue
        peakret = max(c[ei:]) / e - 1
        for nm, kw in VARIANTS:
            r = simulate(d, c, ei, e, kbear, **kw)
            if r is None:
                continue
            out[nm].append(r[0] * 100)
            if peakret > 0.01:
                cap[nm].append(max(0.0, r[0]) / peakret * 100)
    return out, cap


def universe_faders(win, kbear):
    """전 유니버스에서 스크린통과(위너처럼) 후 −80%↓미회복/장기
    거래정지 = '샀는데 죽은' 실제 페이드. 보호규칙 *편익*의 진짜
    시험대(ctrl 표본은 너무 순함). 반환 [(code,buy_date,buy_px)]."""
    U = AD.pick_universe_file(win)
    if not U:
        return []
    anchor, cend = AD._cycle_window(win)
    grid, ref = AD.build_rs_grid(U, AD._shift_iso(anchor, -2), cend)
    wcodes = {r["code"] for r in AD.rows(win)}
    ents = []
    for code, s in U.items():
        if code in wcodes:
            continue
        d, c = s.get("d"), s.get("c")
        if not d or not c or len(c) < 254:
            continue
        q = AD.screen_first_qualify(d, c, anchor, cend, grid, ref, kbear)
        if isinstance(q, str):
            continue
        j, bd, bpx, pu, rp = q
        seg = c[j:]
        mdd = min(seg) / bpx - 1
        last = c[-1] / bpx - 1
        tail = c[-40:] if len(c) >= 40 else c
        if (mdd <= -0.80 and last <= -0.60) or \
           (len(set(tail)) <= 3 and last <= -0.30):
            ents.append((code, bd, bpx))
    return ents


def fmt(s):
    if not s:
        return "결손"
    return (f"중앙{s['med']:+.0f}% 평균{s['mean']:+.0f}% "
            f"최악10%{s['w10']:+.0f}% 손실끝{s['loss%']:.0f}% (n={s['n']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", default="c2024-12")
    ap.add_argument("--ctl", default="c2024-12-ctrl500")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    kbear = AD.build_kbear()
    W = AD.rows(a.win)
    Lo = AD.rows(a.ctl)
    wpx = AD.load_prices(a.win)
    lpx = AD.load_prices(a.ctl)

    def entries(rws):
        return [(r["code"], r.get("pivot_date"), AD.num(r.get("pivot_close")))
                for r in rws]

    # 도플갱어 = 안오름 중 스위트스폿(L+선행상승≥50) 통과(=위너처럼 보임)
    sweet = [AD.base_L, AD.F1]
    dop = [r for r in Lo if all(f(r) for f in sweet)]

    wout, wcap = run_pop(entries(W), wpx, kbear)
    dout, _ = run_pop(entries(dop), lpx, kbear)
    Upx = AD.pick_universe_file(a.win)
    fent = universe_faders(a.win, kbear)
    fout, _ = run_pop(fent, Upx, kbear)

    L = [f"[수익보호] 본전/이익보호 손절 EV [{a.win}] — "
         "문서 자백 구멍('+살짝 올랐다 페이드') 실측",
         f"위너 n={len(W)} · 도플갱어(안오름 중 스크린통과) n={len(dop)}",
         "진입=pivot_close. 같은 진입에 출구규칙만 바꿔 비교.",
         "*사후·종가·2사이클·거래비용무관. 단순 조기익절=위너 독 "
         "(이미 입증) → 부분/조건부만 시험.*",
         "=" * 70,
         "■ 위너에 적용 — 규칙이 *진짜 위너를 일찍 털어* 잃는 비용",
         "  변형 | 실현수익 분포 | 상승폭 포착률(중앙)"]
    base_w = stat(wout["BASE(-15재해/-20트레일)"])
    for nm, _ in VARIANTS:
        s = stat(wout[nm])
        cp = stat(wcap[nm])
        cpv = "결손" if not cp else f"{cp['med']:.0f}%"
        L.append(f"  {nm:22s} | {fmt(s)} | {cpv}")
    L += ["-" * 70,
          "■ 도플갱어(안오름 스크린통과·생존표본) — 참고용",
          "  변형 | 실현수익 분포"]
    for nm, _ in VARIANTS:
        L.append(f"  {nm:22s} | {fmt(stat(dout[nm]))}")
    L += ["-" * 70,
          f"■ ★사망/페이드 {len(fent)}종 (전 유니버스 통과後 −80%↓/정지) "
          "— 보호규칙 *진짜 편익* 시험대",
          "  변형 | 실현수익 분포"]
    for nm, _ in VARIANTS:
        L.append(f"  {nm:22s} | {fmt(stat(fout[nm]))}")

    # 핵심 요약: BASE 대비 위너 EV 손실 vs 도플갱어 최악10% 개선
    bw = base_w["mean"] if base_w else 0
    bf = stat(fout["BASE(-15재해/-20트레일)"])
    bfm = bf["mean"] if bf else 0
    L += ["-" * 70, "■ 트레이드오프 (BASE 대비 Δ) — 핵심",
          "  변형 | 위너 평균EV Δ(비용) | 사망/페이드 평균 Δ(편익)"]
    for nm, _ in VARIANTS:
        sw, sf = stat(wout[nm]), stat(fout[nm])
        if not sw or not sf:
            continue
        L.append(f"  {nm:22s} | {sw['mean']-bw:+.1f}%p | "
                 f"{sf['mean']-bfm:+.1f}%p")
    L += ["=" * 70,
          "해석: 위너 평균EV Δ가 음수 클수록 '진짜 위너를 일찍 죽임'",
          "(비용), 도플갱어 최악10% Δ가 양수 클수록 '페이드 손실 방어'",
          "(편익). 둘이 가장 좋은 균형 = 채택 후보. 단 위너 EV 훼손",
          "큰 변형은 +20% 정적매도(포착8%) 의 재판 — 경계.",
          "한계: 사후·종가·2사이클·거래비용/세금 무관·도플갱어는",
          "가격기반 스크린(I 결손·생존자 — 진짜 폐지 일부 누락)."]

    txt = "\n".join(L)
    out = ROOT / "research" / "oneil-model-book" / f"_profit_protect{a.tag}.txt"
    out.write_text(txt, encoding="utf-8")
    (CY / a.win / "profit_protect_rows.json").write_text(json.dumps(
        {"win": a.win, "winner": {k: stat(v) for k, v in wout.items()},
         "doppelganger": {k: stat(v) for k, v in dout.items()}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    hist = ROOT / "research" / "oneil-model-book" / "analysis_history.md"
    with hist.open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 수익보호 손절 EV [{a.win}] 위너{len(W)}\n\n"
                f"```\n{txt}\n```\n")
    print(f"saved: {out} (+profit_protect_rows.json, history append)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
