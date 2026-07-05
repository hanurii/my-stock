---
name: find-vcp
description: >
  SEPA 2단계. 1단계(find-trend-template) 통과 종목의 일봉에서 미너비니 VCP(변동성
  수축 패턴) 베이스를 탐지하고 피벗(돌파 매수점)·진입상태(breakout/actionable/
  forming/failed)를 산출해 sepa-vcp-candidates.json 에 저장한다. OHLCV 캐시만 사용,
  수급·공유 파일 무접촉. 사용자가 "/find-vcp", "VCP 찾아줘", "베이스·피벗 분석",
  "SEPA 2단계" 등을 요청할 때 사용.
---

# find-vcp — SEPA 2단계: VCP 베이스·피벗 탐지

`find-trend-template`(SEPA 1단계) 통과 종목에 대해 미너비니 **VCP(변동성 수축
패턴)** 를 탐지한다. 정의·근거: `docs/superpowers/specs/2026-06-30-vcp-detector-v2-design.md`.

## 사전 조건
- **최신 데이터로 돌리려면 먼저 `update-data` → `find-trend-template`** 실행.
- 입력 `public/data/sepa-trend-candidates.json` 존재(= find-trend-template 산출).

## 실행 (1줄)
```
python scripts/screen_vcp.py
```
- 산출: `public/data/sepa-vcp-candidates.json`
- 콘솔: 상태 분포 + breakout/actionable 종목 표.

### 옵션
- `--ticker CODE` : 단일 종목 디버그(저장 안 함).
- `--zigzag-pct 8` / `--max-final-depth 10` / `--breakout-vol-mult 1.4` /
  `--lookback-days 120` : VCP 임계값 튜닝(기본값은 미너비니 개념 기반 추정).
- `--out PATH` : 출력 경로 변경.

## 결과 확인
- **VCP 인식**: 적응형 ZigZag로 변동성 수축 연쇄를 탐지. 피벗(최소저항선) = 최종 타이트 코일(좁은 변동폭 AND 마른 거래량) 고점; 인식에 코일 존재 필수(코일 없으면 reason=no_tight_coil).
- **피벗 극저거래량일(레버 B)**: 코일 평균만 마른 게 아니라 **코일 안에 '진짜 극저거래량 하루'(v/MA50 ≤ `coil_extreme_dry_max`=0.5)가 최소 1일** 있어야 VCP 인정(미너비니: "가장 오른쪽 수축에 하루 이틀 극도로 낮은 거래량이 좋다"). 없으면 reason=`no_dry_coil_day`·피벗 무효. MIK 최저일 0.11×로 통과.
- **돌파(status)**: 첫돌파(전일 종가≤피벗, 당일 종가>피벗) + 양봉(종가>시가) + **거래량 확장** + 피벗근접 동시 충족. 거래량 확장 = `거래량≥50일선×1.4` **또는** `거래량≥마른-코일 평균×`coil_breakout_vol_mult`(1.5)`(레버 A — IPO/저유동으로 50일선이 부풀어도 dry-up 대비 진짜 확장을 인정; MIK 돌파일 통과 근거).
- **코일 진단 필드**: 출력 JSON에 `coil_len`(코일 길이/일), `coil_dry_mean`(코일 평균 거래량/MA50), `coil_range_pct`(코일 종가 변동폭%), `coil_min_dry`(코일 **최저일** 거래량/MA50 — 레버 B 근거) 가산 필드 포함.
- **status ⊥ 인식**: status(breakout 등)는 vcp_detected 와 독립 산출 — 실제 매수 신호는 `entry_ready`(=vcp_detected AND status∈{breakout,actionable})만.
- `status_distribution` : breakout(돌파 중) · actionable(피벗 근접+거래량 마름) ·
  forming(형성 중) · failed(수렴 실패).
- `actionable`/`breakout` 종목이 다음 단계(리스크·진입) 후보.

## 안 하는 것
- 전 종목 스캔(트렌드 통과 종목만) · 공유 파일 갱신 · 수급 신호 · 자동 commit.
- 프로젝트 5신호(눌림목 재가속) — 별도. 이번은 교과서 VCP만.
