# SEPA 패턴 테이블 "추이" 컬럼 (최근 티어 이력) — 설계 spec

작성일 2026-07-01 · 상태: 설계 승인됨 · 대상: `/stocks/sepa` 페이지

## 1. 배경·목적

각 패턴(VCP·파워플레이·3C) 테이블의 종목이 **최근 며칠간 어떤 티어를 거쳤는지** 한 행에서 보여준다. 예: 어제 🟢진입임박 → 오늘 🔴돌파는 `🟢🔴`, 오늘 새로 목록에 진입한 종목은 앞에 🆕(예: `🆕🔴`). 이를 위해 매 파이프라인 실행 시 **컴팩트 스냅샷**을 남겨 최근 3일(오늘+2일)치 티어 이력을 보관한다.

(초기 논의의 "티어 변화 요약 섹션"은 범위에서 제외 — 추이 컬럼만 구현.)

## 2. 확정된 결정

- 패턴 테이블에 **"추이" 컬럼만** 추가(별도 변화 요약 섹션·컴포넌트 없음).
- 추이 = 최근 날짜순 티어 점(오래된→최신). 티어 없음(숨김/미노출)인 날은 점 생략.
- **오늘 신규 진입**(직전 날짜엔 티어 없었고 오늘 티어 있음) → 맨 앞에 🆕.
- 티어 규칙은 기존 `classify`(sepaPatterns.ts) **그대로 재사용**(중복 로직 없음).
- 보관 = 최근 **3일**(오늘+2일), 초과분 정리. git으로 6/30·7/1 부트스트랩.
- 대상 패턴 = 4종 전부(vcp·powerplayTrend·powerplayAll·threeC).

## 3. 티어·점 매핑

`classify` 결과 → 점: `breakout → 🔴`, `actionable → 🟢`, `watch → 🟡`, `null(숨김/미노출) → (점 없음)`.

## 4. 스냅샷 히스토리

**파일** `public/data/sepa-tier-history.json` (컴팩트):
```json
{
  "dates": ["2026-06-30", "2026-07-01"],
  "byDate": {
    "2026-07-01": {
      "vcp": [ { "code","name","market","rs","status","pivot_price","pct_to_pivot","vcp_detected","num_contractions" }, ... ],
      "powerplayTrend": [ { ..., "pattern_detected","flag_length_days","flag_depth_pct" }, ... ],
      "powerplayAll": [ ... ],
      "threeC": [ { ..., "pattern_detected" }, ... ]
    },
    "2026-06-30": { ... }
  }
}
```
- `dates`: 오래된→최신, 최대 3.
- 각 레코드 = 후보의 **트림된 RawCandidate**(분류에 필요한 키만). 저장 키 화이트리스트:
  `code, name, market, rs, status, pivot_price, pct_to_pivot, vcp_detected, pattern_detected, num_contractions, flag_length_days, flag_depth_pct` 중 존재하는 것만. 거대한 트렌드 파일은 미포함(작게 유지).
- 원 키(`vcp_detected`/`pattern_detected` 등)를 보존하므로 페이지의 `buildSection(records, config)`를 날짜별로 그대로 돌릴 수 있다.

**스냅샷 스텝** `scripts/snapshot_sepa.py`:
- 현재 `public/data`의 4개 후보 파일(`sepa-vcp-candidates.json`·`sepa-power-play-candidates.json`·`sepa-power-play-all-candidates.json`·`sepa-3c-candidates.json`)을 읽어 각 후보를 화이트리스트로 트림.
- 파일의 `asof` 날짜로 `byDate`에 추가(같은 날짜면 덮어씀), `dates` 갱신, **최근 3일 초과분 삭제**.
- SEPA 파이프라인 **마지막 스텝**으로 실행(검출기 4개 뒤).
- 파일 일부가 없으면 그 패턴은 빈 배열로 스냅샷(graceful).

**부트스트랩**: git의 6/30(`108e471`)·현재 7/1 후보 파일로 초기 `sepa-tier-history.json`(2일치) 생성.

## 5. 티어 이력 계산 (순수 `tierHistory.ts`)

