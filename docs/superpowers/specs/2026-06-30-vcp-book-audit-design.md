# VCP 책 충실도 감사 (vcp-audit) — 설계 spec

작성일 2026-06-30 · 상태: 설계 승인됨, 구현 계획 대기

## 1. 배경·목적

find-vcp의 VCP 검출기(`evaluate_vcp`)가 미너비니 책의 VCP 규칙을 얼마나 충실히
구현하는지 **진단(감사)** 한다. 발단: 인텍플러스(064290)의 "돌파일 2026-02-05"가
음봉이고 피벗보다 +19% 위였음 → 검출기의 돌파 정의가 느슨함을 발견. 더 파보니
거래량 규칙도 책과 다름(아래 §3).

**검증 방식 = "차트 눈대조"가 아니라 "책 규칙을 숫자로 렌더링 → 사용자가 규칙에
비춰 판단".** (사용자는 책 규칙은 정확히 알지만 차트에서 VCP를 짚는 데는 자신이
없음 — 그래서 도구가 숫자로 풀어준다.)

**이번 범위 = 진단까지.** 검출기·find-vcp·find-vcp-history 무수정. 어떤 어긋남을
고칠지는 사용자가 성적표를 보고 결정 → *그다음* 별도 작업으로 `evaluate_vcp` 반영.

## 2. 책의 VCP 규칙 (사용자 정리 — 감사 기준)
1. 패턴 전 **주가 급상승(선행 급등)**.
2. 상승 멈추고 **조정/횡보**에 들어가며 **변동성 수축**.
3. 수축(T)이 **2~6회**, 갈수록 **얕아짐**.
4. **수축할 때마다 거래량이 점점 줄어듦**.
5. 차트 오른쪽에서 **거래량이 50일 이평선을 완전 하회("마름")** 가 1회 이상 → 매수 준비.
6. 마른 뒤 **거래량 터지며 피벗 상향 돌파**.

## 3. 현재 검출기와 책의 어긋남 (감사로 정량화할 대상)
(`scripts/canslim_lib/vcp.py` 확인)
| 책 규칙 | 현재 구현 | 어긋남 |
|---|---|---|
| 선행 급등 | 안 봄 | ✗ 미구현 |
| 수축 2~6·수렴 | count 2~6 + ×1.15 단조 | ≈ 부합 |
| 수축별 거래량 감소 | 안 봄(전/후반 1/3만 비교, line 155-158) | ✗ 미구현 |
| 거래량 마름 = 50일선 하회 | 후반<전반 평균(50일선 아님), 기준거래량=베이스 마지막 50일 평균(line 126) | ✗ 정의 다름 |
| 돌파 = 거래량 터지며 피벗 상향 | 종가>피벗 & 거래량≥1.4×베이스평균 (낡은 피벗·음봉허용·반복발화) | ✗ 느슨 |

## 4. 범위

### 하는 것
- **두 테스트 셋**을 감사:
  - **(정밀도) 검출기가 찾은 6종목** — `sepa-vcp-history.json`의 이벤트 보유 종목. "검출기 주장이 책에 맞나?"
  - **(재현율) 사용자 정답 예시 5개+** — *진짜 VCP라고 사용자가 확인한* 한국 종목 구간. "검출기가 진짜 VCP를 알아보나? 못 알아보면 어느 축에서 탈락?"
- 종목/예시마다 **책 5축 성적표**를 숫자로 렌더링 + 어긋남(✓/✗) 표시.
- 산출 `public/data/sepa-vcp-audit.json` + 콘솔 성적표.

### 안 하는 것
- 검출기·find-vcp·공유 파일 수정(읽기 전용 진단). 컷오프·자동 commit 없음.
- 임계값 자동 최적화. 매매 신호.

