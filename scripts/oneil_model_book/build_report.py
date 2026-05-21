"""4단계 — 데이터셋 정리·제시. 해석·결론·CAN SLIM·미국 대조 없음.

위너·pivot·변수 행렬을 사람이 읽기 좋은 표 + 단순 기술통계(범위·중앙값) +
데이터 계보 흐름도(학습용, 평가 아님)로 REPORT.md 생성.
공통점 발굴은 사용자 본인 몫.
"""
import json
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cyclecfg  # noqa: E402
DIR = cyclecfg.DIR
MB = DIR / "model_book.json"
WF = DIR / "winners_final.json"
OUT = DIR / "REPORT.md"


def med_range(vals):
    v = [x for x in vals if isinstance(x, (int, float))]
    if not v:
        return "—"
    return f"중앙 {st.median(v):,.1f} / 범위 {min(v):,.1f} ~ {max(v):,.1f} (n={len(v)})"


def last(seq):
    return seq[-1][1] if seq else None


def main():
    mb = json.loads(MB.read_text(encoding="utf-8"))
    rows = [r for r in mb["rows"] if not r.get("error")]
    wf = {w["code"]: w for w in json.loads(WF.read_text(encoding="utf-8"))["winners"]}

    L = []
    A = L.append
    A("# 한국 시장 그레이트 위너 모델북 — 데이터셋")
    A("")
    A(f"생성 {mb['generated_at']} · 사이클 {cyclecfg.CYCLE_ID} "
      f"({cyclecfg.ANCHOR} ~ {cyclecfg.CYCLE_END}) · 위너 {len(rows)}종목 · "
      f"되돌림 허용폭 {int(mb['chosen_drawdown']*100)}%")
    A("")
    A("> **원칙**: 이 문서는 사후 최대 상승 종목의 *폭발 직전(pivot) 시점 raw 변수*만 "
      "모은 데이터셋입니다. CAN SLIM 분류·합격판정·미국 대조·결론을 일절 내지 않습니다. "
      "공통점 발굴·해석은 전적으로 독자(사용자)의 몫입니다.")
    A("")

    # 1. 위너 + pivot
    A("## 1. 위너 30 + 폭발 직전 시점(pivot)")
    A("")
    A("| # | 종목(코드) | 시장 | 유지배수 | 저점 | pivot | 직전2개분기 |")
    A("|--:|---|---|--:|---|---|---|")
    for i, r in enumerate(rows, 1):
        w = wf.get(r["code"], {})
        A(f"| {i} | {r['name']}({r['code']}) | {r['market']} | "
          f"{w.get('sustained_multiple','—')}배 | {r['trough_date']} | "
          f"{r['pivot_date']} ({r['pivot_method']}) | {r['prior_q1']}/{r['prior_q2']} |")
    A("")

    # 2. 실적·성장 (델·시스코 핵심 변수)
    A("## 2. 폭발 직전 실적 — 직전 2개 분기 순이익·매출 증가율 (DART 확정, point-in-time)")
    A("")
    A("델·시스코에서 오닐이 주목한 핵심 변수. q1=직전 분기, q2=그 전 분기. "
      "YoY 단위 %, 절대EPS 단위 원. YoY None은 신규상장 등 전년 동기 부재(절대값 참고).")
    A("")
    A("| 종목 | EPS YoY q1 | EPS YoY q2 | 절대EPS q1 | 절대EPS q2 | "
      "매출 YoY q1 | 매출 YoY q2 | 연간EPS 3y | ROE 3y(%) |")
    A("|---|--:|--:|--:|--:|--:|--:|---|--:|")

    def cell(v):
        return "—" if v is None else v
    for r in rows:
        ae = "→".join(f"{v:,.0f}" for _, v in (r.get("annual_eps_3y") or []))
        ro = "→".join(f"{v:.1f}" for _, v in (r.get("roe_3y") or []))
        A(f"| {r['name']} | {cell(r.get('eps_yoy_q1_pct'))} | {cell(r.get('eps_yoy_q2_pct'))} | "
          f"{cell(r.get('eps_q1_value'))} | {cell(r.get('eps_q2_value'))} | "
          f"{cell(r.get('sales_yoy_q1_pct'))} | {cell(r.get('sales_yoy_q2_pct'))} | "
          f"{ae or '—'} | {ro or '—'} |")
    A("")

    # 3. 밸류·수급·기술·공급
    A("## 3. pivot 시점 밸류에이션·수급·가격·공급")
    A("")
    A("PER 'N/A(적자)' = 적자라 PER 무의미(표준 관례). 적자여도 PBR·PSR은 산출 가능.")
    A("")
    A("| 종목 | PER(근사) | PBR(근사) | PSR(근사) | pivot시총(억) | 외인% pivot | "
      "외인 1y변화(%p) | 신고가대비(%) | 거래량/50일 | 발행주식수 |")
    A("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for r in rows:
        A(f"| {r['name']} | {r.get('per_at_pivot_approx','—')} | {r.get('pbr_at_pivot_approx','—')} | "
          f"{r.get('psr_at_pivot_approx','—')} | "
          f"{r.get('market_cap_at_pivot_eok','—')} | {r.get('foreign_foreign_pct_at_pivot','—')} | "
          f"{r.get('foreign_change_pp','—')} | {r.get('pivot_vs_prior_52w_high_pct','—')} | "
          f"{r.get('pivot_volume_vs_50d_avg','—')} | "
          f"{format(r['shares_outstanding'], ',') if r.get('shares_outstanding') else '—'} |")
    A("")

    # 4. 기업행위
    A("## 4. pivot 전후 6개월 자본 변동 공시 (DART)")
    A("")
    for r in rows:
        ca = r.get("capital_actions_around_pivot") or []
        A(f"- **{r['name']}**: " + ("; ".join(ca) if ca else "없음"))
    A("")

    # 4-A. 오닐 기술 핵심
    A("## 4-A. 오닐 기술 핵심 — RS·시장국면·base·유동성")
    A("")
    A("RS=pivot일 52주수익률 전종목 백분위(오닐 'L', 1~99). base 깊이=조정폭, "
      "선행상승=사이클 저점→base 시작.")
    A("")
    A("| 종목 | RS | 52주수익률% | 시장국면(M) | base길이(일) | base깊이% | "
      "선행상승% | pivot거래대금(억) | 50일평균(억) |")
    A("|---|--:|--:|---|--:|--:|--:|--:|--:|")
    for r in rows:
        A(f"| {r['name']} | {cell(r.get('rs_score'))} | {cell(r.get('rs_52w_return_pct'))} | "
          f"{cell(r.get('market_regime_at_pivot'))} | {cell(r.get('base_len_days'))} | "
          f"{cell(r.get('base_depth_pct'))} | {cell(r.get('prior_uptrend_pct'))} | "
          f"{cell(r.get('pivot_turnover_eok'))} | {cell(r.get('pivot_turnover_50d_avg_eok'))} |")
    A("")

    # 4-B. 오닐 펀더멘털 보강
    A("## 4-B. 오닐 펀더멘털 보강 — 순이익률·CFPS·최대주주·EPS가속")
    A("")
    A("CFPS=직전 회계연도 영업현금흐름÷발행주식수(같은 해 EPS와 비교). "
      "EPS가속=직전 4분기 YoY 증가율이 q1>q2>q3 (raw 판정, 합격선 아님).")
    A("")
    A("| 종목 | 순이익률 3y(%) | EPS YoY 4분기(최신→과거) | EPS가속 | "
      "최대주주지분% | CFPS(원) | 같은해 EPS(원) |")
    A("|---|---|---|:--:|--:|--:|--:|")
    for r in rows:
        nm3 = "→".join(f"{v:.1f}" for _, v in (r.get("net_margin_3y") or []))
        e4 = " ".join(f"{(v if v is not None else '—')}" for _, v in (r.get("eps_yoy_4q") or []))
        A(f"| {r['name']} | {nm3 or '—'} | {e4 or '—'} | "
          f"{'O' if r.get('eps_accelerating') else '·'} | "
          f"{cell(r.get('largest_holder_pct'))} | {cell(r.get('cfps_fy'))} | "
          f"{cell(r.get('eps_fy_for_cfps'))} |")
    A("")

    # 4-C. 신흥국 특화
    A("## 4-C. 신흥국 특화 — 환율·희석·지배구조·업종그룹")
    A("")
    A("희석=pivot 분기 vs 4분기 전 발행주식수 증가율. 그룹강도=같은 업종(표준산업"
      "분류 3자리) 위너 수. 설립경과/상장경과 병행(상장일은 data.go.kr 금융위, "
      "키 미승인 시 결손→설립경과 참고).")
    A("")
    A("| 종목 | 원/달러 pivot | 원달러 6M% | 희석 1y% | 지주사 | "
      "업종3 | 동업종 위너수 | 설립경과(년) | 상장경과(년) | 공매도잔고% |")
    A("|---|--:|--:|--:|:--:|---|--:|--:|--:|--:|")
    for r in rows:
        A(f"| {r['name']} | {cell(r.get('krw_at_pivot'))} | {cell(r.get('krw_6m_change_pct'))} | "
          f"{cell(r.get('share_dilution_1y_pct'))} | {'O' if r.get('holding_co_flag') else '·'} | "
          f"{cell(r.get('induty_group3'))} | {cell(r.get('sector_group_winner_count'))} | "
          f"{cell(r.get('years_since_establishment'))} | {cell(r.get('years_since_listing'))} | "
          f"{cell(r.get('short_balance_ratio_pct'))} |")
    A("")

    # 4-D. 오닐 'I' — 기관·외국인·개인 수급 (point-in-time)
    A("## 4-D. 오닐 'I' — 기관·외국인·개인 수급 (pivot 직전, point-in-time)")
    A("")
    A("finance.naver.com frgn 일별(2.4년 깊이)을 pivot 이전으로 필터한 직전 60영업일 "
      "누적 순매매(주). 개인=−(기관+외국인) 근사. (DART 5%룰 잉여라 제거 — frgn이 "
      "point-in-time 기관/외인 직접 제공.)")
    A("")
    A("| 종목 | 기준일 | 기관 60일 | 기관추세 | QoQ | 외국인 60일 | 외인추세 | "
      "개인 60일(근사) |")
    A("|---|---|--:|:--:|:--:|--:|:--:|--:|")
    for r in rows:
        A(f"| {r['name']} | {cell(r.get('supply_flow_asof'))} | {cell(r.get('inst_net_60d'))} | "
          f"{cell(r.get('inst_trend_60d'))} | {cell(r.get('inst_trend_qoq'))} | "
          f"{cell(r.get('fgn_net_60d'))} | {cell(r.get('fgn_trend_60d'))} | "
          f"{cell(r.get('indiv_net_60d_approx'))} |")
    A("")

    # 5. 단순 기술통계 (해석 아님)
    A("## 5. 변수별 단순 분포 (해석 아님 — 공통점은 직접 판단)")
    A("")
    fields = [
        ("직전분기 EPS YoY %", [r.get("eps_yoy_q1_pct") for r in rows]),
        ("전전분기 EPS YoY %", [r.get("eps_yoy_q2_pct") for r in rows]),
        ("직전분기 매출 YoY %", [r.get("sales_yoy_q1_pct") for r in rows]),
        ("최근 ROE %", [last(r.get("roe_3y")) for r in rows]),
        ("pivot PER(근사)", [r.get("per_at_pivot_approx") for r in rows]),
        ("pivot PBR(근사)", [r.get("pbr_at_pivot_approx") for r in rows]),
        ("pivot PSR(근사)", [r.get("psr_at_pivot_approx") for r in rows]),
        ("외인 1년 변화 %p", [r.get("foreign_change_pp") for r in rows]),
        ("pivot 신고가대비 %", [r.get("pivot_vs_prior_52w_high_pct") for r in rows]),
        ("pivot 거래량/50일평균", [r.get("pivot_volume_vs_50d_avg") for r in rows]),
        ("pivot 시총(억원)", [r.get("market_cap_at_pivot_eok") for r in rows]),
        ("RS 점수(1~99)", [r.get("rs_score") for r in rows]),
        ("pivot 52주수익률 %", [r.get("rs_52w_return_pct") for r in rows]),
        ("base 길이(일)", [r.get("base_len_days") for r in rows]),
        ("base 깊이 %", [r.get("base_depth_pct") for r in rows]),
        ("base 직전 선행상승 %", [r.get("prior_uptrend_pct") for r in rows]),
        ("최근 순이익률 %", [last(r.get("net_margin_3y")) for r in rows]),
        ("최대주주 지분율 %", [r.get("largest_holder_pct") for r in rows]),
        ("희석 1년 %", [r.get("share_dilution_1y_pct") for r in rows]),
        ("원/달러 6개월 변화 %", [r.get("krw_6m_change_pct") for r in rows]),
        ("설립 경과(년)", [r.get("years_since_establishment") for r in rows]),
        ("동업종 위너 수", [r.get("sector_group_winner_count") for r in rows]),
        ("기관 60일 누적순매매(주)", [r.get("inst_net_60d") for r in rows]),
        ("외국인 60일 누적순매매(주)", [r.get("fgn_net_60d") for r in rows]),
        ("개인 60일 누적(근사,주)", [r.get("indiv_net_60d_approx") for r in rows]),
        ("상장 경과(년)", [r.get("years_since_listing") for r in rows]),
        ("공매도 잔고 %", [r.get("short_balance_ratio_pct") for r in rows]),
    ]
    A("| 변수 | 분포 |")
    A("|---|---|")
    for nm, vs in fields:
        A(f"| {nm} | {med_range(vs)} |")
    A("")

    # 6. 데이터 계보 흐름도 (학습용)
    A("## 6. 데이터 계보 흐름도 (각 변수의 출처 — 학습용, 평가 아님)")
    A("")
    A("```")
    A("위너 선정      Yahoo 일봉(2y) ── 저점→고점 상승배수 ── 지속성 필터(유지율50%/60일)")
    A("                                        │")
    A("pivot 식별     Yahoo 일봉 ── 25일돌파+되돌림20%+본체2배 ──► pivot 일자")
    A("                                        │ (직전 2개 확정분기)")
    A("              ┌─────────────────────────┼───────────────────────────┐")
    A("실적·성장      DART fnlttSinglAcntAll    DART fnlttSinglAcntAll        Naver 연간")
    A("              분기 EPS/매출 YoY          Q4=연간−9M                   3y EPS/ROE/부채")
    A("수급('I')      finance.naver frgn 일별 기관·외인 순매매(2.4y, point-in-time)")
    A("              + Naver 외국인지분율 / DART 5%룰(현 스냅샷 참고)          ")
    A("가격·기술      Yahoo 일봉 ── 신고가 근접 / 거래량 급증                ")
    A("공급           DART stockTotqySttus 발행·유통주식수                   ")
    A("기업행위       DART list ── pivot±6M 증자·CB 공시                     ")
    A("밸류           pivot가 ÷ (TTM EPS / 최근 BPS) 근사                    ")
    A("RS('L')        compute_rs ── pivot일 52주수익률 전종목 백분위(1~99)    ")
    A("시장국면('M')  Yahoo 지수 2y ── pivot 시점 50/200일선 국면            ")
    A("펀더보강       Naver 순이익률 / DART 영업현금흐름÷주식수(CFPS)         ")
    A("공급·지배      DART hyslrSttus 최대주주지분 / stockTotqySttus 희석     ")
    A("분류           DART company induty_code(업종) / est_dt(설립경과)       ")
    A("상장일/공매도  data.go.kr 금융위 KRX상장종목정보·공매도(키 승인 필요)  ")
    A("신흥국         Yahoo KRW=X 환율국면 / 지주사플래그 / 테마(수동)         ")
    A("```")
    A("")
    A("## 7. 데이터 한계 (정직 명시)")
    A("")
    for k, v in mb["data_notes"].items():
        A(f"- **{k}**: {v}")
    A("- 기관·외국인·개인 수급: finance.naver frgn 일별로 **pivot 직전 60/120일 "
      "point-in-time 확보**(과거 '결손' 정정). 개인=−(기관+외인) 근사.")
    sb_ok = sum(1 for r in rows if r.get("short_balance_ratio_pct") is not None)
    ld_ok = sum(1 for r in rows if r.get("listing_date"))
    A(f"- 상장일: data.go.kr 금융위 수신 {ld_ok}/{len(rows)}건. 미수신은 키의 "
      "해당 데이터셋 활용신청 필요 → 결손 시 `years_since_establishment`(설립경과) 참고.")
    A(f"- 공매도 잔고: data.go.kr 수신 {sb_ok}/{len(rows)}건. 미수신은 데이터셋 "
      "활용신청 필요 → 결손(추정으로 채우지 않음).")
    A("- 테마/정책: `theme_manual`, 정성: `qualitative_memo` 사용자 기입란.")
    A("- 위너는 생존자 편향(오닐 방식 의도). 예측 스크리너 아님 — 사후 데이터 수집.")
    A("")
    A("### 결손 명세 (해당 변수만 null, 나머지 변수는 유효)")
    A("")
    eps_gap = [(r["name"], r["prior_q1"], r.get("eps_yoy_q1_src"))
               for r in rows if r.get("eps_yoy_q1_pct") is None]
    A(f"- 직전분기 EPS *증가율* 결손 {len(eps_gap)}건(절대 EPS 값은 표2 제공): " +
      ("; ".join(f"{n}({q})" for n, q, _ in eps_gap) or "없음"))
    null_sh = [r["name"] for r in rows if not r.get("shares_outstanding")]
    approx_sh = [r["name"] for r in rows
                 if r.get("shares_src") and "근사" in r["shares_src"]]
    A(f"- 발행주식수: 완전 결손 {len(null_sh)}건"
      f"({', '.join(null_sh) if null_sh else '없음'}); "
      f"DART 미제공 → Naver 시총÷현재가 근사 보강 {len(approx_sh)}건"
      f"({', '.join(approx_sh) if approx_sh else '없음'}, `shares_src`에 출처 표기).")
    per_na = sum(1 for r in rows if r.get("per_at_pivot_approx") == "N/A(적자)")
    per_hist = sum(1 for r in rows if r.get("per_at_pivot_approx") == "N/A(이력부족)")
    psr_ok = sum(1 for r in rows if r.get("psr_at_pivot_approx") is not None)
    A(f"- pivot 시점 PER: 'N/A(적자)' {per_na}건 = 적자라 PER 무의미(음수PER 미표기, "
      f"실제 관찰값). 'N/A(이력부족)' {per_hist}건 = 분모(4분기 EPS) 미확보(주로 진짜 신규상장).")
    A(f"- 적자 종목 밸류에이션 보완: **PSR**(시총÷최근4분기 매출) {psr_ok}/{len(rows)}건 산출, "
      "PBR과 함께 적자여도 사용 가능. 단 표준 '매출액' 라인이 모호한 바이오·지주·"
      "금융형은 매출 추출이 부정확할 수 있어 `psr_src`로 출처 표기(추정 아님).")
    A("- 결손 사유·출처는 `model_book.json` 의 `*_src` 필드에 종목별 기록. "
      "환각 금지 원칙상 추정값으로 채우지 않음(근사는 출처 명시).")
    A("")
    A("원천 데이터: `model_book.json` / `model_book.csv` / `winners_final.json` / `pivots.json`")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print("written", OUT)


if __name__ == "__main__":
    main()
