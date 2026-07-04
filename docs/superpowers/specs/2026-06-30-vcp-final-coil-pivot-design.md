# VCP 피벗 = 최종 타이트 코일 탐지 (설계 spec)

작성일 2026-06-30 · 상태: 구현 완료(feat/vcp-redesign), 5예시 3/5 돌파 — 사용자 승인(엄격 dry 게이트 유지) · 대상 브랜치 feat/vcp-redesign

## 1. 배경·목적

VCP 검출기 재설계(feat/vcp-redesign)는 **코일 게이트 적용 전 인식(vcp_detected) 5/5**를 달성했으나,
**돌파일 피벗이 3/5 forming**(데브시스터즈·한솔케미칼·다올1차). 원인: 현재 피벗 =
`max(closes[base_start:last_lo_idx+1])`(ZigZag 수축 구간 종가 최고)인데, 계단식 VCP의
**폭발 직전 타이트 코일**(예: 데브 Nov 18-27, ~2% 폭)은 적응형 ZigZag 임계 밑이라
수축으로 안 잡혀, 피벗이 *그 코일 천장(9,560)보다 낮은 이전 수축 고점*이 됨 →
회복이 일찍 넘어 forming.

**미너비니 표준([[vcp-best-practices]]): 피벗 = "마지막 *가장 타이트한* 수축의 고점".**
그 최종 코일은 *좁은 변동폭 AND 마른 거래량*이 동시인 구간으로 정의된다. 이 spec은
그 **최종 타이트 코일을 ZigZag와 별개로 직접 탐지**해 피벗을 그 고가로 잡고, 인식에도
최종 코일 존재를 요구한다.

## 2. 확정된 결정 (미너비니 기준)
- 최종 코일 = **좁은 변동폭 AND 마른 거래량**이 동시인 최근(돌파 직전) 구간. **피벗 = 코일 고가.**
- 인식 게이트에 **최종 타이트 코일 존재 필수** 추가(없으면 VCP 아님 — 연장 종목 자동 배제).
- 피벗=코일고가(고정), 돌파=거래량 터짐(첫돌파+양봉+근접 유지).
- in-place(feat/vcp-redesign 위), **반환 키 불변**. 성공선=5예시 돌파+70종목 가드.

## 3. 알고리즘

### 3.1 최종 타이트 코일 탐지 (신규 `detect_final_coil`)
입력: highs, lows, closes, vols, ma50, b1(현재 바 인덱스=n-1), params.
코일은 **현재 바 직전까지**의 구간(현재/돌파 바는 코일에서 제외 → 피벗이 돌파 전 고정 저항).
- 현재 바 직전 `b1-1`부터 **뒤로 누적**하며 다음을 만족하는 동안 코일에 포함:
  - **좁은 변동폭**: `(max(close in coil) − min(close in coil)) / max(close in coil) × 100 ≤ coil_tight_pct`
    (기본 ~12%, 점차 조여 최종 코일만; 튜닝).
  - **길이 상한**: 코일 길이 ≤ `coil_max_days`(기본 12) — "최근" 유지.
  - 위반 시 멈춤.
- **최소 길이**: 코일 길이 ≥ `coil_min_days`(기본 3; 책 "3~5일").
- **거래량 마름(동시 조건)**: 코일 평균 `mean(vols/ma50) ≤ coil_dry_max`(기본 0.95) —
  *한 바만 마른 게 아니라 코일 전반이 마른* 것(기존 dry_min 단일바 게이트의 느슨함 보강).
- 위 모두 만족 시 코일 확정: **`pivot = max(close in coil)`**(종가 기준 — 장중 스파이크 회피;
  사용자 주석 피벗과 정합 검증). 불만족이면 `None`.
- 반환: `{coil_start, coil_end(=b1-1), pivot, coil_len, coil_dry_mean, coil_range_pct}` 또는 None.

