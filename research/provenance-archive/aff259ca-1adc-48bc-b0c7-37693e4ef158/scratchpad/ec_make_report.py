# -*- coding: utf-8 -*-
"""Render ec_report.md from ec_final.json."""
import json
from pathlib import Path

P = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad")
d = json.loads((P / "ec_final.json").read_text(encoding="utf-8"))
rows = d["rows"]
dist = d["distribution"]

L = []
L.append("# 실적 캘린더 92종목 Q2(2026.06) 실적 분류 리포트")
L.append("")
L.append("작성: 2026-08-17 · 대상: `sepa-earnings-calendar.json`(HEAD) byCode 92종목 · 지표: **영업이익**(억원, DART fnlttSinglAcnt)")
L.append("")
L.append("## 결론 (분포 요약)")
L.append("")
L.append("| 분류 | 개수 | 비고 |")
L.append("|---|---:|---|")
L.append(f"| 🔴 쇼크 | {dist['쇼크']} | 컨센 대비 −10% 이하 미스 |")
L.append(f"| 🟠 부진(YoY) | {dist['부진(YoY)']} | 비커버, H1 YoY −30% 이하 또는 적자전환 |")
L.append(f"| 🟢 서프라이즈 | {dist['서프라이즈']} | 컨센 대비 +10% 이상 |")
L.append(f"| 🟢 호실적(YoY) | {dist['호실적(YoY)']} | 비커버, H1 YoY +30% 이상 또는 흑자전환 |")
L.append(f"| ⚪ 부합 | {dist['부합']} | 컨센 ±10% 이내 |")
L.append(f"| ⚪ 무난(YoY) | {dist['무난(YoY)']} | 비커버, YoY ±30% 이내 |")
L.append(f"| ❔ 판정불가 | {dist['판정불가']} | 전년동기 결측 |")
n_cov = sum(1 for r in rows if r["method"] == "consensus")
L.append(f"| **합계** | **{len(rows)}** | 컨센 커버 {n_cov} / YoY 프록시 {len(rows)-n_cov} |")
L.append("")
neg = [r for r in rows if r["classification"] in ("쇼크", "부진(YoY)")]
pos_s = [r for r in rows if r["classification"] == "서프라이즈"]
L.append(f"- **쇼크 {dist['쇼크']}건**: " + ", ".join(f"{r['name']}({r['beat_pct']:+.1f}%)" for r in rows if r["classification"] == "쇼크"))
L.append(f"- **부진(YoY) {dist['부진(YoY)']}건**: " + ", ".join(
    f"{r['name']}({('%+.1f%%' % r['yoy_pct']) if r['yoy_pct'] is not None else r['yoy_case']})" for r in rows if r["classification"] == "부진(YoY)"))
L.append(f"- **서프라이즈 {dist['서프라이즈']}건**: " + ", ".join(f"{r['name']}({r['beat_pct']:+.0f}%)" for r in pos_s))
L.append("- 시장반응 정합(관측 61건 중 |±8%| 이상 큰 반응 발생 건): 일치 7건(주성엔지니어링·NHN·DL이앤씨·슈프리마·코스메카코리아·지오엘리먼트·심텍홀딩스), 불일치 1건(팬오션 호실적인데 익일 −9.8%), 중립 라벨(부합·무난)의 큰 반응 6건.")
L.append("")
L.append("## 판정 규칙 (원문 그대로)")
L.append("")
L.append("> - 컨센서스 커버 종목: beat% = (Q2 실제 영업이익 - 컨센서스)/|컨센서스|\\*100 → ≥+10% 서프라이즈, ≤-10% 쇼크, 사이 부합. 적자 실제 vs 흑자 컨센 → 쇼크; 흑자 실제 vs 적자 컨센 → 서프라이즈.")
L.append("> - 비커버 종목(컨센 없음): YoY 프록시 명시 라벨 — H1 영업이익 YoY ≥+30% 또는 흑자전환 → \"호실적(YoY)\", ≤-30% 또는 적자전환 → \"부진(YoY)\", 사이 → \"무난(YoY)\". 전년동기 결측이면 \"판정불가\".")
L.append("> - 시장 반응은 별도 열(검증용 corroboration): observable하고 day_ret ≤-8% 또는 ≥+8%면 라벨과 일치/불일치 표시.")
L.append("")
L.append("Q2 영업이익 = 반기누적(11012) − 1분기(11013), 원 단위 차감 후 억원 환산. YoY% 분모는 |전년동기 H1|.")
L.append("")
L.append("## 전체 표 (쇼크·부진 우선 정렬)")
L.append("")
L.append("| # | 종목 (코드) | 분류 | 근거 | Q2 영업이익(억) | 시장반응 [공시일·등락·relvol·관측] | 정합 |")
L.append("|---:|---|---|---|---:|---|---|")
for i, r in enumerate(rows, 1):
    ra = r["reaction"]
    if r["beat_pct"] is not None:
        basis = f"beat {r['beat_pct']:+.1f}% (컨센 {r['q2_op_consensus_eok']:,.0f}억)"
    elif r["yoy_pct"] is not None:
        tag = f"·{r['yoy_case']}" if r["yoy_case"] else ""
        basis = f"H1 YoY {r['yoy_pct']:+.1f}%{tag}"
    else:
        basis = r["yoy_case"] or (r["basis"] or "")
    q2 = f"{r['q2_op_actual_eok']:,.1f}" if r["q2_op_actual_eok"] is not None else "—"
    if ra["observable"]:
        rx = f"{ra['reveal_date'][5:]} {ra['reveal_kind']} → 익일({ra['reaction_date'][5:]}) {ra['day_ret_pct']:+.1f}% · rv{ra['relvol']:.1f} · 관측"
    else:
        sd = f" · 당일 {ra['day_ret_pct']:+.1f}%·rv{ra['relvol']:.1f}" if ra["day_ret_pct"] is not None else ""
        rx = f"{ra['reveal_date'][5:]} {ra['reveal_kind']} → 익일 8/18 미도래{sd}"
    corro = r["corroboration"]
    L.append(f"| {i} | {r['name']} ({r['code']}) | {r['classification']} | {basis} | {q2} | {rx} | {corro} |")
