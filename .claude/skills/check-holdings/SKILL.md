---
name: check-holdings
description: >
  SEPA 보유 종목 매도규칙 점검. 매수 목록(sepa-holdings.json)의 각 종목을
  미너비니 돌파 후 위반 규칙 6가지(저거래량 돌파·대량 후퇴·연속 저저점·이평선
  이탈·하락일 우세·돌파 실패)로 검사해 🔴손절/🟠조기매도/🟢정상보유 신호를
  sepa-holdings-feedback.json 에 저장한다. OHLCV 캐시 + 후보 파일(피벗)만 읽고
  수급·공유 파일·페이지 코드는 건드리지 않는다. 사용자가 "/check-holdings",
  "보유 점검", "매도규칙 점검", "규칙 위반 잡아줘" 등을 요청할 때 사용.
---

# check-holdings — 보유 종목 매도규칙 점검

매수한 종목이 "계속 들고 있어도 되는지"를 미너비니 매도 규칙으로 점검한다.
정의·근거: `docs/superpowers/specs/2026-07-05-holdings-rules-v2-design.md`
(+ 최초 설계 `2026-07-03-sepa-holdings-feedback-design.md`).

## 사전 조건
- 입력 `public/data/sepa-holdings.json` (사용자가 매수·매도 때 직접 관리).
  없거나 비면 빈 결과로 정상 종료.
- 피벗 참고: `sepa-vcp-candidates.json` / `sepa-power-play-candidates.json`
  (있으면 사용, 없어도 매수 시점 스냅샷 `pivot_price`로 판정).
- 시세: `update-data`가 갱신하는 OHLCV 캐시(추가 수집 없음).

## 실행 (1줄)
```
python scripts/screen_holdings_feedback.py
```
- 산출: `public/data/sepa-holdings-feedback.json`
- 콘솔: 종목별 신호(🔴/🟠/🟢/⚫) + 위반 규칙 목록.

### 옵션
- `--out PATH` : 출력 경로 변경.

## 결과 확인 (6개 규칙)
- ① 저거래량 돌파 · ② 대량 거래 후퇴 · ③ 연속 저저점(저가+거래량) ·
  ④ 이평선 아래 마감 · ⑤ 하락일·나쁜 마감 우세 · ⑥ 돌파 실패(스쿼트+비대칭).
- 신호: 🔴 손절(현재가 ≤ 손절선) > 🟠 조기 매도(위반 ≥ 1건) > 🟢 정상 보유.
- 🟡 소프트 경고(거래량 낮은 저점경신·스쿼트 관찰중)는 위반이 아니라 detail 표기.

## 안 하는 것
- 매수 목록 편집 · 공유/수급 파일 갱신 · 페이지 코드 수정 · 자동 commit.
