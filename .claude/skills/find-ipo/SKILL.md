---
name: find-ipo
description: >
  SEPA 형제 스킬(find-vcp·find-power-play·find-3c 와 같은 층). 1단계
  (find-trend-template --ipo-track)가 산출한 IPO 트랙(상장 20~199거래일 대체
  관문) 평가를 읽어 통과 종목·통과 임박(5~6/7)·과열 딱지(iRS≥90/고점 코앞/조기
  통과)를 정리해 sepa-ipo-candidates.json 에 저장한다. 재평가 없음(관문 산출
  소비만), 비차단. 사용자가 "/find-ipo", "IPO 후보", "신규상장 뭐 있어",
  "IPO 트랙 정리" 등을 요청할 때 사용.
---

# find-ipo — IPO 트랙(신규상장) 후보 정리

1단계 관문의 `ipo_candidates`(대체 7조건 평가)를 소비해 사람이 볼 판으로 정리한다.
설계·검증: `docs/superpowers/specs/2026-08-08-ipo-exception-track-design.md` ·
`docs/research/2026-08-08-ipo-track-replay-findings.md` (위너 재현율 92% 합격,
-10% 손절 부적합, iRS≥90·고점 코앞·상장 60일 미만 통과 = 과열 열세 구간).

## 사전 조건
- `find-trend-template` 이 `--ipo-track` 으로 먼저 실행돼 있어야 함
  (`sepa-trend-candidates.json` 에 `ipo_candidates` 존재).

## 실행 (1줄)
```
python scripts/screen_ipo_track.py
```
- 산출: `public/data/sepa-ipo-candidates.json`
  — `pass`(통과, `overheat` 딱지 배열 포함) · `near_miss`(5~6/7, 탈락 사유) ·
  `exit_caution`(청산 주의문).
- 콘솔: 🐣 통과 목록(과열 딱지) + ◔ 임박 목록 + 청산 주의.
- **비차단**: 입력에 `ipo_candidates` 없으면(관문이 플래그 없이 돌았음) 경고 한 줄
  후 이전 산출 유지.

## 결과 해석
- **과열 딱지**는 표시일 뿐 차단이 아님 — 검증 소표본(n<80) 기준 열세 구간 경고.
- **청산 주의**: 통과 종목에 기본 -10% 손절 부적합(재현상 91%가 4일 내 손절).
  IPO 전용 청산 규칙은 미확립 — 매매 전환은 별도 검토.

## 안 하는 것
- 재평가(관문 산출 소비만) · 패턴 검출(`--include-ipo` 는 온디맨드 별도) ·
  매수 추천 편입 · 자동 commit(부모 `sepa`가 커밋).
