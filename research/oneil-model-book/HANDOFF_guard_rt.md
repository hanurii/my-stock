# HANDOFF — 가드 포함 실시간 재현 (마이크로샤드 디스패치)

## 목적 (모든 세션 공통·필독)

가격신호만의 실시간 백테스트가 2사이클 모두 KOSPI(+18~19%)에
대패(CAGR −15~−17%). 두 가지 분리됨: ① 문서 "+90%·23.6x"는
*사후 pivot* 착시(확정) ② 거래량-조용·케이프·수급(I)·섹터무리
**가드를 유니버스 전체로 재현 못 함** → 진짜 edge 미검증.
이 작업 = 가드 전부 포함 + 무사후 실시간 재현 → **edge 있나/없나**
판가름. 결과 미리 알 수 없음. 판정 전 라이브 금지.

## 절대 규칙 (위반 금지)

환각 금지·결손은 결손대로(추정 금지)·look-ahead 차단·`scripts/
oneil_model_book/` 네이밍·`analysis_history.md` append-only·산출물
한계블록 필수. 작업폴더 `C:\Users\hanul\playground\my-stock`.
**수집기 3종은 이미 작성·검증됨**(아래) — 새 세션은 *실행 샤드*만.

## 수집기(완성) + 샤드 크기 (코드당 실측 기준)

| 패키지 | 스크립트 | 코드/속도 | 대상수 | ~12분 샤드 권장 |
|---|---|---|---|---|
| A 거래량 | `collect_volume.py` | ~1초 | c2024 2637·c2020 2199 | `--workers-total 4` (샤드 ~660종·~12분) |
| C 섹터 | `collect_sector.py` | ~0.6초 | 미보유 ~1942(합집합) | `--workers-total 3` (~650종·~7분) |
| B 수급 | `collect_flow_universe.py` | **~11초(병목)** | c2024 2637·c2020 2199 | `--workers-total 40` (~66종·~12분) |

> 더 잘게(=세션당 더 짧게) 원하면 workers-total 을 키우고 K 를
> 0..(total−1) 전부 돌리면 됨. 모든 수집기 멱등·재개·part파일 분리
> (충돌 없음). 끝나면 사이클별/패키지별 1회 `--reduce`.

## 의존 그래프

```
A(거래량)  C(섹터)        ← 지금 병렬 (필수)
B(수급)                  ← 선택/지연 가능(병목). 없으면 D 가 I=판정보류
   └──→ D(가드 스크린, A·C 후) → E(자본곡선 재실행) → F(통합·결론)
```
권장 경로: **A·C 먼저 전량 → D1(price+거래량+케이프+섹터)→E→F 로
1차 판정**. B(수급)는 그 후 D3 로 보강(I가드 추가) 재실행. B 를
기다리지 말 것(8시간+).

---

# 디스패치 — 새 Claude Code 창에 블록 그대로 붙여넣기

> 각 블록의 `K=` 만 본인 창 번호로 바꿔 실행. 한 창 = 한 샤드(~12분).
> 끝나면 맨 아래 `## 진행로그` 에 결과 한 줄 append.

## ◆ A 거래량 — c2024-12 (창 A0~A3, workers-total=4)

```
my-stock 레포. 아래 한 줄 실행 후 결과를 HANDOFF_guard_rt.md
## 진행로그 에 "A c2024 wK done: 수집N 결손M" 으로 append.
(K 를 0,1,2,3 중 본인 창 번호로)

PYTHONIOENCODING=utf-8 python scripts/oneil_model_book/collect_volume.py --cycle c2024-12 --worker K --workers-total 4

검증: 종료 로그의 '수집/결손' 수 확인. 에러 시 같은 명령 재실행
(멱등). 절대 다른 파일 건드리지 말 것.
```

## ◆ A 거래량 — c2020-03 (창 A4~A7, workers-total=4)

```
my-stock 레포. K=0,1,2,3 중 본인 번호.
PYTHONIOENCODING=utf-8 python scripts/oneil_model_book/collect_volume.py --cycle c2020-03 --worker K --workers-total 4
끝나면 진행로그 "A c2020 wK done: 수집N 결손M".
```

