---
name: find-power-play
description: >
  SEPA 패턴 스킬(find-vcp 형제). 1단계(find-trend-template) 통과 종목의 일봉에서
  미너비니 파워 플레이(Power Play = High Tight Flag)를 탐지한다 — 14주 내 90%↑
  대량거래 폭등(깃대) + 얕고 좁은 횡보(깃발) + 돌파. 피벗·진입상태
  (breakout/actionable/forming/failed)를 산출해 sepa-power-play-candidates.json
  에 저장한다. OHLCV 캐시만 사용, 수급·공유 파일 무접촉. 사용자가 "/find-power-play",
  "파워 플레이 찾아줘", "하이 타이트 플래그", "깃발 패턴" 등을 요청할 때 사용.
---

# find-power-play — SEPA 패턴: 파워 플레이(High Tight Flag)

`find-trend-template`(SEPA 1단계) 통과 종목에 대해 미너비니 **파워 플레이**(14주 내 90%↑
깃대 + 얕은 깃발 + 돌파)를 탐지한다. find-vcp 의 형제 스킬(같은 입력, 다른 패턴).
정의·근거: `docs/superpowers/specs/2026-06-29-find-power-play-design.md`.

> **핵심 게이트(3개):** 깃대 90%/14주 · 깃발 깊이(≤20%) · 깃발 길이(8~30거래일).
> 조용한 출발(quiet)·깃대 거래량·거래량 마름(dryup)은 **보고용 지표(게이트 아님)** —
> 콘솔·JSON에는 표시되지만 불합격 사유로 쓰이지 않는다.
> 단, `volume_dryup_ratio`는 pattern_detected 불합격 사유엔 안 쓰이지만 actionable 상태 판정에는 쓰여 entry_ready에 간접 영향.
> 미너비니 본인 예시 BBY는 13주/135% — 14주/90% 기준은 BBY보다 넉넉한 허용 범위.

## 사전 조건
- **최신 데이터로 돌리려면 먼저 `update-data` → `find-trend-template`** 실행.
- 입력 `public/data/sepa-trend-candidates.json` 존재(= find-trend-template 산출).

## 실행 (1줄)
```
python scripts/screen_power_play.py
```
- 산출: `public/data/sepa-power-play-candidates.json`
- 콘솔: 상태 분포 + entry_ready 종목 표(깃대 상승률·기간, 깃발 깊이·길이, 피벗).

### 옵션
- `--universe all` : **전수 스캔** — 트렌드 통과뿐 아니라 평가된 전 종목(컷오프 없음)을
  대상으로 파워 플레이 탐지. 산출 `public/data/sepa-power-play-all-candidates.json`.
  (기본 `--universe trend` 는 트렌드 통과 종목만 → `sepa-power-play-candidates.json`.)
  하이타이트플래그는 추세 템플릿 미통과 종목에서도 나올 수 있어, `/stocks/sepa` 페이지가
  트렌드 섹션과 별도로 전수 섹션을 함께 보여준다.
  전수는 RS 약한 종목 노이즈가 많으므로 `--rs-min 80` 과 함께 쓰는 것을 권장
  (페이지 전수 섹션은 `--universe all --rs-min 80` 산출 기준).
- `--rs-min 80` : RS 강도 하한(이상만 평가) — 전수 스캔 노이즈 축소.
- `--ticker CODE` : 단일 종목 디버그(저장 안 함).
- `--min-flagpole-gain 90` / `--max-flagpole-days 70` : 깃대(14주 내 90%↑) 튜닝.
  (미너비니 본인 예시 BBY는 13주/135%; 기본값 90%/70d는 넉넉한 허용 범위.)
- `--flag-window 45` : 피벗 후보를 최근 N봉으로 한정 — 무관한 옛 고점 배제.
- `--pole-vol-mult 1.5` / `--max-pre-pole-gain 30` : 깃대 거래량·조용한 출발 튜닝
  (보고용; 게이트 아님).
- `--min-flag-days 8` / `--max-flag-days 30` / `--max-flag-depth 20` : 깃발 튜닝
  (저가주는 `--max-flag-depth 25`).
- `--min-flag-pullback 3` : 깃발 최소 눌림폭(%) — 깃발 천장 대비 최소 되돌림.
- `--lookback-days 120` : 깃대·깃발을 탐색하는 되돌아보는 기간(거래일).
- `--breakout-vol-mult 1.4` / `--near-pivot-pct 5` : 돌파/근접(actionable) 판정 임계값 튜닝.
- `--out PATH` : 출력 경로 변경.

## 결과 확인
- `pattern_count` : 파워 플레이 3 하드게이트 성립 종목 수(14주 90% 깃대 + 깃발 깊이 + 깃발 길이).
- `status_distribution` : breakout(돌파) · actionable(피벗 근접+거래량 마름) ·
  forming(형성 중) · failed(깃발 붕괴).
- `entry_ready` 종목이 다음 단계(리스크·진입) 후보.
- 불성립 종목도 `reason`과 함께 전부 포함(환각 방지·디버그).
- `status` 는 패턴 성립 여부와 무관하게 가격 위치·거래량 조건(돌파/근접/형성/붕괴)으로 결정된다. 따라서 `pattern_detected=false` 인 종목도 breakout/actionable 로 표시될 수 있으며, '살 자리(entry_ready)' 는 패턴까지 성립한 종목에만 부여된다(요약의 breakout·actionable 개수 ≠ entry_ready).

## 안 하는 것
- VCP 베이스 탐지(그건 find-vcp) · 전 종목 스캔(트렌드 통과 종목만) ·
  공유 파일 갱신 · 수급 신호 · 자동 commit.
- 타이트(tightness)는 합격 게이트가 아님 — 보고용 지표(책: 조정 ≤10%면 이미 타이트).
- **하드 게이트는 3개뿐:** 깃대(90%/14주·70거래일) · 깃발 깊이(≤20%) · 깃발 길이(8~30거래일).
  조용한 출발(quiet)·깃대 거래량·거래량 마름(dryup)은 **소프트 신호 = 보고용**이며
  불합격 사유(reason)에 포함되지 않는다.
