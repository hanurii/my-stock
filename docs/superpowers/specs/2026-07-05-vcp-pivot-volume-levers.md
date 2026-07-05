# VCP 견고화 — 피벗 거래량 두 레버 (레버 A 포팅 + 레버 B 신규)

작성일 2026-07-05 · 상태: 구현·검증 완료 · 대상 브랜치 feat/stocks-sepa-page

## 1. 배경

미너비니 책 발췌(마이클스 MIK 2014-11-06 매수 사례): "피벗 포인트가 제대로 형성될 경우
거래량이 수축되며 종종 평균보다 훨씬 낮아진다. 가장 오른쪽 수축 구간에서는 50일 평균
거래량보다 낮고, **하루 이틀 정도는 극도로 거래량이 낮은 것이 좋다.**" → 피벗의 거래량
서명(dry-up)이 VCP의 핵심.

현행 검출기(feat/stocks-sepa-page)를 MIK 오라클(`public/data/vcp_oracle_mik.json`,
Tiingo 복원)로 as-of 검증한 결과 두 갭이 드러났다:
1. **돌파일 오분류**: 인식·피벗은 정확(vcp=True, 피벗 18.33 vs 책 18.50, −0.9%)한데 돌파일
   status가 `forming`. 원인 = 돌파 거래량(663,891)이 `MA50×1.4`(873,734) 미달. **MA50이
   IPO 직후 대량거래에 오염돼 부풀림** — 마른 코일 평균(363,263) 대비로는 1.83× 진짜 확장.
2. **극저거래량일 미사용**: MIK 코일에 실재하는 극저일(10-27 = 0.11×MA50)을 검출기가 인식
   기준으로 쓰지 않음. 코일 **평균** 마름(`coil_dry_max`)만 검사.

## 2. 확정된 결정

- **레버 A(포팅)**: 돌파 거래량 게이트에 마른-코일 기준선 OR-경로 추가. 이미 `feat/vcp-redesign`
  에 구현된 것을 현행 SEPA 브랜치로 포팅(오라클 데이터·테스트·`_SERIES_KEYS` opens 수정 포함).
- **레버 B(신규)**: 코일에 극저거래량일 ≥1일 요구. 임계값 `coil_extreme_dry_max=0.5`
  (사용자 승인 — 한국 유니버스 실측상 신호 종목 최저일이 0.2~0.6대라 MIK의 0.11을 그대로
  쓰면 현재 신호 대부분 탈락. 0.5는 돌파 2건 보존 + 진짜 마름일 없는 3건만 탈락).
- `coil_min_dry` 진단 필드를 출력에 상시 노출(게이트 실패 시에도).

## 3. 알고리즘

### 3.1 레버 A — `_is_breakout(closes, opens, vols, ma50, pivot, p, coil=None)`
거래량 확장 = `vols[i] ≥ MA50[i]×breakout_vol_mult(1.4)` **또는**
`vols[i] ≥ 코일평균거래량 × coil_breakout_vol_mult(1.5)`. 후자는 `coil` 인자가 있을 때만
활성(coil=None이면 기존 동작 보존). `base_v = mean(vols[coil_start:coil_end+1])`(원거래량
평균 = 확장 기준선; detect_final_coil의 dry_mean=vol/MA50 비율 평균과는 다른 지표).

### 3.2 레버 B — 코일 극저거래량일 게이트
- `detect_final_coil` 이 코일 최저일 비율 `coil_min_dry = min(vol/MA50 in coil)` 와
  극저일 수 `coil_extreme_days = #{ vol/MA50 ≤ coil_extreme_dry_max }` 를 반환(진단 산출만;
  게이트는 evaluate_vcp 에서 적용해 별도 reason 발화).
- `evaluate_vcp`: `cond_dry_day = coil and coil["coil_extreme_days"] ≥ coil_extreme_min_days(1)`.
  - `cond_dry_day` 실패 시 → `coil_valid=None` → 피벗 무효(돌파 불가), `vcp_detected=False`,
    `reason="no_dry_coil_day"`. `coil_min_dry` 진단은 계속 노출(왜 걸렸는지 가시화).
  - `vcp_detected = cond_count AND cond_mono AND cond_converge AND cond_coil AND cond_dry_day`.

### 3.3 방어(포팅 부수)
- `vcp_history._SERIES_KEYS` 에 `opens` 추가 → replay as-of 슬라이스가 opens 를 통과.
- `_is_breakout` 에 `if i >= len(opens): return False` 가드 — opens 누락 입력(일부 replay)에서
  IndexError 방지.

## 4. 반환 스키마
기존 키 전부 보존 + 신규 진단 키 `coil_min_dry` 1개 추가(가산). find-vcp/history/audit 그대로 읽음.

## 5. 파라미터 (DEFAULT_PARAMS 추가)
| 파라미터 | 값 | 의미 |
|---|---|---|
| `coil_breakout_vol_mult` | 1.5 | 레버 A — 돌파 거래량을 마른-코일 평균 대비로도 인정(IPO/저유동 MA50 오염 보정) |
| `coil_extreme_dry_max` | 0.5 | 레버 B — 코일 '진짜 마른 날' 거래량/MA50 상한 |
| `coil_extreme_min_days` | 1 | 레버 B — 극저거래량일 최소 일수(책 "최소 하루") |

## 6. 검증 결과
- **MIK 오라클**: as-of 2014-11-06 → vcp=True, **status=breakout**(레버 A), 피벗 18.33(−0.9%),
  coil_min_dry 0.11(레버 B 통과), entry_ready=True.
- **단위/통합 테스트 156 passed, 1 xfailed**. 신규 테스트: MIK 돌파 as-of, 코일 OR-경로 True/부족,
  detect_final_coil 진단(coil_min_dry/extreme_days), 레버 B 게이트 실데이터 토글(0.05→거절/기본→인정).
- **77종목 find-vcp 재실행**:
  - VCP 22→**16**(레버 B가 진짜 마름일 없는 6건 배제 — 책 "밋밋한 저볼륨" 회피와 정합).
  - status=breakout 2→**6**(레버 A OR-경로로 이수화학·BNK금융지주·나이스정보통신 3건 forming→breakout;
    +084870은 코일·돌파 있으나 1수축이라 vcp=False·entry_ready=False로 정상 필터).
  - entry_ready 11(전부 vcp_detected).

## 7. 구성 요소
- `scripts/canslim_lib/vcp.py`: DEFAULT_PARAMS(+3), `_is_breakout`(coil OR-경로+opens 가드),
  `detect_final_coil`(coil_min_dry·coil_extreme_days 산출), `evaluate_vcp`(레버 B 게이트·진단·reason).
- `scripts/canslim_lib/vcp_history.py`: `_SERIES_KEYS` +opens.
- `tests/test_vcp.py`(+6), `tests/test_vcp_history.py`(통합 테스트 코일형으로 갱신).
- `public/data/vcp_oracle_mik.json`, `scripts/_build_mik_oracle.py`(feat/vcp-redesign 에서 포팅).
- `.claude/skills/find-vcp/SKILL.md` 동기화([[doc-logic-sync]]).

## 8. 후속
- MIK 이외 상폐/저유동 예시로 레버 A OR-경로 일반화 추가 검증 가능.
- `coil_extreme_dry_max` 는 한국 유니버스 라벨 확보 시 재튜닝 여지(현 0.5는 실측 균형점).
- status ⊥ vcp_detected 디커플링(084870류)을 정리할지는 별건(기존 설계, 이번 범위 밖).