- 타입: `interface TierHistory { dates: string[]; byDate: Record<string, Record<string, RawCandidate[]>> }` (안쪽 키 = 패턴 id: `"vcp"|"powerplayTrend"|"powerplayAll"|"threeC"`).
- `function computeTrendByCode(history: TierHistory, patternKey: PatternKey, config: PatternConfig): Record<string, string>`
  - 각 날짜의 해당 패턴 레코드마다 **레코드별 티어**(`Tier|null`)를 구해 **종목별 날짜순 배열**을 만든다.
  - 여기서 `buildSection`(숨김 제외·정렬)이 아니라 **레코드 1건→티어** 계산이 필요하다(숨김=null도 배열에 보존해야 하므로). DRY를 위해 `buildSection` 내부의 "detected·structureOk 추출 후 `classify`" 로직을 순수 헬퍼 `classifyCandidate(raw, config): Tier | null`로 뽑아 `buildSection`과 `computeTrendByCode`가 공유한다.
  - 각 종목의 표시 문자열 = `renderTrend(seq)`.
- `function renderTrend(seq: (Tier|null)[]): string`
  - `dots` = seq에서 null 아닌 티어를 순서대로 점(🔴/🟢/🟡)으로.
  - `isNew` = 최신값 non-null **AND** 직전 날짜값 null(직전 날짜 자체가 없으면 isNew=false).
  - 반환 = `(isNew ? "🆕" : "") + dots`. 모두 null이면 `""`.
- 검증 예: `[actionable, breakout]→"🟢🔴"`, `[null, breakout]→"🆕🔴"`, `[actionable, actionable]→"🟢🟢"`, `[actionable, watch]→"🟢🟡"`, 단일 `[breakout]→"🔴"`(직전 없음, isNew 아님).

## 6. 페이지·컴포넌트

- `src/app/stocks/sepa/tierHistory.ts` (신규, 순수) — 위 로직. **vitest 테스트.**
- `src/app/stocks/sepa/SepaPatternTable.tsx` (수정) — 선택적 prop `trendByCode?: Record<string, string>`. 있으면 헤더에 "추이" 컬럼(피벗대비 다음), 각 행에 `trendByCode[r.code] || "—"` 렌더.
- `src/app/stocks/sepa/page.tsx` (수정) — `sepa-tier-history.json` 로드 → 패턴별 `computeTrendByCode` 계산 → 각 `PatternSection`(→`SepaPatternTable`)에 `trendByCode` 전달. `PatternSection`에 `trendByCode` prop 추가.
- 스냅샷 스텝은 `find-3c` 등 SEPA 파이프라인 스킬 문서에 "마지막에 `python scripts/snapshot_sepa.py`" 한 줄 안내([[doc-logic-sync]]).

## 7. 에러·엣지

- 히스토리 파일 없음 → 페이지는 `trendByCode` 미전달 → 추이 컬럼 생략(기존 테이블 그대로, graceful).
- 히스토리 1일치뿐 → 추이는 오늘 점 1개, 🆕 없음.
- 종목이 히스토리엔 있으나 오늘 티어 null(숨김) → 추이 표시 대상은 현재 테이블 행(=오늘 티어 있는 종목)뿐이므로 그 행의 과거 점만 노출.
- 스냅샷 파일 일부 없음/깨짐 → 해당 패턴 빈 배열(스냅샷·계산 모두 graceful).

## 8. 테스트

- `tierHistory.ts` vitest(기존 러너): `renderTrend` 케이스(위 §5 예), `computeTrendByCode`(2일치 합성 히스토리 → 종목별 문자열, 신규 🆕, 숨김 제외).
- `snapshot_sepa.py`: 실행 스모크 — 현재 파일 스냅샷 후 `sepa-tier-history.json`에 오늘 날짜·4패턴 키 존재, `dates` 3일 이내.
- tsc·`next build` 무에러, 기존 vitest(29건) 유지.

## 9. 안 하는 것 (YAGNI)

- 티어 변화 요약 섹션(신규/승격/강등/이탈 묶음) — 제외.
- 3일 초과 장기 이력·차트. · 인트라데이 추이. · 자동 파이프라인 래퍼.
- 트렌드(1단계) 티어 추이 — 패턴 4종만.

## 10. 성공 기준

- `/stocks/sepa` 각 패턴 테이블에 "추이" 컬럼이 뜨고, 오늘/어제 티어가 점으로(예: 타이거일렉 `🟢🔴`, 나이스 `🟢🟡`), 신규 진입은 `🆕🔴`(아이비김영)로 표시.
- `sepa-tier-history.json`이 6/30·7/1로 부트스트랩되고, 이후 `snapshot_sepa.py`로 매일 갱신·3일 유지.
- `tierHistory.ts` vitest 통과. tsc·build 무에러, 기존 페이지·테스트 무영향.