## ◆ A reduce (A 8창 모두 done 후, 1회·아무 창)

```
my-stock 레포. 두 줄 실행, 결과 진행로그에 "A reduce done: c2024 X종 / c2020 Y종".
PYTHONIOENCODING=utf-8 python scripts/oneil_model_book/collect_volume.py --cycle c2024-12 --reduce
PYTHONIOENCODING=utf-8 python scripts/oneil_model_book/collect_volume.py --cycle c2020-03 --reduce
```

## ◆ C 섹터 (창 C0~C2, workers-total=3)

```
my-stock 레포. K=0,1,2 중 본인 번호.
PYTHONIOENCODING=utf-8 python scripts/oneil_model_book/collect_sector.py --worker K --workers-total 3
끝나면 진행로그 "C wK done: 수집N 결손M".
```

## ◆ C reduce (C 3창 done 후, 1회)

```
my-stock 레포.
PYTHONIOENCODING=utf-8 python scripts/oneil_model_book/collect_sector.py --reduce
진행로그 "C reduce done: sector 총 N종".
```

## ◆ B 수급 — 선택/지연 (병목 8h+. 돌릴 거면 workers-total=40)

```
my-stock 레포. *선택*. K 를 0..39 중 본인 번호.
PYTHONIOENCODING=utf-8 python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --worker K --workers-total 40 --pages 30
끝나면 진행로그 "B c2024 wK done: 수집N 결손M(2010전 결손 정상)".
(c2020-03 분은 --cycle c2020-03 로 동일. 모두 끝나면
 --reduce 를 --cycle 별 1회.)
주의: 네이버는 최근구간 위주 — 오래된 구간 결손 정상. 추정 금지.
```

---

# D·E·F (수집 완료 후 — 각 단일 세션 ~15분)

## ◆ D 가드 스크린 평가기 (A·C reduce 완료 후)

```
my-stock 레포. screen_v11.py 의 가드를 실시간(no look-ahead) 함수로
구현: scripts/oneil_model_book/screen_rt.py.
입력: cycles/<cyc>/_universe_prices*(종가)·_universe_volume.json(A)·
 research/oneil-model-book/_universe_sector.json(C)·
 cycles/<cyc>/_universe_flow.json(B 있으면, 없으면 I=판정보류).
함수 screen_rt(code, prices, vol, sector, flow, asof_idx, rs_ref)
 → (통과?, 사유). 게이트 = analyze_equity_curve.py 의 가격게이트
 (RS≥80·선행상승≥50·≤88%고가·±10%50MA·추세확인신선·거래정지제외)
 + 거래량-조용(vol[asof] ≤ 1.2×50일평균)
 + 케이프형 신저점 절단(screen_v11 cape 로직, 가격만)
 + 섹터무리 가점(같은 induty 2+ 동시통과 = 랭킹 상향, 임의점수 금지)
 + I(flow 60일 외인 or 기관 >0; flow 결손 = '판정보류'=통과허용·플래그).
analyze_doppelganger 의 prior_up_at/rs_pct/build_rs_grid 재사용.
검증: 위너 model_book pivot일에 적용 → 통과율 *방향* 이 기존
 필드스크린과 일치(완전동일 아님 정상). 샘플5 사유 트레이스.
산출 _screen_rt_selftest.txt. 진행로그 "D done: 위너통과율X%·
 가드별탈락분포…".
한계: B결손→I판정보류로 과대통과 가능, 명시.
```

## ◆ E 자본곡선 재실행 (D 후)

```
my-stock 레포. analyze_equity_curve.py 복제 →
analyze_equity_curve_rt.py. 진입스크린만 screen_rt(D)로 교체,
거래량/섹터/수급 파일 로드 추가. 출구·비용0.66%·★스위치·trade
stats·KOSPI벤치·look-ahead차단 그대로. 실행: c2024-12·c2020-03.
산출 _equity_curve_rt*.txt + json + analysis_history append.
핵심표: '가격만(−17%)' vs '가드포함(신규)' vs 'KOSPI(+19%)' —
 CAGR·MDD·샤프·승률·평균체결. 진행로그 "E done: 가드포함 CAGR=__%,
 승률__% → edge 방향 __".
```

