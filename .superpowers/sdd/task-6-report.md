# Task 6 Report: 문서 동기화 (doc-logic-sync)

## 변경 사항

### 1. `.claude/skills/find-vcp/SKILL.md`

#### 변경 내용

**#1. 스펙 참조 업데이트**
- **이전**: `docs/superpowers/specs/2026-06-29-find-vcp-design.md`
- **이후**: `docs/superpowers/specs/2026-06-30-vcp-detector-v2-design.md`

**#2. 결과 확인 섹션 확장 (새 VCP 정의 명시)**

- **이전**:
  ```
  ## 결과 확인
  - `status_distribution` : breakout(돌파 중) · actionable(피벗 근접+거래량 마름) ·
    forming(형성 중) · failed(수렴 실패).
  - `actionable`/`breakout` 종목이 다음 단계(리스크·진입) 후보.
  ```

- **이후**:
  ```
  ## 결과 확인
  - **VCP 인식**: 적응형 ZigZag로 변동성 수축 연쇄를 탐지. 피벗(최소저항선) = 횡보 구간의 종가 천장.
  - **돌파(status)**: 첫돌파(전일 종가≤피벗, 당일 종가>피벗) + 양봉(종가>시가) + 거래량터짐(거래량≥50일선×1.4) + 피벗근접 동시 충족.
  - `status_distribution` : breakout(돌파 중) · actionable(피벗 근접+거래량 마름) ·
    forming(형성 중) · failed(수렴 실패).
  - `actionable`/`breakout` 종목이 다음 단계(리스크·진입) 후보.
  ```

### 2. `scripts/screen_vcp.py`

#### CLI 인자 help 텍스트 추가

**--zigzag-pct**:
```python
# 이전
ap.add_argument("--zigzag-pct", type=float, default=DEFAULT_PARAMS["zigzag_pct"])

# 이후
ap.add_argument("--zigzag-pct", type=float, default=DEFAULT_PARAMS["zigzag_pct"],
                help="(현재 미사용 — evaluate_vcp 재설계로 적응형 전환)")
```

**--max-final-depth**:
```python
# 이전
ap.add_argument("--max-final-depth", type=float, default=DEFAULT_PARAMS["max_final_depth"])

# 이후
ap.add_argument("--max-final-depth", type=float, default=DEFAULT_PARAMS["max_final_depth"],
                help="(현재 미사용 — evaluate_vcp 재설계로 적응형 전환)")
```

## 검증 결과

### 테스트 실행
```
$ python -m pytest tests/test_vcp.py -q
..............                                                           [100%]
14 passed in 0.03s
```

### 구문 확인
```
$ python -c "import ast; ast.parse(open('scripts/screen_vcp.py', encoding='utf-8').read()); print('syntax ok')"
syntax ok
```

## Commit

```
Commit: 3f19e57
Subject: docs(vcp): 검출기 재설계 문서 동기화 (find-vcp 스킬·CLI 표기)

Files changed:
  - .claude/skills/find-vcp/SKILL.md (+3 lines)
  - scripts/screen_vcp.py (+4 lines)
```

## 요약

- **SKILL.md**: 스펙 참조 날짜 업데이트 + 결과 확인 섹션에 새 VCP 인식·돌파 정의 추가 설명 (적응형 ZigZag·피벗 정의·거래량 기준·4조건 돌파)
- **screen_vcp.py**: --zigzag-pct/--max-final-depth 인자에 미사용 안내 문구 추가 (기존 인자 유지, 호출자 깨짐 방지)
- **검증**: 테스트 14/14 통과, 구문 오류 없음

---

## Final fix: anchor ceiling

### 변경 내용

**`scripts/canslim_lib/vcp.py`**

- FROM: `ceiling_seg = closes[bs:n - 1]`  (회복·돌파 바 포함 → 피벗 float)
- TO: `ceiling_seg = closes[bs:last_lo_idx + 1]`  (수축 구간 종료 저점까지만 → 피벗 고정)

`last_lo_idx = chain["last_lo_idx"]` 를 명시적으로 읽어 사용. 주석도 새 논리로 교체.

**`tests/test_vcp.py`**

`test_evaluate_vcp_above_ceiling_extended_not_breakout` 추가:
- c1(25% 수축)+c2(15% 수축) VCP 베이스 → 수축 구간 천장 100
- extended 5봉(101.5→107.5, 천장 위 연장) + bo_ext(109, 대량거래)
- 구 코드: pivot=107.5, closes[-2]=107.5 ≤ pivot(no-op) → breakout 오탐
- 신 코드: pivot=100(고정), closes[-2]=107.5 > pivot → first_cross=False → status=forming → entry_ready=False ✓
- assert `r["status"] != "breakout"` AND `r["entry_ready"] is False`

**`docs/superpowers/specs/2026-06-30-vcp-detector-v2-design.md` §4.1**

천장이 수축 구간(`base_start..last_contraction_low`)에 고정되며 회복·돌파 바 제외,
연장 오탐 차단 원리·트레이드오프 기술.

### 5예시 as-of 결과 (verbatim)

```
데브시스터즈 vcp= True status= forming pivot= 9380.0
한솔케미칼 vcp= True status= forming pivot= 284000.0
다올투자증권1차 vcp= True status= forming pivot= 4835.0
다올투자증권2차 vcp= True status= breakout pivot= 6340.0
켐트로스 vcp= True status= breakout pivot= 10200.0
```

**2/5 status=breakout** (다올2차·켐트로스). 나머지 3개는 `forming`:

| 종목 | pivot | closes[-2] | prev_le_pivot |
|---|---|---|---|
| 데브시스터즈 | 9380 | 9550 | False |
| 한솔케미칼 | 284000 | 296000 | False |
| 다올투자증권1차 | 4835 | 4880 | False |

원인: 회복이 수축 구간 천장을 이미 초과(수축 구간 최고가보다 회복 바 종가가 높아짐)하여
지정 breakout_date 전날 종가가 pivot 위에 있음 → 첫돌파 가드 False → forming.
태스크 지시에 따라 DONE_WITH_CONCERNS로 보고 (revert 하지 않음).

### 70종목 스크리너 결과

```
입력 70종목 | VCP 41 | 진입가능(entry_ready) 4 | breakout 1 · actionable 4 · forming 65 · failed 0
```

기가비스(436530): 리스트 미포함(스크리너 입력 파일에 없음).
entry_ready/breakout 모두 낮은 수준 유지 (거짓양성 폭증 없음).

### pytest 결과

```
15 passed in 0.05s
```

### base_vol_cap 결정

`vcp_audit.py:141`과 `screen_vcp_audit.py:38`에서 사용 중 → **제거 안 함(유지)**.

