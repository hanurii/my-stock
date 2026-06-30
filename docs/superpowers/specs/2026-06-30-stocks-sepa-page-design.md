# /stocks/sepa — SEPA 멀티 패턴 대시보드 (설계 spec)

작성일 2026-06-30 · 상태: 설계 승인 대기 · 대상: 새 Next.js 라우트 `src/app/stocks/sepa`

## 1. 배경·목적

SEPA(Specific Entry Point Analysis) 파이프라인의 산출(트렌드 템플릿 1단계 + VCP·파워플레이·3C 등 패턴)을 **한 페이지에서 패턴별 섹션으로** 보여준다. 각 섹션은 그 패턴을 **이미 만족한 종목**과 **곧 만족할 예의주시 종목**을 함께 노출해, 사용자가 진입 후보를 한눈에 본다.

기존 `src/app/stocks/trend-template/page.tsx` 패턴(서버 컴포넌트가 `public/data` JSON을 `fs`로 읽어 헤더+요약+정렬 테이블 렌더)을 그대로 따른다.

## 2. 확정된 결정

- **범위**: 트렌드 템플릿(1단계 게이트) + VCP + 파워플레이 + 3C(자리표시). **확장형** — 패턴 추가 = 레지스트리 1줄 + 컬럼 설정.
- **구조**: 패턴별 디테일 섹션(패턴 고유 지표까지 표에 풀어 보임). 한 종목이 여러 섹션에 중복 등장 가능.
- **파워플레이 = 2개 하위 섹션**: (A) 트렌드 통과 종목 중 / (B) 전체 종목(전수) 중. (B)의 산출 파일은 **아직 없음** → 자리만 마련, 데이터 생기기 전엔 "데이터 없음".
- **노출 대상(공통 티어 규칙)**: 만족 + 곧 만족(예의주시)까지. 예의주시 임계 = 피벗까지 **0~12%**.
- **데이터 연결**: 페이지는 `public/data`를 읽기만 한다. 새 코일 검출기 결과·파워플레이 전수 스캔을 master에 올리는 일은 **별도 트랙**. 파일 없으면 graceful 안내.
- **읽기 전용**: 공유 데이터 파일 무수정, 자동 commit 무, 수급 신호 무.
- **테스트**: vitest 신규 도입, 순수 분류기만 단위 테스트(§8).
- **내비**: `StocksTabs`에 `/stocks/sepa` 탭 추가(§9).

## 3. 티어 분류 규칙 (패턴 공통)

각 패턴 후보 레코드는 `status`(breakout/actionable/forming/failed), `pivot_price`, `pct_to_pivot`(= (pivot−종가)/pivot×100; 양수=종가가 피벗 아래), 패턴별 `*_detected`/`entry_ready`, 그리고 패턴별 "구조 형성" 지표를 갖는다. 표시 티어는:

| 티어 | 배지 | 규칙 |
|---|---|---|
| 돌파(완성) | 🔴 | `detected = true` AND `status = "breakout"` |
| 진입임박 | 🟢 | `detected = true` AND `status = "actionable"` |
| 예의주시(곧 만족) | 🟡 | `(detected = true AND status = "forming")` **OR** (`status ≠ "failed"` AND `pivot_price != null` AND `0 ≤ pct_to_pivot ≤ 12` AND `structureOk(c)`) |
| (숨김) | — | 그 외(failed / 피벗 없음 / 피벗에서 12% 초과로 먼 형성중 / 미검출+원거리) |

- `structureOk(c)`는 **패턴별 술어**(레지스트리 제공):
  - VCP: `num_contractions >= 2`
  - 파워플레이: `flag_length_days != null && flag_length_days > 0`
  - 기본값(미지정 패턴): `pivot_price != null`
- **정렬**: 티어 우선(🔴 → 🟢 → 🟡), 동률이면 `abs(pct_to_pivot)` 오름차순(피벗에 가까운 순 — 돌파는 음수이므로 절댓값으로 "가장 덜 연장된" 종목을 위로), 그다음 `rs` 내림차순.
- `watch_pct = 12`는 모듈 상수(한 곳에서 조정).