> 종가기반 vs 고가기반 피벗: 종가기반 채택(고가는 장중 스파이크에 오염; 한솔 8/13 사례).
> 5예시 검증 시 사용자 피벗(9,560/302,500/4,540…)과 어긋나면 plan서 재고.

### 3.2 인식 게이트 (evaluate_vcp)
`vcp_detected = (2≤T≤6 수축) AND (수축 net-수렴 depths[-1]<depths[0]) AND (최종 코일 존재)`.
- 기존 "우측 1/3 dry_min ≤ dry_max" 단일바 게이트 → **코일의 평균-마름(3.1)으로 대체**.
- 코일 None이면 `reason="no_tight_coil"`.

### 3.3 피벗·돌파
- `pivot_price = 코일 pivot`(고정). `_is_breakout`(기존: 첫돌파+양봉+거래량≥50선×breakout_vol_mult+
  시가 근접) 그대로 — 코일 피벗이 고정이라 첫돌파(전일종가≤피벗<당일종가)가 진짜 가드.
- status: breakout / failed / actionable / forming 기존 규칙 유지(피벗만 코일 피벗으로).
- entry_ready = vcp_detected AND status∈{breakout,actionable}.

### 3.4 as-of 동작
- 돌파일(b1=돌파): 코일=직전 타이트 구간, 피벗=코일 고가, 당일 거래량터짐 돌파 → breakout.
- 코일 형성중(현재가 코일 안): 피벗=현재까지 코일 고가, 미충족 → forming/actionable.
- 연장 종목: 직전에 타이트+마른 코일 없음 → detect_final_coil None → 인식 실패 → 돌파 없음(부동 문제 해소).

## 4. 반환 스키마
**기존 13키 불변**(vcp_detected, num_contractions, contractions, base_length_days, base_depth_pct,
pivot_price, pct_to_pivot, volume_dryup_ratio, tightness_pct, status, swings, reason, entry_ready).
코일 근거 필드 추가 가능(coil_len 등), 기존 키 제거·이름변경 금지. find-vcp/history/audit 그대로 읽음.

## 5. 구성 요소
- `scripts/canslim_lib/vcp.py`: 신규 `detect_final_coil(...)` + `evaluate_vcp` 수정
  (피벗·인식 게이트를 코일 기반으로). 기존 `find_contraction_chain`(수축연쇄·인식)·
  `adaptive_zigzag`·`_is_breakout`·`volume_ma`는 유지.
- `tests/test_vcp.py`: detect_final_coil 단위테스트(타이트+마른 코일→피벗=고가, 비타이트/안마름→None) +
  above-ceiling 회귀테스트 유지 + 5예시는 보정 태스크.
- 신규 파라미터 `coil_tight_pct(12.0)`·`coil_min_days(3)`·`coil_max_days(12)`·`coil_dry_max(0.95)`를
  DEFAULT_PARAMS에 추가. 기존 `dry_max(0.82)`는 코일 게이트로 대체되며 잔존(미사용/레거시 표기).

## 6. 성공·머지 기준 (실제 달성 결과)
- 5예시 중 **3/5** 돌파일 as-of vcp=True·status=breakout·피벗 근사 — 사용자 승인.
  - PASS(3): 데브시스터즈 194480 (pivot ~9,550 vs 9,560, −0.1%), 한솔케미칼 014680 (~297,000 vs 302,500, −1.8%),
    다올투자증권 2차 030210 (~6,080 vs 6,070, +0.2%).
  - UNMET(2, 구조적): 켐트로스 220260·다올투자증권 1차 030210 — §8 참조.
  - 메리츠 138040: 시작부터 제외(조용한 돌파·50MA 아래 진입으로 VCP 범위 밖).
- 70종목 회귀 가드: vcp 15→18(+3, dry_max 0.90→0.95), 비합리적 폭증 없음, 기가비스(420770) vcp_detected=False 유지.
- 19/단위테스트 통과. [[doc-logic-sync]] 따라 스펙·find-vcp 스킬 동기화 완료.

