# 산출 코드 보존 archive

**목적: 숫자를 낳은 코드가 사라지는 것을 막는다.**

## 왜 있는가

21번 출처 감사(`research/handoff/results/21-provenance-audit.md`)에서 **메모리 12주장 중 8개의 산출 코드를 찾지 못했다.**
원인은 개별 주장의 문제가 아니라 **숫자를 쌓는 방식**이었다:

> 스크래치 스크립트가 숫자를 낸다 → 숫자는 메모리로 간다 → **스크립트는 사라진다.**

그리고 감사 도중 **그 기전이 지금도 돌아가고 있다**는 것이 확인됐다 —
과거 세션 스크래치패드가 `%LOCALAPPDATA%\Temp` 아래에 살아 있었고 그 안에 `.py` 562개가 있었다.
**임시 폴더이고 백업 대상이 아니며, `.cache`는 이미 한 번 통째로 지워진 전례가 있다**(메모리 `cache-loss-and-backup`).

## 무엇이 들어 있는가

세션 ID별 폴더 + `.cache/bt5y/`의 분석 스크립트. **원본 경로 구조를 그대로 보존**했다(같은 이름 파일이 여러 하위 폴더에 있어 평탄화하면 덮인다).

- `aff259ca-…` — `build_events.py`(actionable×주도섹터 판별자 · **룩어헤드 확인된 코드**), `build_passmatrix.py`, `finalize_newcomer.py`
- `c9b9862c-…` — `cf.py`·`classify.py`·`pattern_test.py`·`regime_test.py`·`_liq.py` 등
- `990b6503-…` — `repro_edges.py`
- `_cache-bt5y/` — `cmp_exit.py`(**코스피 +109%가 하드코딩 print문이었던 파일**), `analyze2.py` 등

## 쓰는 법

**이 archive는 실행용이 아니라 대조용이다.** 경로·의존성이 원래 세션 기준이라 그대로 돌지 않을 수 있다.
숫자의 출처를 확인할 때 **grep으로 값·필드명을 찾아** 읽는다.

## 규칙

**메모리에 숫자를 넣을 때는 커밋된 스크립트 경로를 함께 적는다. 없으면 넣지 않는다.**

---

## 🚨 실행 금지 — 네트워크를 부르는 파일이 들어 있다

`probe1.py`(Naver) · `probe*_krx.py`(KRX) · `probe5_kis.py`(KIS) · `short_probe.py` 등.
**이 archive는 읽기 전용이다.** 실행하면 API 차단(메모리 `cold-rebuild-trips-api-protection`)이나 캐시 손상을 부를 수 있다.
확인이 필요하면 **grep으로 읽는다.**

## `_inputs/` — 스크립트가 읽는 중간 산출

21b 재감사에서 드러난 것: **`.py`만 보존하면 막은 게 아니다.**
많은 스크립트가 첫 줄에서 `os.environ['SCRATCH']` 아래의 중간 JSON을 읽는데,
그 입력이 없으면 **"코드는 있는데 재현 불가"**로 문제가 옮겨갈 뿐이다.

→ archive의 `.py`가 이름으로 참조하는 JSON 중 **20MB 이하 75개(약 51MB)**를 `<세션ID>/_inputs/`에 넣었다.
20MB 초과 1개는 제외했다. 원본 스크래치 JSON 총량은 1.1GB+ 규모라 전량 보존은 하지 않았다.

**한계**: 파일명으로만 찾았으므로 **변수로 조립되는 경로는 놓친다.**
