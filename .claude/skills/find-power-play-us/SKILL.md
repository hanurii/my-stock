---
name: find-power-play-us
description: 미국 SEPA 2단계. 1단계(find-trend-template-us) 통과 종목의 일봉에서 미너비니 파워 플레이(High Tight Flag, 짧고 큰 폭등 뒤 얕고 좁은 횡보)를 탐지해 피벗과 진입상태를 sepa-us-power-play-candidates.json 에 저장한다. 검출기 코드와 값은 한국과 같은 모듈을 그대로 쓴다. 한국 후보 파일은 건드리지 않는다. 사용자가 "/find-power-play-us", "미국 파워플레이", "미국 하이 타이트 플래그" 등을 요청할 때 사용.
---

# find-power-play-us

## 순서
1. `python scripts/verify_frozen_params.py` — 종료 코드가 0 이 아니면 멈춘다
2. `python scripts/screen_detectors_us.py --kind power-play`
3. 검출 수와 **분모**를 함께 보고한다

## 입력
`public/data/sepa-us-trend-candidates.json` (1단계 산출).
대상은 관문 통과(`all_pass`) 종목 **만**이다. 파일에는 평가한 전 종목이 들어 있으므로
`all_pass` 로 거르지 않으면 관문에서 **떨어진** 종목까지 검사하게 된다.
출력이 「1단계 평가 N종목 중 M종목」으로 둘을 다 찍는다.

**관문 임박(`gate_near`)은 넣지 않는다.** 한국 정본은 `all_pass or gate_near`
(`scripts/screen_vcp.py:44`)인데 미국판은 **일부러 좁다** — 27.4년 하네스가
`GATE_NEAR_ALLOW = set()` 로 돌았기 때문이다
(`scripts/backtest_volatility_pilot_us.py:237`, 기본값 `--gate-near off` 는 `:565`).
오늘은 1단계가 `gate_near` 키를 아예 안 내서 두 술어의 결과가 같다. 그래도 좁게 둔다 —
1단계에 관문 완화가 들어오는 날 넓은 술어를 쓰면 27.4년이 **본 적 없는** 종목이
예외도 경고도 없이 후보로 올라온다. 각본이 그 값을 하네스에서 **읽어** 쓰므로,
하네스가 바뀌면 경고가 찍힌다.

## 산출
`public/data/sepa-us-power-play-candidates.json`

- `candidates` 에는 검사한 종목이 **전부** 들어간다(`failed` 포함). 한국판과 같다.
- **「진입」의 자가 둘이다. 갈라 읽어라.**
  - `entry_ready_count` — **27.4년 하네스가 진입으로 «센» 것.** 주문을 거는 대상은
    이것이다. 정의: 패턴 성립 그리고 상태가 `actionable` 그리고 피벗이 있음
    (`scripts/backtest_volatility_pilot_us.py:236`·`:288`).
  - `already_breakout_count` — 패턴은 성립했고 이미 **돌파**한 것.
    **하네스 정의로는 진입이 아니다.** 사용자 진입이 「장 시작 전 피벗 가격 예약」이라
    이미 피벗 위면 예약이 안 걸리거나 추격이 된다. 정보로만 남긴다.
  - 레코드 안의 `entry_ready` 필드와 `module_entry_ready_count` 는 **검출기 모듈**의
    자다(성립 그리고 상태가 breakout·actionable). 위 둘을 합친 값이고, 한국 각본이
    쓰는 이름이다. **주문을 거는 수가 아니다.**
- 상태(`status`)와 성립 여부는 따로 산출되므로 상태만 보고 고르면 안 된다.
  `status_distribution` 은 검출 여부와 무관한 **전체** 레코드 수다.
- `params` 에 그날 쓰인 값이 그대로 실린다. `canslim_lib/power_play.py` 의
  `DEFAULT_PARAMS` 이고 27.4년 백테스트가 돈 값이다.

## 한국판과 다른 한 가지
한국 `screen_power_play.py` 에는 `--universe all`(전수 스캔)과 `--rs-min` 이 있다.
미국판에는 **없다**. 요구사항에 없어서 안 만들었다. 필요하면 그때 만든다.

## 되돌리지 말 것
- 검출기에 `params` 를 넘기지 않는다. 넘기면 얼린 값을 우회하는 것이다.
- 계열은 1단계 산출의 `asof` 까지 잘라서 넘긴다(룩어헤드 방지).

## 안 하는 것
전 종목 스캔 · 한국 파일 갱신 · 자동 커밋.