### 2026-07-04 갱신: MIK 오라클 편입 후 **6예시 중 4/6** 돌파 (`2026-07-04-vcp-mik-oracle-design.md`)
- PASS(4) = 위 3건 + **마이클스컴퍼니(MIK, 미국, 2014-11-06 돌파)**: 코일 피벗 18.33 vs 복원
  저항/매수점 18.50(−0.9%, ≤2% 기준 이내), status=breakout. MIK는 2014-06 IPO 종목이라
  50일 거래량선이 상장초기 고거래량에 부풀려져 있어, 실제 돌파거래량(MA50×1.06,
  "조용한 돌파"로 보임)이 기존 breakout_vol_mult 게이트를 통과 못 했다 — §8의
  `coil_breakout_vol_mult` OR-경로로 해결.
- UNMET(2)·범위밖(1)은 변동 없음(켐트로스·다올1차·메리츠) — MIK는 이들과 근본적으로
  다른 케이스(코일은 정상 인식·피벗 정확, 돌파거래량 판정 기준선만 문제)임을 §8에 기록.
- 70종목 회귀 재확인(coil_breakout_vol_mult 도입 후): breakout 1→3(+2, 신규 vcp_detected
  증가 아님 — 기존 vcp_detected 종목의 status만 actionable/forming→breakout으로 정정),
  vcp_count 16→16(불변). 기가비스(420770)는 이 변경으로 인한 breakout 전환 없음(변경
  전후 동일하게 vcp_detected=True/status=forming) — 단, `vcp_detected=False` 유지라는
  위 문장의 전제 자체가 이번 확인 시점(2026-07-04)에는 이미 성립하지 않았음(120일
  lookback 창 이동에 따른 사전 존재 드리프트, 이번 작업과 무관 — §8 참조).
- 22/단위테스트 통과(신규 3건 포함).

## 7. 검증 계획
- detect_final_coil 합성 단위테스트: ① 타이트+마른 코일 → 피벗=코일고가, ② 변동폭 큼 → None,
  ③ 거래량 안마름 → None, ④ 코일 너무 짧음 → None.
- 5예시 돌파일 as-of 재현(피벗 사용자 주석 대조).
- 70종목 find-vcp 재실행(분포·기가비스 점검).

## 8. 미해결/후속

### 확정 파라미터 (Task 3 보정 완료)
| 파라미터 | 확정값 | 비고 |
|---|---|---|
| `coil_tight_pct` | 12.0 | 5예시 보정 후 유지 |
| `coil_min_days` | 3 | 책 "3~5일" |
| `coil_max_days` | 12 | 25→12 단축: '최근 마른 구간'만 잡도록(25는 직전 고거래량 바 흡수→한솔 등 dry_mean 부풀림) |
| `coil_dry_max` | 0.95 | 0.90→0.95 소폭 완화: 데브 0.890 여유·소폭 완화, 기가비스 여전히 배제 |
| `dry_max` | 0.82 | 잔존·레거시(코일 게이트로 대체, 미사용) |
| `coil_breakout_vol_mult` | 1.5 | 2026-07-04 신규(MIK 보정). 돌파 거래량 확장 판정을 `vols[i] ≥ ma50×breakout_vol_mult(1.4)` **OR** `vols[i] ≥ 코일평균거래량×coil_breakout_vol_mult(1.5)` 중 하나로 완화. 근거: 미너비니의 실제 정의("거래량이 직전 dry-up 대비 확장")를 구현한 것으로, 마른 코일이 존재하는 **모든** 종목에 일반 적용된다(IPO·저유동주 한정 아님) — MIK(2014-06 IPO, 상장초기 고거래량이 50일선을 부풀려 MA50 기준으론 돌파가 "조용"해 보였던 사례)는 이 OR-경로가 필요함을 드러낸 **동기 사례**일 뿐, 적용 범위의 한계는 아니다. `coil=None`(기존 호출부) 시 (b) 경로는 비활성이라 기존 동작 완전 보존. **모니터링**: 70종목 세트만 확인됨(breakout 1→3, 전부 기존 인식 종목의 상태 전환, vcp_count 16→16) — 다음 전체 유니버스 find-vcp 실행 시 breakout 건수 변화를 관찰할 것. |

