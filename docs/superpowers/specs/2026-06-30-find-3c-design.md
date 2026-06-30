# find-3c — SEPA 패턴 스킬: 3C(Cup-Completion Cheat) 탐지 (설계 spec)

작성일 2026-06-30 · 상태: 설계 승인됨, 구현 계획 대기

## 1. 배경·목적

마크 미너비니 SEPA(Specific Entry Point Analysis)를 한국 시장에 적용하는
파이프라인의 **패턴 탐지 스킬**. `find-vcp`·`find-power-play`의 **형제 스킬**로,
같은 입력(트렌드 템플레이트 통과 종목)을 받아 미너비니의 또 다른 패턴인
**3C = Cup-Completion Cheat(컵 완성 치트)** 를 탐지한다.

3C(치트)는 컵 모양 바닥에서 **남보다 일찍, 옛 고점 한참 아래에서 사는 조기
진입** 기법이다. 전통적 컵앤핸들 피벗(컵 오른쪽 끝, 옛 고점 부근)까지 기다리지
않고, 컵 바닥에서 반등하는 **도중에 생긴 좁은 선반(shelf)** 을 거래량과 함께
뚫는 순간을 매수점으로 본다. 더 낮은 가격에 사서 **손절폭을 좁게** 가져가는 것이
핵심 이점이다.

미너비니는 치트를 4단계로 설명한다:

1. **하락(Downtrend)** — 주가가 흘러내리며 컵의 왼쪽 벽을 만든다.
2. **바닥(The Low)** — 더 안 빠지고 바닥에서 다지는 구간.
3. **반등(Uptrend)** — 바닥을 치고 오르기 시작(컵의 오른쪽 벽).
4. **치트 선반(Cheat area)** — 반등 도중 잠깐 멈춰 **좁은 횡보 선반**을 만들고,
   그 선반의 고점을 거래량 터지며 뚫는 순간이 조기 매수점.

### 방법론 선택 (의도적 결정)

`find-vcp`·`find-power-play`와 동일하게, "무엇을 찾는가"=미너비니 교과서,
"어떻게 숫자로 판정하나"=이 프로젝트의 공학적 번역이다. 사용자는 교과서에
충실한 기본값을 선택했고, 완화·강화가 필요하면 §6의 CLI 인자로 언제든 조정한다.

### 치트 위치 범위 (사용자 결정)

치트 선반은 **컵 깊이의 하단/중단(아래 2/3)** 에 있을 때만 인정한다(low/regular
cheat). 선반이 컵 윗부분(상단 1/3, 거의 핸들 위치)에 있으면 그건 일반
컵앤핸들 돌파이지 "치트(조기 진입)"가 아니므로 제외한다. 이 위치 게이트가
"옛 고점 한참 아래에서 일찍 산다"는 치트의 본질을 구현하는 결정적 조건이다.

## 2. 범위

### 하는 것
- 입력: `public/data/sepa-trend-candidates.json`의 `all_pass == true` 종목만 분석.
- 각 종목의 일봉(OHLCV 캐시)에서 3C(컵+치트 선반) 패턴을 탐지하고 지표·상태를 산출.
- 산출: `public/data/sepa-3c-candidates.json`.

### 안 하는 것
- VCP 베이스 탐지(`find-vcp`) · 파워 플레이(`find-power-play`) — 이번은 3C만.
- 수급(외인/기관 순매수) 신호 — VCP·파워플레이와 동일하게 OHLCV 거래량으로 충분.
- 실제 매매·손절·비중 신호 — 후보 좁히기까지. 리스크 규칙은 다음 단계.
- 공유 파일(`trend-template-candidates.json` 등) 갱신 — 항상 전용 출력 파일.
- 자동 git commit/push.

## 3. 데이터 입력

- **OHLCV 캐시**: 형제 스킬과 동일 소스(수정주가 일봉). 실행 전 `update-data`로
  최신화 권장(선행 스킬).
- **대상 종목 목록**: `sepa-trend-candidates.json`의 `candidates[]` 중 `all_pass`.
- 종목당 필요한 시계열: `dates`, `closes`, `highs`, `lows`, `volumes`.

## 3.5 알고리즘 출처 (정직한 구분)