## 4. 데이터 소스 (읽기 전용, 없으면 graceful)

`public/data/` 에서 요청 시 로드. `readJson<T>()`(트렌드 페이지와 동일, 실패 시 null):

| 패턴/단계 | 파일 | 현 존재 | 비고 |
|---|---|---|---|
| 1단계 트렌드 | `sepa-trend-candidates.json` | ✅ | 모집단·게이트. 없으면 페이지 전체 안내 |
| VCP | `sepa-vcp-candidates.json` | ✅ | 신 코일 검출기 출력(coil_len 등 포함) |
| 파워플레이(트렌드) | `sepa-power-play-candidates.json` | ✅ | source=트렌드 통과 |
| 파워플레이(전수) | `sepa-power-play-all-candidates.json` | ❌ 미생성 | 전수 스캔. 없으면 "데이터 없음" |
| 3C | `sepa-3c-candidates.json` | ❌ 미생성 | 없으면 "준비중" |

**레코드 스키마(읽는 필드)**:
- 공통: `code, name, market, current_price, rs, status, pivot_price, pct_to_pivot, volume_dryup_ratio, tightness_pct`.
- VCP 추가: `vcp_detected, entry_ready, num_contractions, contractions[], base_length_days, base_depth_pct, coil_len, coil_dry_mean, coil_range_pct`.
- 파워플레이 추가: `pattern_detected, entry_ready, flagpole_gain_pct, flagpole_days, flagpole_vol_ratio, pre_pole_gain_pct, flag_length_days, flag_depth_pct, pole_start_date, flag_high_date`.
- 트렌드: `code, name, market, market_cap_eok, current_price, rs, all_pass, extras{high_52w,...}` + top-level `asof, evaluated_count, market_status`.

> 레지스트리가 패턴마다 `detectField`(예: `vcp_detected`/`pattern_detected`)를 지정해 공통 분류기가 detected를 읽는다.

## 5. 구성 요소

- `src/app/stocks/sepa/page.tsx` — **서버 컴포넌트**. 파일 로드 → 패턴별 분류 → 헤더·트렌드요약·섹션들·용어 렌더. 트렌드 파일 없으면 전체 안내(트렌드 페이지 문구 패턴 재사용).
- `src/app/stocks/sepa/sepaPatterns.ts` — **순수 로직(프레임워크 비의존)**. 패턴 레지스트리(id, label, file, detectField, structureOk, columns) + 티어 분류기 `classify(candidate, watch_pct)` + 정렬 `sortRows(rows)` + 행 매퍼. **테스트 대상**.
- `src/app/stocks/sepa/SepaPatternTable.tsx` — **클라이언트 컴포넌트**. `rows` + `columns`(레지스트리 컬럼 설정) 받아 티어 그룹 표시 + 머리글 클릭 정렬. `TrendTemplateTable` 스타일·테마 토큰 재사용. 패턴마다 컬럼만 다르고 렌더 로직은 공유(DRY).

각 패턴 섹션은 `<section>`: 헤더(패턴명 + 카운트: 검출 N · 🔴a 🟢b 🟡c) + `SepaPatternTable`. 파일 없으면 표 대신 자리표시 문구.

**추가로 수정/생성하는 파일**:
- `src/app/stocks/StocksTabs.tsx` (수정) — `tabs` 배열에 `/stocks/sepa` 항목 추가(§9).
- `package.json` (수정) — `vitest` devDependency + `"test": "vitest run"` 스크립트.
- `vitest.config.ts` (생성) — node 환경 설정(§8).
- `src/app/stocks/sepa/sepaPatterns.test.ts` (생성) — 분류기 단위 테스트(§8).

## 6. 페이지 레이아웃 (위→아래)

