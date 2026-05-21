"""표본(N)별 공통점 집계 — 영구 보존 (append-only).

model_book.json 을 읽어 핵심 공통점 지표를 산출하고:
  1) research/oneil-model-book/_agg_N{n}.txt  (해당 N 원시 스냅샷, 덮어쓰기)
  2) research/oneil-model-book/analysis_history.md 에 스냅샷 섹션 **append** (누적, 무손실)
CAN SLIM 미적용·해석 없음. 수치만. (해석은 사용자/별도 서술표)
"""
import json
import statistics as st
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cyclecfg  # noqa: E402

DIR = cyclecfg.DIR                         # 사이클별 산출
MB = DIR / "model_book.json"
HIST = cyclecfg.RESEARCH / "analysis_history.md"   # 전역(교차사이클) 누적


def main():
    d = json.loads(MB.read_text(encoding="utf-8"))
    R = [r for r in d["rows"] if not r.get("error")]
    n = len(R)

    def num(k):
        return [r[k] for r in R if isinstance(r.get(k), (int, float))]

    def cnt(c):
        return sum(1 for r in R if c(r))

    rs = num("rs_score")
    e1 = num("eps_yoy_q1_pct")
    nm = [r["net_margin_3y"][-1][1] for r in R if r.get("net_margin_3y")]
    nh = num("pivot_vs_prior_52w_high_pct")
    vs = num("pivot_volume_vs_50d_avg")
    io = num("inst_net_60d")
    fo = num("fgn_net_60d")
    lh = num("largest_holder_pct")
    kr = num("krw_6m_change_pct")
    di = num("share_dilution_1y_pct")
    yl = num("years_since_listing")
    mc = num("market_cap_at_pivot_eok")
    bo_v = num("breakout_vol_vs_50d")
    bo_h = num("breakout_vs_prior_252d_high_pct")

    def med(x):
        return round(st.median(x), 1) if x else None

    L = []
    P = L.append
    P(f"N={n}  (생성 {datetime.now().strftime('%Y-%m-%d %H:%M')}, 사이클 {d.get('cycle_start_date','?')}~)")
    P(f"RS: n={len(rs)} 중앙{med(rs)} >=90:{sum(1 for x in rs if x>=90)} "
      f">=80:{sum(1 for x in rs if x>=80)} <50:{sum(1 for x in rs if x<50)}")
    P(f"시장국면: {dict(Counter(r.get('market_regime_at_pivot') for r in R))}")
    P(f"직전분기 EPS YoY: n={len(e1)} 중앙{med(e1)}% 양수{sum(1 for x in e1 if x>0)} >100%:{sum(1 for x in e1 if x>100)}")
    P(f"EPS 4분기 가속: {cnt(lambda r: r.get('eps_accelerating'))}/{n}")
    P(f"pivot 적자(PER N/A적자): {cnt(lambda r: r.get('per_at_pivot_approx')=='N/A(적자)')}/{n} "
      f"| 이력부족: {cnt(lambda r: r.get('per_at_pivot_approx')=='N/A(이력부족)')}")
    P(f"최근 순이익률 음수: {sum(1 for x in nm if x<0)}/{len(nm)} 중앙{med(nm)}%")
    P(f"신고가대비 중앙{med(nh)}% >=100경신:{sum(1 for x in nh if x>=100)}")
    P(f"pivot거래량/50일 중앙{med(vs)} >=1.5:{sum(1 for x in vs if x>=1.5)}")
    P(f"base 길이중앙{med(num('base_len_days'))}일 깊이중앙{med(num('base_depth_pct'))}% "
      f"선행상승중앙{med(num('prior_uptrend_pct'))}%")
    P(f"기관 OR 외인 매수: {cnt(lambda r:(r.get('inst_net_60d') or 0)>0 or (r.get('fgn_net_60d') or 0)>0)}/{n} "
      f"| 외인>0:{sum(1 for x in fo if x>0)} | 외인매수&개인매도:"
      f"{cnt(lambda r:(r.get('fgn_net_60d') or 0)>0 and (r.get('indiv_net_60d_approx') or 0)<0)}")
    P(f"최대주주 중앙{med(lh)}% >=30:{sum(1 for x in lh if x>=30)} >=40:{sum(1 for x in lh if x>=40)}")
    P(f"원달러6M 중앙{med(kr)}% 약세>0:{sum(1 for x in kr if x>0)}/{len(kr)}")
    P(f"발행주식1y 무희석(0%):{sum(1 for x in di if x==0)} 증가>0:{sum(1 for x in di if x>0)} 중앙{med(di)}%")
    P(f"상장경과 중앙{med(yl)}년 <=5:{sum(1 for x in yl if x<=5)} <=10:{sum(1 for x in yl if x<=10)}")
    P(f"pivot시총 중앙{med(mc)}억 <5천억:{sum(1 for x in mc if x<5000)} <1조:{sum(1 for x in mc if x<10000)}")
    P(f"저점월: {dict(Counter(r['trough_date'][:7] for r in R))}")
    P(f"업종3 상위: {Counter(r.get('induty_group3') for r in R if r.get('induty_group3')).most_common(8)}")
    P(f"pivot방식 F/P: {dict(Counter(r.get('pivot_method') for r in R))}")
    P(f"RS basis: {dict(Counter(r.get('rs_basis') for r in R))}")
    if bo_v:
        P(f"[돌파일] 검출 {len(bo_v)}/{n} | 거래량/50일 중앙{med(bo_v)} >=1.5:"
          f"{sum(1 for x in bo_v if x>=1.5)} >=2:{sum(1 for x in bo_v if x>=2)} | "
          f"신고가대비 중앙{med(bo_h)}% >=100경신:{sum(1 for x in bo_h if x>=100)}")

    block = "\n".join(L)
    (DIR / f"_agg_N{n}.txt").write_text(block, encoding="utf-8")

    # analysis_history.md 에 append (무손실 누적)
    sec = f"\n\n## 자동 스냅샷 [{cyclecfg.CYCLE_ID}] N={n}\n\n```\n{block}\n```\n"
    with HIST.open("a", encoding="utf-8") as f:
        f.write(sec)
    print(f"N={n} 스냅샷 저장: _agg_N{n}.txt + analysis_history.md append")


if __name__ == "__main__":
    main()