- **개념·정의 = 마크 미너비니.** 아래 §4.0의 4단계 정성 정의는 미너비니
  『Trade Like a Stock Market Wizard』(2013)·『Think & Trade Like a Champion』
  (2017) 등의 Cup-Completion Cheat 설명을 발췌·요약한 것이다.
- **구체 수치·계산 규칙 = 이 프로젝트의 공학적 번역(원전 아님).** "좁은 선반",
  "하단/중단", "거래량 마름", 컵 깊이·기간 한도 등을 기계 판정으로 옮기며 고른
  임계값은 책의 "정답"이 아니라 구현 선택이다. 전부 CLI 인자로 노출하고(§6)
  한국 종목 백테스트 튜닝을 후속 과제로 둔다(§9).

## 4. 3C 판정 알고리즘

### 4.0 미너비니 정의 (발췌 요약 — 판정의 기준 원본)

치트의 4단계(§1)와 매수 규칙:
- 컵(하락→바닥→반등)이 형성되는 도중, **반등의 하단~중단**에서 주가가 잠깐
  멈춰 **좁고 타이트한 선반(cheat area)** 을 만든다.
- 선반 직전·내부에서 **거래량이 줄어든다(마름)**.
- 선반 고점을 **거래량과 함께 돌파**하는 지점이 **조기 매수점(피벗)**.
- 이 매수점은 전통적 컵앤핸들 피벗(옛 고점 부근)보다 **한참 아래**다 → 손절폭이 좁다.

→ 성립 조건 = **(컵)** ①왼쪽 하락(깊이 밴드) ②바닥 다지기(기간) ③오른쪽 반등
+ **(치트 선반)** ④좁은 선반(길이·깊이) + **하단/중단 위치** + 돌파 전 거래량 마름.

### 4.1 분석 구간(lookback)

- lookback = 최근 **250거래일**(약 1년). 컵 베이스는 깃발보다 길어(7주~수개월)
  넉넉한 창이 필요하다. (파워플레이의 120일보다 큼.)
- **데이터 길이 가드**: 시계열이 없으면 `no_data`/`no_series`, lookback 적용 후
  `min_total_days`(기본 40거래일, 내부 파라미터) 미만이면 `base_too_short` 로
  조기 반환(컵은 최소 7주 베이스를 요구하므로 파워플레이의 20보다 큼).

### 4.2 앵커링 — 컵 바닥·왼쪽 테두리·선반 고점 (바닥 기준 앵커)

> **갱신(2026-06-30, v2a로 교체됨):** 아래 "컵 바닥 먼저" 앵커링은 트렌드 통과
> 입력(신고가 다수)에서 `shelf_position_pct > 100%`·`pattern_count=0` 을 내는
> 한계가 실데이터로 확인되어, **"왼쪽 테두리(옛 peak)=lookback 최고가 먼저"**
> 앵커링으로 교체되었다. 정의·근거는
> `2026-06-30-find-3c-v2-anchoring-design.md` 참조. 이하 본 절 내용은 역사적 기록.