1. **헤더**: "SEPA 셋업" + 부제 + 각 파일 `asof`(서로 다르면 모두 표기, 신선도 차이 노출) + 트렌드 통과 N.
2. **1단계 트렌드 요약 카드** + KOSPI 추세 배지(`market_status`).
3. **VCP 섹션**.
4. **파워플레이 섹션** — 하위 A(트렌드) · B(전수, 당분간 "데이터 없음").
5. **3C 섹션** — "준비중".
6. **용어·배지 설명**: 티어(🔴돌파·🟢진입임박·🟡예의주시) + 패턴 지표(피벗·수축·코일마름·깃대상승·깃발깊이 등) 해설.

## 7. 에러·엣지 처리

- 트렌드 파일 없음/깨짐 → 페이지 전체 "데이터가 아직 생성되지 않았습니다" 안내.
- 개별 패턴 파일 없음/깨짐 → 그 섹션만 자리표시(전수 파워플레이·3C는 당분간 상시 해당).
- 표시 종목 0건(파일은 있으나 티어 통과 0) → 섹션에 "현재 해당 종목 없음".
- `pivot_price`/`pct_to_pivot` null → 그 종목은 예의주시 후보에서 제외(숨김), 표 렌더 시 "—".
- 파일별 `asof` 상이 → 경고 아닌 정보로 각 기준일 병기.

## 8. 테스트 (확정: vitest 도입)

프로젝트에 JS/TS 테스트 러너가 없으므로(package.json: dev/build/start/lint뿐) **vitest를 새로 도입**한다. 순수 `sepaPatterns.ts`만 단위 테스트한다(페이지 컴포넌트는 얇은 렌더라 시각 확인).

- 설정: `vitest` devDependency 추가 + package.json `"test": "vitest run"` 스크립트 + `vitest.config.ts`(node 환경; React 컴포넌트는 테스트 대상 아님이라 jsdom 불필요).
- 테스트 파일: `src/app/stocks/sepa/sepaPatterns.test.ts`.
- 검증 케이스: 티어 규칙(🔴 detected+breakout / 🟢 detected+actionable / 🟡 detected+forming / 🟡 미검출+피벗 0~12%+structureOk / 숨김: failed·피벗없음·먼 형성중), **12% 경계**(pct_to_pivot=12 → 포함, 12.01 → 숨김; pct_to_pivot=0 → 포함, −0.01 → 돌파 아니면 숨김), structureOk 패턴별(VCP num_contractions, 파워플레이 flag_length_days), 정렬(티어 → abs(pct_to_pivot) → rs).
- `next build`·`eslint`에 영향 없도록 vitest 설정은 빌드 파이프라인과 분리.

## 9. 내비게이션 (확정: StocksTabs 탭 추가)

`src/app/stocks/StocksTabs.tsx`의 `tabs` 배열에 `/stocks/sepa` 항목을 추가한다 — `{ href: "/stocks/sepa", label: "SEPA 셋업", icon: "candlestick_chart" }`(label·icon은 구현 시 최종 확정, material symbols). 기존 탭 동작·`berkshireIsNew` 프롭은 그대로. 활성 표시는 `usePathname` 기존 로직이 자동 처리.

## 10. 안 하는 것 (YAGNI)

- 데이터 생성/갱신/머지(별도 트랙) · 공유 파일 수정 · 자동 commit.
- 파워플레이 전수 스캔 데이터 생성(데이터 트랙). · 3C 검출기(아직 Phase 2).
- 차트·실시간·매매 신호·수급. · 탭바 개편.

## 11. 성공 기준

- `/stocks/sepa` 접속 시: 트렌드 요약 + VCP·파워플레이(A) 섹션이 현 `public/data` 기준으로 렌더되고, 각 종목이 🔴/🟢/🟡 티어로 올바르게 분류·정렬됨.
- 없는 파일(파워플레이 전수·3C) 섹션은 깨지지 않고 자리표시.
- `StocksTabs`에 "SEPA 셋업" 탭이 추가되고 활성 표시가 동작.
- 분류기 vitest 단위 테스트 통과(`npm run test`). 12% 경계·정렬·structureOk 검증.
- 기존 페이지·빌드 무영향(`next build` 성공, lint 통과).