### 충족 못한 예시 (구조적 — 튜닝 여지 아님)
- **켐트로스 220260**: 돌파 직전 횡보 구간 거래량이 50일선 대비 약 1.0~1.4×(일부 바 2~3×) — "마른 코일" 정의를 충족하지 않음 → detect_final_coil=None → reason=no_tight_coil. 통과시키려면 dry_max≈1.4 이상 필요하나 연장 가짜양성(기가비스류)까지 허용해 게이트를 무력화함 → 엄격 dry 게이트 유지 결정.
- **다올투자증권 1차 030210**: 마찬가지로 횡보 거래량 고조(elevated) + 피벗 불일치(~4,880 vs 사용자 4,540, +7.5%). 구조적 불일치로 판단.
- 두 예시 모두 "dry 코일 없는 횡보" 패턴이므로 VCP 정의 자체에서 제외하는 것이 미너비니 기준에 부합.
- **MIK는 이 두 예시와 다른 케이스**(구분 필요): 켐트로스·다올1차는 횡보 거래량이
  애초에 마르지 않아 `detect_final_coil=None`(코일 자체 미탐지)인 *구조적 미인식*이지만,
  MIK는 코일이 정상 탐지되고(마른 구간 확정, 피벗=18.33 정확) **오직 돌파 당일 거래량이
  부풀려진 MA50 대비로만 낮게** 보였을 뿐인 *돌파 판정 기준선 문제*였다. 그래서 코일
  게이트를 건드리지 않고 돌파 거래량 게이트에 OR-경로(`coil_breakout_vol_mult`)만
  추가해 해결했다 — 켐트로스·다올1차의 "마른 코일 자체가 없음" 문제는 이 변경으로 풀리지
  않으며(의도된 것), 여전히 §8 상단 표의 엄격 dry 게이트 결정이 유효하다.
- 메리츠 138040은 이 논의와 무관 — 애초에 VCP 범위 밖(50MA 아래 진입)이라 코일 탐지
  대상이 아니다.

### 기가비스(420770) — 사전 존재 창-민감도 (2026-07-04 확인, 본 작업 무관)
2026-06-30 시점 기록은 기가비스 `vcp_detected=False` 유지였으나, 2026-07-04 재확인
시점에는 `vcp_detected=True`/`status=forming`으로 나타났다. 원인은 가격 캐시가
2026-06-30→07-03로 갱신되며 120일 lookback 창이 밀려 수축 패턴 형태(인식 게이트의
net-수렴 판정)가 바뀐 것으로 추정 — `coil_breakout_vol_mult` 도입(돌파 거래량 게이트)과는
무관하며, 도입 전/후 동일하게 `vcp_detected=True`/`status=forming`이라 이번 작업으로 인한
회귀는 아니다. 여전히 forming(돌파 아님)이라 즉시 거래 신호는 없으나, 인식 게이트의
윈도우 민감성으로 사용자에게 플래그.

### 후속
- ATR-1/3 지표(책)는 coil_range_pct로 근사; 정밀 ATR 게이트는 후속 가능.
- 머지 후 find-vcp 재실행·프로덕션 반영은 별도.
- 기가비스 인식 게이트의 창-민감도(위)는 이 spec 범위 밖 별도 조사 후보.

### 이력
- 2026-06-30: 최초 작성, 5예시 3/5 돌파 확정.
- 2026-07-04: MIK 6예시 편입 + 코일-기준선 돌파 OR-경로(`coil_breakout_vol_mult=1.5`) —
  6예시 중 4/6 PASS로 갱신(§6). `2026-07-04-vcp-mik-oracle-design.md` 참조.