> **중요(파워플레이와 다른 점):** 파워플레이의 피벗(깃발 천장)은 깃대 꼭대기라
> **구간 전체 최고점**이므로 "눌림 확인된 최고 고가"를 그냥 잡으면 됐다. 하지만
> 치트의 선반은 **옛 고점(왼쪽 테두리)보다 낮은** 위치에서 돌파한다(그게 "일찍
> 산다"의 본질). 따라서 "구간 전체 최고 고가"를 피벗으로 잡으면 선반이 아니라
> **왼쪽 테두리**를 잡아버린다. 그래서 치트는 **컵 바닥을 먼저 앵커**하고, 그
> 바닥 *이후*(오른쪽 벽)에서만 선반을 찾는다.

순서대로:

1. **컵 바닥(cup_low)** = lookback 구간 전체의 **최저 저점**(`argmin(lows)`).
   `cup_low_idx`, `cup_low`.
2. **왼쪽 테두리(left_rim_high, 옛 고점)** = `cup_low` *이전* 구간 `[0, cup_low_idx]`
   의 **최고 고가**. `left_rim_idx`, `left_rim_high`. (왼쪽 하락 벽의 출발 고점.)
3. **치트 선반 고점(shelf_high) = 피벗(돌파 매수점)** = `cup_low` *이후*(오른쪽 벽,
   `[cup_low_idx+1, n−1]`)에서 **"뒤에 눌림이 확인된 가장 높은 고점"**.
   > **중요(돌파가 잡히려면):** 교과서적 돌파일(신고가로 선반 천장을 뚫는 날)은
   > 그날 고가가 곧 우측 신고가가 된다. 피벗을 "우측 최고 고가"로 잡으면 피벗이
   > 돌파 봉 자신으로 옮겨가 "종가 > 피벗"이 영영 성립하지 않는다. 그래서
   > `find-power-play`/`find-vcp`와 동일하게 피벗을 **그 뒤로 눌림이 확인된 고점**
   > 으로 한정한다.
   - 구현: 우측 피벗 후보 = `i ∈ [cup_low_idx+1, n−2]` 중
     `min(이후 저가들) ≤ highs[i] × (1 − min_shelf_pullback/100)` 를 만족(= 그 뒤로
     `min_shelf_pullback`%(기본 3) 이상 눌린 고점). 후보 중 **가장 높은 고가**가
     `shelf_high`. (후보가 없으면 우측 구간 최고 고가로 폴백 → 보통 선반 길이
     게이트에서 걸러짐.)

→ 인덱스 순서 `left_rim_idx ≤ cup_low_idx < shelf_high_idx` 가 구조적으로 보장된다.
컵·선반이 실제로 없으면(그냥 상승/하락) 아래 깊이·위치 게이트에서 자연히 걸러진다.

> **앵커링 한계(후속, §9):** `cup_low`를 lookback 전체의 최저점으로 잡으므로,
> 한 종목에 베이스가 여러 개면 **가장 깊은(보통 가장 오래된) 바닥**에 앵커되어
> 현재 컵이 아닌 큰 베이스를 잡을 수 있다. 이때도 깊이·기간·선반 위치 게이트가
> 부적합한 앵커를 거른다. 트렌드 통과 종목은 상승 추세라 현재 컵이 보통
> 지배적이므로 1차 구현으로는 충분하다고 보고, 다중 베이스 정교화는 후속 과제.

### 4.3 컵 게이트 (①하락 ②바닥 — 조건 4.0-①②)

1. **컵 깊이** `cup_depth_pct = (left_rim_high − cup_low)/left_rim_high × 100`.
   - `min_cup_depth`(기본 12%) ≤ 깊이 ≤ `max_cup_depth`(기본 50%).
   - 미달 시 `cup_too_shallow`(컵이 아니라 단순 상승), 초과 시 `cup_too_deep`(망가진 차트).
2. **베이스 기간** `cup_base_days = (n−1) − left_rim_idx` (왼쪽 테두리→현재 거래일).
   - `≥ min_cup_days`(기본 35거래일 = 7주, 오닐 최소 베이스). 미달 시 `cup_too_short`
     (V자 급반등 배제).

### 4.4 치트 선반 게이트 (④좁은 선반 + 위치 + 거래량 마름)

선반 구간 = `shelf_high` 이후 현재까지 `[shelf_high_idx, n−1]` (파워플레이 깃발과
동일 정의). `shelf_low = min(선반 저가)`.

1. **길이** `shelf_length_days = (n−1) − shelf_high_idx`.
   - `≥ min_shelf_days`(기본 5) 이고 `≤ max_shelf_days`(기본 25).
   - 미달 `shelf_too_short`, 초과 `shelf_too_long`.
2. **깊이** `shelf_depth_pct = (shelf_high − shelf_low)/shelf_high × 100`.
   - `≤ max_shelf_depth`(기본 **12%**; 치트 선반은 타이트). 초과 시 `shelf_too_loose`.
3. **★ 위치(치트의 본질)** `shelf_position_pct =
   (shelf_high − cup_low)/(left_rim_high − cup_low) × 100`
   = 선반이 컵 깊이의 몇 % 높이에 있는지(0%=바닥, 100%=왼쪽 테두리).
   - `≤ max_shelf_position`(기본 **66%** = 하단/중단; low cheat만 원하면 33).
   - 초과 시 `shelf_too_high_in_cup`(선반이 컵 윗부분 = 일반 컵앤핸들이지 치트 아님).
   - 분모(`left_rim_high − cup_low`)는 §4.3-1에서 양수 보장(깊이≥12%).
4. **거래량 마름** `volume_dryup_ratio = 최근 5거래일 평균 거래량 / 오른쪽 반등
   구간 평균 거래량(rally_vol_avg, §4.5)`. 돌파 전 거래량이 줄어야 함 → 성립 조건
   `≤ 1.0`(§4.6 actionable 게이트와 동일 경계). 안 마르면 `volume_not_drying`.

`pattern_detected = true` ⟺ §4.3~4.4의 게이트(컵 깊이·기간 + 선반 길이·깊이·
위치·거래량 마름)를 **모두 충족**. 불충족 시 `pattern_detected=false` +
`reason`(첫 불충족 조건) 기록.

### 4.5 거래량 기준 구간 — 오른쪽 반등 (돌파·dryup 분모)

- **`rally_vol_avg`** = 오른쪽 반등 구간 `[cup_low_idx, shelf_high_idx]` 평균
  거래량. 이 구간이 비면 컵 전체 `[left_rim_idx, shelf_high_idx]` 평균으로 폴백.
  돌파·dryup·기준 거래량에 이 값을 분모로 일관 사용(파워플레이 `pole_vol_avg`와
  같은 역할).
- **`rally_vol_ratio`**(보고용, 게이트 아님) = `rally_vol_avg / 왼쪽 하락 구간
  `[left_rim_idx, cup_low_idx]` 평균 거래량`. 컵의 전형적 거래량 특성(왼쪽 하락 시
  거래량 감소, 오른쪽 반등 시 증가) 참고 지표. 왼쪽 구간이 비면 `null`.

### 4.6 피벗·상태 판정 (find-vcp·find-power-play와 동일 규칙)

- **기준 거래량 `rally_vol_avg`**(§4.5) = 돌파·dryup 분모로 일관.
- **`pivot_price`** = `shelf_high`(돌파 매수점).
- **`pct_to_pivot`** = `(pivot_price − current_close)/pivot_price × 100`
  (양수면 피벗 아래, 음수면 이미 위).
- **`status`**:
  - `breakout` : 당일 종가 > 피벗 AND 당일 거래량 ≥ `rally_vol_avg ×
    breakout_vol_mult`(기본 1.4) — "대규모 거래량 돌파".
  - `failed` : 종가가 선반 저점(`shelf_low`) 하향 이탈(선반 붕괴).
  - `actionable` : 피벗 0~`near_pivot_pct`%(기본 5) 근접(`0 ≤ pct_to_pivot ≤ 5`)
    AND `volume_dryup_ratio ≤ 1.0`.
  - `forming` : 위 어디에도 안 들면 형성 중.
- **`entry_ready`** = `pattern_detected AND status ∈ {breakout, actionable}`.
  '살 자리' 신호는 진짜 3C 종목에만 부여(비패턴 돌파/근접은 false).

> **status 와 pattern 의 관계(형제 스킬과 동일):** `status` 는 패턴 성립 여부와
> 무관하게 **가격 위치**(돌파/근접/형성/붕괴)로 결정된다. 따라서
> `pattern_detected=false` 인 종목도 breakout/actionable 로 표시될 수 있으며,
> '살 자리(entry_ready)' 는 패턴까지 성립한 종목에만 부여된다(요약의
> breakout·actionable 개수 ≠ entry_ready).

> 임계값(컵 깊이 12~50%·기간 35일, 선반 깊이 12%·길이 5~25일·위치 66%, 거래량
> 마름 1.0·돌파 1.4배·근접 5% 등)은 전부 CLI 인자로 노출(§6). 위 숫자는
> 미너비니/오닐 책 기반 기본값.

## 5. 출력 스키마

`public/data/sepa-3c-candidates.json` (find-power-play와 동일 골격):

```jsonc
{
  "generated_at": "2026-06-30 21:00",
  "asof": "2026-06-30",
  "source": "sepa-trend-candidates.json",
  "params": { "lookback_days": 250, "min_cup_depth": 12, "max_cup_depth": 50,
              "min_cup_days": 35, "min_shelf_pullback": 3, "min_shelf_days": 5,
              "max_shelf_days": 25, "max_shelf_depth": 12, "max_shelf_position": 66,
              "breakout_vol_mult": 1.4, "near_pivot_pct": 5 },
  "pattern_count": 0,        // pattern_detected true 개수
  "entry_ready_count": 0,    // entry_ready true 개수(진짜 패턴 + 살 자리)
  "status_distribution": { "breakout": 0, "actionable": 0, "forming": 0, "failed": 0 },
  "candidates": [
    {
      "code": "...", "name": "...", "market": "KOSDAQ",
      "current_price": 0, "rs": 99,
      "pattern_detected": true,
      "entry_ready": true,   // pattern_detected AND status ∈ {breakout, actionable}
      "cup_depth_pct": 28.4,        // 컵 깊이(왼쪽 테두리 대비 바닥)
      "cup_base_days": 62,          // 베이스 기간(왼쪽 테두리→현재, 거래일)
      "shelf_position_pct": 41.0,   // ★ 선반이 컵 깊이의 몇 % 높이(하단/중단=≤66)
      "shelf_depth_pct": 7.8,       // 선반 조정폭(타이트)
      "shelf_length_days": 11,      // 선반 길이(거래일)
      "pivot_price": 0,             // = 선반 고점
      "pct_to_pivot": 2.1,
      "volume_dryup_ratio": 0.72,
      "rally_vol_ratio": 1.6,       // 보고용(오른쪽 반등량/왼쪽 하락량)
      "tightness_pct": 3.1,         // 보고용(최근 10일, 합격 게이트 아님)
      "status": "actionable",
      "reason": null,               // 성립 시 null; 불성립 시 첫 불충족 조건명
      "left_rim_date": "...",       // 근거(옛 고점)
      "cup_low_date": "...",        // 근거(컵 바닥)
      "shelf_high_date": "..."      // 근거(선반 고점=피벗)
    }
  ]
}
```

- `candidates`는 입력 종목 전부 포함(불성립도 reason과 함께) — 환각 방지·디버그용.
- `reason`은 `pattern_detected=false`인 모든 경로에서 채워진다
  (no_data / no_series / base_too_short / no_overhead_cup / cup_too_shallow /
  cup_too_deep / cup_too_short / shelf_too_short / shelf_too_long /
  shelf_too_loose / shelf_too_high_in_cup / volume_not_drying / eval_error:*).
  (`no_overhead_cup` = v2a 추가: 옛 peak가 너무 최근이라 그 아래 회복 컵 구조가 없음.)
- 정렬: `entry_ready` 우선(true→false) → `status`(breakout→actionable→
  forming→failed) → `pct_to_pivot` 오름차순.

## 6. 구성 요소(코드 구조) — find-power-play 패턴 미러링

- **`scripts/canslim_lib/cheat.py`** : 순수 평가 부품 —
  `evaluate_cheat(series_dict, params) -> dict`, 보조 함수
  (`find_cheat_shelf` 선반/컵 앵커 탐지). 입출력 순수 함수라 합성 시계열로 단위
  테스트 가능. 기존 `canslim_lib/power_play.py`·`vcp.py`와 같은 부품 패턴.
- **`scripts/screen_3c.py`** : CLI 엔트리. 입력 로드 → 종목별 평가 → JSON 저장 +
  콘솔 요약표(상태별 개수, entry_ready 종목 표). 한 종목 평가 오류가 전체 런을
  멈추지 않게 종목별 try/except(`eval_error:*`).
- **`.claude/skills/find-3c/SKILL.md`** : find-power-play SKILL.md와 동일 톤.

### CLI 인자
- `--in`(default `public/data/sepa-trend-candidates.json`)
- `--out`(default `public/data/sepa-3c-candidates.json`)
- `--lookback-days`(250), `--min-cup-depth`(12), `--max-cup-depth`(50),
  `--min-cup-days`(35), `--min-shelf-pullback`(3), `--min-shelf-days`(5),
  `--max-shelf-days`(25), `--max-shelf-depth`(12), `--max-shelf-position`(66),
  `--breakout-vol-mult`(1.4), `--near-pivot-pct`(5)
- `--ticker`(단일 종목 디버그, 저장 안 함)

## 7. 불변 원칙 (기존 SEPA 스킬과 동일)

- 공유 파일 무접촉, 컷오프 금지, 환각 금지(판정 근거 JSON 포함), 자동 commit 안 함.
- `update-data` 선행 권장(최신 OHLCV). `find-3c` SKILL.md에 명시.
- 콘솔 출력 수치(패턴 개수·상태 분포 등)는 그대로 보고, 추측·요약 금지.

## 8. 검증 계획

- `cheat.py` 순수 함수 단위 테스트(합성 시계열):
  ① 깔끔한 3C(하락→바닥→반등 도중 하단/중단 좁은 선반) → `pattern_detected`,
  ② 컵 너무 얕음(<12%) → false(`cup_too_shallow`),
  ③ 컵 너무 깊음(>50%) → false(`cup_too_deep`),
  ④ V자 급반등(베이스 <35일) → false(`cup_too_short`),
  ⑤ 선반이 컵 상단(위치 >66%) → false(`shelf_too_high_in_cup`),
  ⑥ 선반 너무 느슨(>12%) → false(`shelf_too_loose`),
  ⑦ 피벗 돌파 + 대량거래 → `status=breakout`.
- 실제 트렌드 통과 종목으로 1회 풀런 → 상태 분포 확인. **2026-06-30 관측: 70종목
  중 `pattern_count=0`, 대부분 불성립(`shelf_too_loose`/`cup_too_shallow`/
  `shelf_too_long`/`shelf_too_short` 등)이며 `shelf_position_pct`가 100%를 크게
  초과한다 — §9의 앵커링 한계가 입력 집단 전체에서 확인됨.** v1은 이 상태로
  완성하고 앵커링 재설계는 후속(§9).
- `--ticker`로 한 종목을 찍어 컵 깊이·선반 위치·피벗 산출 자체는 오류 없이 나오는지
  확인(현 v1에선 위치 지표가 신고가 종목에서 >100%로 나오는 게 정상적 한계).

## 9. 미해결/후속

- 임계값 기본치는 미너비니/오닐 책 기반 추정 — 한국 종목으로 백테스트 튜닝은 후속.
- "하단/중단 위치"·"선반 타이트"·"거래량 마름" 임계값은 정성적이라 백테스트
  민감도 점검 후속 과제.
- **앵커링 정교화(§4.2 한계) — 실데이터로 확인된 v1 핵심 제약:** 2026-06-30
  트렌드 통과 70종목 풀런 결과 `pattern_count=0`, 사실상 전 종목 불성립이었다.
  원인은 "3C가 희귀해서"가 아니라 **앵커링이 입력 집단과 안 맞아서**다:
  입력이 트렌드 통과 종목(=52주 신고가 부근, 상승 추세)인데 `cup_low`를
  lookback 전체 최저점(≈52주 저점)으로 잡으면 `left_rim`은 그 옛 저점 *이전*
  고점이 되고, 종목은 이미 그 고점을 넘어 신고가를 만들었으므로
  `shelf_high > left_rim` → `shelf_position_pct`가 100%를 크게 초과(관측값
  271%·1428%·2577% 등)해 위치 지표가 무의미해진다. 즉 **현 v1은 트렌드 통과
  입력에서 거의 항상 0개를 산출**한다(의도된 선별이 아니라 구조적 한계).
  - **올바른 수정(후속):** `find_cheat_shelf`를 **최근 컵 앵커링**으로 재설계 —
    선반보다 높은 *가장 최근* 옛 고점을 `left_rim`으로, 그 사이 최저점을 `cup_low`
    로 잡는다. 그러면 `shelf_position ≤ 100%`가 구조적으로 보장되고 신고가 종목은
    `shelf_too_high_in_cup`으로 깔끔히 걸러진다. 본질적으로 치트(옛 고점 아래
    회복 중 조기 진입)와 신고가 추세주는 상충하므로, 트렌드 통과 종목 중에서도
    최근 조정으로 옛 고점 아래에 있는 소수만 후보가 된다.
  - 사용자 결정(2026-06-30): v1은 현 설계·구조 그대로 완성하고, 위 재설계는
    별도 작업으로 분리한다.
- 형제 스킬(find-vcp·find-power-play)과의 결과 중복(한 종목이 여러 패턴에 동시
  검출) 처리·통합 뷰는 별도.
- SEPA 다음 단계(리스크: 손절폭·비중)는 별도 spec. 치트의 핵심 이점인 "좁은
  손절폭"은 이 단계 이후 리스크 spec에서 다룬다.
