---
name: find-trend-template-us
description: 미국 SEPA 발굴의 첫 관문. Minervini 트렌드 템플레이트 8조건과 RS 80 으로 NASDAQ·NYSE·NYSEMKT 종목을 추려 sepa-us-trend-candidates.json 에 저장한다. 한국 후보 파일과 공유 데이터는 건드리지 않는다. 사용자가 "/find-trend-template-us", "미국 1단계", "미국 추세 통과 종목" 등을 요청할 때 사용.
---

# find-trend-template-us

## 순서
1. `python scripts/verify_frozen_params.py` — 다르면 멈춘다
2. `python scripts/screen_trend_template_us.py`
3. 통과 수와 분모를 보고한다

## 뺀 것
국면 자동 필터 · DART 실적 · 외국인 지분율 — 까닭은 스크립트 머리말에 있다.

## 되돌리지 말 것
RS 는 정지·유동성을 **거른 뒤** 잰다. 한국판은 전 시장으로 재는데 미국판은
**일부러 다르다** — 27.4년 백테스트가 거른 뒤 쟀기 때문이다. 되돌리면 백테스트가
본 적 없는 종목이 후보로 올라온다. 까닭은 `scripts/screen_trend_template_us.py`
머리말에 있다.

## 자료
`us_matrix.load_latest()` 가 합본(`tail.json`)이 있으면 그것을, 없으면 뼈대
(`base.json`)를 읽는다. 어느 것을 읽었는지 출력 첫 줄에 찍힌다 — 갱신했는데
`뼈대만` 이라고 나오면 `/update-data-us` 의 꼬리 단계가 안 돈 것이다.