## 5. 데이터 로딩 (캐시 + FDR 2원화)
정답 예시는 **과거(2020 이전 등) 구간이라 캐시(최근 ~400영업일)에 없음.**
- `load_series(code, start=None, end=None) -> dict`:
  - start/end 없으면 → `ohlcv_matrix.get_series(code)` (캐시, 최근 6종목용).
  - start/end 있으면 → **FinanceDataReader**로 `[start−버퍼, end]` 일봉 fetch
    (버퍼 = 책5축에 필요한 50일MA+선행급등 lookback 확보 위해 start 이전 ~80영업일).
    FDR 수정주가는 우리 캐시 수정주가와 일치 검증됨(ohlcv_matrix.fill_recent_via_fdr 주석).
  - 반환 키: `dates, opens, highs, lows, closes, volumes` (audit가 쓰는 시계열).
- FDR는 KRX 공개데이터라 API 키 불필요. 네트워크 실패 시 그 예시만 skip+사유 기록.

## 6. 감사 알고리즘 — 책 5축 (베이스 구간 [b0..b1] 위에서)

베이스 구간:
- **예시**: 사용자가 준 기간(정답 베이스).
- **검출 6종목**: 검출 이벤트 확인일을 기준일로, `evaluate_vcp`와 동일 규칙
  (lookback 120일 내 최고 종가 지점 = b0, 기준일 = b1)으로 베이스 구간을 재계산.
  (`evaluate_vcp`는 베이스 인덱스를 반환하지 않으므로 audit가 같은 argmax 규칙으로 산출.)

거래량 기준선 = **거래량 50일 이동평균(trailing, rolling)** `ma50[i] = mean(vol[i-49..i])`.
모든 거래량 판정을 이 ma50 기준으로(책 정의).

| 축 | 산출 | 기본 통과조건(파라미터·튜닝 대상) |
|---|---|---|
| ① 선행급등 | adv% = (close[b0] / min(close[b0−60..b0]) − 1)×100, 기간 | adv ≥ `--min-advance`(기본 25%) |
| ② 수축 | zigzag→find_contractions 깊이 수열, 개수 | 2≤T≤6 AND 갈수록 얕음(×`--mono-tol` 1.15) |
| ③ 수축별 거래량 | 각 수축 구간 평균 vol / ma50(%) | 수축 진행하며 **감소** AND 후반 수축 < 100%(50일선 하회) |
| ④ 마른점 | 베이스 우측 min(vol/ma50)와 날짜 | min ≤ `--dry-max`(기본 0.7 = 50일선 30%+ 하회) |
| ⑤ 돌파 | 마른점 이후 피벗 상향일들: 각 날의 vol/ma50, 봉방향(종가>시가), 피벗연장(close−pivot)/pivot%, 첫돌파(전일종가≤피벗)? | "깨끗한 돌파" = 첫돌파 AND 양봉 AND vol/ma50 ≥ `--breakout-vol`(1.4) AND 연장 ≤ `--near`(5%) |

- ⑤에는 **현 검출기(V0)가 찍는 모든 날**과 **깨끗한 돌파 후보**를 같이 표기해 느슨함을 대비.
- 각 축에 `pass`(✓/✗) + `note`(한 줄). 통과조건 임계값은 전부 CLI 인자 — *정답 예시에
  맞춰 보정(calibrate)* 하는 게 이 감사의 목적.

**검출기 평결(별도 표기)**: 그 구간에서 `evaluate_vcp`가 `vcp_detected=true`를 냈는지,
`status=breakout`이 떴는지(예시=재현율, 6종목=확인). 책5축 ✓와 검출기 평결의
괴리가 곧 "고칠 지점".

