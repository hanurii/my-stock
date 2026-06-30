---
name: vcp-audit
description: >
  find-vcp의 VCP 검출기가 미너비니 책 규칙(선행급등·수축·수축별 거래량·거래량 50일선
  마름·돌파)을 얼마나 충실히 구현하는지 종목별 5축 성적표로 진단하는 읽기전용 도구.
  검출기가 찾은 종목(정밀도) + 사용자 정답 VCP 예시(재현율, 과거 구간은 FDR로 fetch)를
  감사해 sepa-vcp-audit.json 에 저장. 검출기는 수정하지 않음(진단까지). 사용자가
  "/vcp-audit", "VCP 책 충실도", "검출기 감사", "내 예시로 검증" 등을 요청할 때 사용.
---

# vcp-audit — VCP 책 충실도 감사

VCP 검출기를 책 규칙의 숫자로 풀어 어디가 어긋나는지 진단한다(차트 눈대조 불필요).
정의: `docs/superpowers/specs/2026-06-30-vcp-book-audit-design.md`.

## 사전 조건
- 검출 종목 감사: `public/data/sepa-vcp-history.json`(= find-vcp-history 산출) 필요.
- 정답 예시 감사: `public/data/vcp_examples.json`에 예시(코드·기간) 채워야 함.
- FDR(FinanceDataReader) 설치(과거 예시 fetch용).

## 실행
```
python scripts/screen_vcp_audit.py
```
- 산출: `public/data/sepa-vcp-audit.json` + 콘솔 5축 O/X 성적표.

### 옵션
- `--no-examples` / `--no-detector` : 한쪽만.
- `--min-advance 25` `--dry-max 0.7` `--breakout-vol 1.4` `--near 5` : 통과 임계값(정답 예시로 보정).

## 결과 보는 법
- 5축: prior_advance·contractions·contraction_volumes·dry_point·breakout 각 O/X.
- 검출기 vcp 평결과 비교해 "책엔 맞는데 검출기는 놓침" 또는 "검출기는 통과인데 책 어긋남"을 찾는다.
- 모든 거래량 판정은 거래량 50일선 기준(책 정의).

## 안 하는 것
- 검출기·find-vcp 수정 · 임계값 자동 최적화 · 공유 파일 갱신 · 자동 commit.
