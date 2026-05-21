"""교차 사이클 집계 — 전 시대 한국식 CAN SLIM 근거 누적.

research/oneil-model-book/cycles/*/model_book.json 전부 취합 → 사이클별 핵심
지표 비교표를 cross_cycle.md 로 *재생성*(덮어쓰기, 항상 최신 전 사이클 반영).
글자별 "확인된 사이클 수/신뢰도"도 산출. korea_canslim.md(큐레이션 v1)는
사람이 버전업할 때 참고하는 근거 — 자동 덮어쓰기 안 함(환각 금지).
"""
import json
import statistics as st
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book"
CYCLES = RESEARCH / "cycles"
OUT = RESEARCH / "cross_cycle.md"


def metrics(rows: list[dict]) -> dict:
    R = [r for r in rows if not r.get("error")]
    n = len(R)
    if not n:
        return {}

    def num(k):
        return [r[k] for r in R if isinstance(r.get(k), (int, float))]

    def pctge(c, base=None):
        b = base if base is not None else n
        return round(100 * sum(1 for r in R if c(r)) / b, 0) if b else None

    rs = num("rs_score")
    e1 = num("eps_yoy_q1_pct")
    bo_v = num("breakout_vol_vs_50d")
    bo_h = num("breakout_vs_prior_252d_high_pct")
    mr = [r.get("market_regime_at_pivot") for r in R if r.get("market_regime_at_pivot")]
    return {
        "N": n,
        "RS중앙": round(st.median(rs), 0) if rs else None,
        "RS≥80%": pctge(lambda r: isinstance(r.get("rs_score"), (int, float)) and r["rs_score"] >= 80),
        "상승장%": (round(100 * sum(1 for x in mr if x == "상승추세") / len(mr), 0) if mr else None),
        "직전분기EPS+%": pctge(lambda r: isinstance(r.get("eps_yoy_q1_pct"), (int, float)) and r["eps_yoy_q1_pct"] > 0),
        "EPS중앙%": round(st.median(e1), 0) if e1 else None,
        "pivot적자%": pctge(lambda r: r.get("per_at_pivot_approx") == "N/A(적자)"),
        "기관OR외인매수%": pctge(lambda r: (r.get("inst_net_60d") or 0) > 0 or (r.get("fgn_net_60d") or 0) > 0),
        "외인순매수%": pctge(lambda r: (r.get("fgn_net_60d") or 0) > 0),
        "최대주주≥30%": pctge(lambda r: isinstance(r.get("largest_holder_pct"), (int, float)) and r["largest_holder_pct"] >= 30),
        "원화약세%": pctge(lambda r: isinstance(r.get("krw_6m_change_pct"), (int, float)) and r["krw_6m_change_pct"] > 0),
        "무희석%": pctge(lambda r: r.get("share_dilution_1y_pct") == 0),
        "시총<1조%": pctge(lambda r: isinstance(r.get("market_cap_at_pivot_eok"), (int, float)) and r["market_cap_at_pivot_eok"] < 10000),
        "돌파일거래량중앙": round(st.median(bo_v), 1) if bo_v else None,
        "돌파일신고가중앙%": round(st.median(bo_h), 0) if bo_h else None,
    }


def main():
    cyc = {}
    for d in sorted(CYCLES.glob("c*/")):
        mb = d / "model_book.json"
        if mb.exists():
            try:
                rows = json.loads(mb.read_text(encoding="utf-8")).get("rows", [])
            except json.JSONDecodeError:
                continue
            m = metrics(rows)
            if m:
                cyc[d.name] = m
    if not cyc:
        print("교차 집계할 사이클 model_book 없음")
        return

    cols = list(next(iter(cyc.values())).keys())
    L = ["# 교차 사이클 비교 — 전 시대 한국식 CAN SLIM 근거",
         "",
         f"> {len(cyc)}개 사이클 model_book 자동 취합(`analyze_cross_cycle.py`). "
         "각 셀은 해당 사이클 위너의 폭발 직전 공통 수치. 데이터 결손 사이클은 "
         "해당 칸 공백(환각 금지). korea_canslim.md 버전업 시 이 표를 근거로.",
         "",
         "| 사이클 | " + " | ".join(cols) + " |",
         "|---|" + "---|" * len(cols)]
    for cid, m in cyc.items():
        L.append(f"| {cid} | " + " | ".join(
            ("" if m.get(c) is None else str(m.get(c))) for c in cols) + " |")

    # 글자별 사이클 일관성 (여러 사이클서 반복 확인 → 신뢰도)
    L += ["", "## 글자별 사이클 일관성 (≥60%를 '성립'으로 카운트)", ""]
    rules = {
        "M(상승장)": ("상승장%", 60), "L(RS≥80)": ("RS≥80%", 50),
        "I(기관/외인매수)": ("기관OR외인매수%", 60), "S(대주주≥30%)": ("최대주주≥30%", 50),
        "S(무희석)": ("무희석%", 50), "C(직전분기 EPS+)": ("직전분기EPS+%", 60),
        "A역(적자허용)": ("pivot적자%", 25), "+K(원화약세)": ("원화약세%", 60),
        "N(돌파일거래량≥1.5중앙)": ("돌파일거래량중앙", 1.5),
    }
    for name, (col, thr) in rules.items():
        ok = [cid for cid, m in cyc.items()
              if isinstance(m.get(col), (int, float)) and m[col] >= thr]
        L.append(f"- **{name}**: {len(ok)}/{len(cyc)} 사이클 성립 "
                 f"({', '.join(ok) if ok else '데이터 부족'})")
    L += ["", "→ 여러 사이클서 반복 성립할수록 한국식 CAN SLIM 해당 항목 신뢰도↑. "
          "엇갈리면 '국면 의존'으로 표기. korea_canslim.md 는 이 근거로만 버전업."]

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"cross_cycle.md 갱신: {len(cyc)}개 사이클 ({', '.join(cyc)})")


if __name__ == "__main__":
    main()