## 7. 출력 스키마
`public/data/sepa-vcp-audit.json`:
```jsonc
{
  "generated_at": "2026-06-30 ...",
  "params": { "min_advance": 25, "mono_tol": 1.15, "dry_max": 0.7,
              "breakout_vol": 1.4, "near": 5, "vol_ma_window": 50 },
  "items": [
    {
      "code": "064290", "name": "인텍플러스", "source": "detector|example",
      "base_start": "2026-01-05", "base_end": "2026-02-05",
      "detector_verdict": { "vcp_detected": true, "breakout_days": ["..."] },
      "axes": {
        "prior_advance": { "value_pct": 0, "days": 0, "pass": true, "note": "..." },
        "contractions": { "depths": [25.0, 13.0, 7.0], "count": 3, "shrinking": true, "pass": true },
        "contraction_volumes": { "per": [ {"depth":25.0,"vol_vs_ma50_pct":90}, ... ],
                                 "decreasing": false, "pass": false, "note": "..." },
        "dry_point": { "min_vol_vs_ma50_pct": 0, "date": "...", "pass": false },
        "breakout": { "pivot": 0, "detector_flags": ["..."], "clean_candidates": [
            {"date":"...","vol_vs_ma50_pct":0,"up_candle":true,"extension_pct":0,"first_cross":true} ],
          "pass": false, "note": "검출기는 음봉·피벗+19%에서 발화" }
      }
    }
  ],
  "summary": { "n_items": 0, "axis_pass_counts": { "prior_advance": 0, "contractions": 0,
               "contraction_volumes": 0, "dry_point": 0, "breakout": 0 } }
}
```
- `items`는 입력 전부 포함(FDR 실패/데이터 부족은 `note`와 함께).
- 콘솔: 종목별 5축 ✓/✗ 한 줄 요약 + 어긋남 많은 축 집계.

## 8. 구성 요소
- **`scripts/canslim_lib/vcp_audit.py`** (순수·테스트 가능, FDR 로더 포함):
  `load_series`, `volume_ma`, `audit_prior_advance`, `audit_contractions`(zigzag/find_contractions 재사용),
  `audit_contraction_volumes`, `audit_dry_point`, `audit_breakout`, `audit_item(...)`.
  베이스·피벗·수축·검출기 평결은 기존 `evaluate_vcp`/`zigzag`/`find_contractions` 재사용.
- **`scripts/screen_vcp_audit.py`** (CLI): 6종목(history) + 예시파일 입력 → audit → JSON + 콘솔.
- **예시 입력**: `public/data/vcp_examples.json` = `[{code,start,end,breakout_date?,pivot?,note?}]`
  (사용자가 5개+ 제공 → 구현 후 요청).
- (선택) `.claude/skills/vcp-audit/SKILL.md` — `/vcp-audit` 재실행용.

### CLI 인자
- `--examples public/data/vcp_examples.json`, `--codes`, `--history public/data/sepa-vcp-history.json`
- `--min-advance 25` `--dry-max 0.7` `--breakout-vol 1.4` `--near 5` `--mono-tol 1.15` `--vol-ma-window 50`
- `--out`, `--ticker`(단일 디버그)

## 9. 검증 계획
- `vcp_audit.py` 순수 함수 단위 테스트(합성 시계열):
  ① `volume_ma`가 trailing 50일 평균을 정확히 계산.
  ② `audit_prior_advance`가 저점→베이스시작 상승%·기간 정확.
  ③ `audit_dry_point`가 우측 min(vol/ma50)와 날짜를 정확히.
  ④ `audit_breakout`의 첫돌파·양봉·연장·vol/ma50 판정 정확.
  ⑤ 수축별 거래량 감소 판정 정확.
- FDR 로더는 네트워크 I/O라 통합 확인(실제 1종목 과거 구간 fetch 성공)로 검증.
- 실데이터: 6종목 + (제공 시)예시 풀런 → 성적표가 합리적이고 §3 어긋남이 숫자로 드러나는지.

## 10. 미해결/후속
- 임계값(min-advance·dry-max 등)을 **정답 예시에 맞춰 보정** → 그 보정값으로 검출기 개선이 다음 단계 spec.
- 검출기 실제 수정(거래량 50일선 기준·선행급등·수축별거래량·돌파 엄격화)은 이 감사 결과를 근거로 별도 진행.
- 예시가 너무 과거라 FDR 결손이면 대체 소스(네이버 과거 일봉) 검토 — 필요 시.