## ◆ F 통합·문서·결론 (E 후)

```
my-stock 레포. E 결과로 KOREA_SYSTEM_v1.md "⚠⚠ 최중대 한계" 절에
'가드포함 실시간 결과' 추가(수동)·korea_canslim/exit_rules 갱신·
memory equity-curve-hindsight-pivot.md 갱신(Yes/No 확정)·MEMORY.md
인덱스. 사용자용 평이한 1쪽 요약(가드 넣으니 살았나/죽었나+숫자+
라이브 가부). 진행로그 "F done: 결론=__".
```

---

## 진행로그 (완료 시 한 줄 append, 다른 세션이 의존성 판단)

- (메인) 수집기 3종 작성·검증 완료. A 부분 c2024 ~349종(reduce 흡수).
- A c2020 w0 done: 수집 474 결손 5 (collect_sector.py --worker 0 --workers-total 3, part0 → _universe_sector.part0.json, reduce 대기)
- A c2020 w1 done: 수집 478 결손 1 (collect_sector.py --worker 1 --workers-total 3, part1 → _universe_sector.part1.json, reduce 대기)
- A c2020 w2 done: 수집 471 결손 8 (collect_sector.py --worker 2 --workers-total 3, part2 → _universe_sector.part2.json, reduce 대기)
- A c2024 w0 done: 수집 659 결손 1 (collect_volume.py --cycle c2024-12 --worker 0 --workers-total 4, part0 → _universe_volume.part0.json, reduce 대기)
- A c2024 w1 done: 수집 653 결손 7 (collect_volume.py --cycle c2024-12 --worker 1 --workers-total 4, part1 → _universe_volume.part1.json, reduce 대기)
- A c2024 w3 done: 수집 655 결손 2 (collect_volume.py --cycle c2024-12 --worker 3 --workers-total 4, part3 → _universe_volume.part3.json, reduce 대기)
- A c2024 w2 done: 수집 657 결손 3 (collect_volume.py --cycle c2024-12 --worker 2 --workers-total 4, part2 → _universe_volume.part2.json, reduce 대기)
- A c2020 w1 done: 수집 547 결손 3 (collect_volume.py --cycle c2020-03 --worker 1 --workers-total 4, 550종, part1 → _universe_volume.part1.json, reduce 대기)
- A c2020 w2 done: 수집 545 결손 5 (collect_volume.py --cycle c2020-03 --worker 2 --workers-total 4, 550종, part2 → _universe_volume.part2.json, reduce 대기)
- A c2020 w0 done: 수집 547 결손 3 (collect_volume.py --cycle c2020-03 --worker 0 --workers-total 4, 550종, part0 → _universe_volume.part0.json, reduce 대기)
- A c2020 w3 done: 수집 541 결손 8 (collect_volume.py --cycle c2020-03 --worker 3 --workers-total 4, 549종, part3 → _universe_volume.part3.json, reduce 대기)
- A/C reduce done: 거래량 c2024 2624·c2020 2180 (99%), sector 2623종.
- D+E done (메인세션·통합): analyze_equity_curve_rt.py — 가드포함 실시간.
  c2024 CAGR -11%(가격만 -17%, KOSPI +19%), c2020 +10~15%(가격만 -15%,
  KOSPI +18%). 가드 기여 확정·장세의존. I(수급)=판정보류(B 미수집).
- F done: KOREA_SYSTEM_v1.md "후속" 절·memory·요약 반영. 결론=부분Yes·
  라이브 보류. 잔여 차기 = B(수급) 수집 후 D3 재실행.
- B done + D3 완결(2026-05-19): 수급 후보한정 수집(c2024 1217·c2020 737, 100%).
  I가드 = 단일 최대 가드: c2024 CAGR -11%→-3%(Δ+7.3%p). c2020 수급
  ~2023-11+ 라 2019~21 결손→I효과 측정불가(+10% 유지). 두 사이클 다
  KOSPI 미달 → 사후 pivot 착시 본질 *완결 확정*. 라이브 불가(확정).
  잔여=수급 장기수집(2020 커버)·다사이클 OOS. [전 작업 종료]