L.append("")
L.append("## 주의사항 (caveats)")
L.append("")
L.append("1. **컨센서스 커버리지 한계** — 92종목 중 컨센 존재 52종목뿐(네이버 모바일 finance/quarter의 FnGuide 컨센, `isConsensus=Y`). 35종목은 애널리스트 추정치 자체가 없어 YoY 프록시로 판정했고, 5종목(팬오션·지오엘리먼트·대원전선·저스템·광진실업)은 네이버가 이미 실제치로 덮어써 **발표 전 컨센을 복원할 수 없어** 비커버(YoY) 처리했다. 애널리스트 수(n_analysts)는 어떤 엔드포인트에도 없다. 또한 컨센 값은 2026-08-17 시점 스냅샷이라 발표 직전 컨센과 다를 수 있다(부합인데 당일 폭등한 삼성전기 +29.9%·코스맥스엔비티 +24.0%·네오팜 +13.9% 등은 이 괴리 또는 실적 외 재료 가능성).")
L.append("2. **8/14 제출분 반응 미관측** — 31종목(1/3)이 8/14(금) 공시라 익일 반응일(8/18 월)이 아직 오지 않았다. 이들의 시장반응 칸은 8/14 **당일** 수익률 참고치이며 정합 판정에서 제외(예: DN오토모티브 당일 +19.1%, 네오오토 당일 +20.2%·rv27.0 — 반기보고서 공시와 같은 날의 급등이라 인과는 미확정).")
L.append("3. **금융사 계정 매핑** — 보험·금융지주 6종목(신한지주·KB금융·하나금융지주·삼성화재·한화생명·코리안리)은 매출 계정이 '이자수익'으로 대체 매핑됐고, 현대해상은 fnlttSinglAcnt 손익계산서에 매출성 계정이 아예 없어 rev 결측(영업이익·순이익은 정상). 분류는 전부 **영업이익 기준**이라 영향 없음. 단 보험사 영업이익은 IFRS17 계정 특성상 제조업과 직접 비교 곤란.")
L.append("4. **연결 없음(OFS) 6종목** — 광주신세계·샘씨엔에스·네오팜·네오오토·타이거일렉·메가터치는 연결 미작성이라 개별 재무제표 기준. q1/h1 혼합(fs_div 불일치)은 0건.")
L.append("5. **부호 점검 7종목** — |Q2 영업이익| > H1 영업이익인 종목(주성엔지니어링·아이크래프트·광진실업·한성크린텍·주성코퍼레이션·제이에스링크·씨이랩)은 전부 Q1 적자 턴어라운드(3건) 또는 H1 자체 적자(4건)로 산술상 자연스러운 결과. 5개 무작위 종목 원본 캐시 재계산(q2=h1−q1)에서 전건 일치 확인.")
L.append("6. **극소 컨센 분모** — 한올바이오파마는 컨센 1억원이라 beat +5,500%가 산출됨(서프라이즈 자체는 유효하나 배율은 무의미).")
L.append("7. **적자지속 YoY 해석** — 씨이랩(−23.2억→−46.5억)처럼 양쪽 적자인 경우 |전년|을 분모로 한 증감률로 판정(손실 확대=부진). 흑자/적자 전환은 % 계산보다 우선 적용.")
L.append("8. **판정불가 0건** — 유일한 결측(현대해상 매출)도 영업이익은 완전해 전 92종목 판정 완료. F&F는 92명단에 없어 쇼크 앵커 점검은 해당 없음.")
L.append("")
L.append("### 자체 검증 요약")
L.append("- 무작위 5종목(제이에스링크·샘씨엔에스·한양이엔지·슈프리마·씨이랩) 원본 DART 캐시에서 q2=h1−q1 재계산 → **전건 일치**.")
L.append("- 앵커 ① 코리안리(보험): Q2 영업이익 1,750.5억 산출 확인, H1 YoY +78.4% → 호실적(YoY). 8/14 잠정 공시라 익일 반응 미관측(당일 +4.2%).")
L.append("- 앵커 ② DN오토모티브: 컨센 1,604억 vs 실제 2,054억 = beat +28.1% 서프라이즈. 8/14 반기보고서 **당일 +19.1%·rv4.8 관측**(익일 8/18 미도래) — '8/14 +20% 반응'은 당일 급등으로 확인됨.")
L.append("- 앵커 ③ F&F: 92명단에 **없음**(383220 부재) → 쇼크 분류 점검 대상 아님.")
L.append("")
L.append("데이터: `ec_final.json`(전 92행, 근거·플래그 포함). 원천: DART fnlttSinglAcnt(실제), 네이버/FnGuide(컨센), OHLCV 캐시(반응).")

(P / "ec_report.md").write_text("\n".join(L), encoding="utf-8")
print("wrote ec_report.md, lines:", len(L))
