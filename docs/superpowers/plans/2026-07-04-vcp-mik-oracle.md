# MIK 오라클 확장 + VCP 검출기 견고화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 미너비니 실전 성공 사례 마이클스 컴퍼니(MIK) 2014-11-06을 VCP 검출기의 6번째 정답 오라클로 편입하고, 진단이 시키는 만큼 코일 피벗 로직을 견고화한다.

**Architecture:** 상폐된 미국 종목 MIK의 일봉을 고정 JSON 파일(`vcp_oracle_mik.json`)로 저장해 네트워크 없이 영구 재현한다. `vcp_examples.json`에 `market`·`data_file` 필드를 추가해 로더가 로컬 파일을 읽도록 분기하고(기존 한국 예시 경로 무변경), vcp-audit 5축 성적표 + 코일 검출기 as-of 판정으로 진단한 뒤, 회귀 가드를 지키는 선에서 파라미터 재보정 또는 구조 수정을 적용한다.

**Tech Stack:** Python 3, pytest, 기존 `canslim_lib.vcp` / `canslim_lib.vcp_audit` 모듈, JSON 데이터 파일.

**작업 워크트리:** `C:\Users\hanul\playground\my-stock-vcp-redesign` (브랜치 `feat/vcp-redesign`). 모든 경로는 이 워크트리 루트 기준.

## Global Constraints

- **회귀 가드(모든 태스크가 지켜야 함):** 기존 PASS 3건(데브시스터즈 194480 · 한솔케미칼 014680 · 다올2차 030210)의 돌파일 as-of 판정(vcp_detected=True·status=breakout·피벗 근사)을 깨지 않는다.
- **70종목 한국 유니버스 가드:** find-vcp 재실행 시 분포에 비합리적 변화 없음, 기가비스(420770) `vcp_detected=False` 유지.
- **단위테스트 전부 통과:** 기존 19+ 테스트 + 신규 테스트.
- **봇 검증 자동 우회 금지:** stooq/WSJ 등의 JS 봇 검증을 스크립트로 우회하지 않는다(2026-07-04 차단 확인). 데이터는 공개 미러 또는 사용자 브라우저 다운로드로만 확보.
- **오라클 전용:** MIK를 한국 스크리너 유니버스·후보 파일에 편입하지 않는다.
- **doc-logic-sync:** 로직을 바꾸면 같은 라운드에 스펙(`2026-06-30-vcp-final-coil-pivot-design.md`)과 find-vcp 스킬 문서를 동기화한다.
- **커밋 저자 트레일러:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- **고정 데이터 파일 형식:** `{"dates":[...], "opens":[...], "highs":[...], "lows":[...], "closes":[...], "volumes":[...]}` — `load_series` 반환 형식(6키, dates는 "YYYY-MM-DD" 문자열)과 동일.

---

## Task 1: MIK 일봉 데이터 확보 및 고정 파일 저장

**Files:**
- Create: `public/data/vcp_oracle_mik.json`
- Create: `scripts/_build_mik_oracle.py` (일회성 변환 스크립트, 재현 근거로 커밋)

**Interfaces:**
- Produces: `public/data/vcp_oracle_mik.json` — 6키 dict, MIK(NASDAQ) 상장(2014-06-27경)~2015-06-30 전체 일봉. dates 오름차순, 각 배열 동일 길이, low ≤ open/close ≤ high, 2014-11-06 포함.

> **IPO 확인(2026-07-04):** MIK는 2014년 6월 NASDAQ 상장. 따라서 2014-11-06 돌파는 상장 ~4.5개월 후 형성된 첫 베이스이며, 상장 이전 데이터는 존재하지 않는다. 데이터 범위는 상장일~2015-06으로 잡는다(선행급등 60일 창은 상장 후 구간에서만 계산됨 — 진단 시 유의).

> **데이터 출처 결정(사람 판단 필요):** 자동 경로(FDR/야후, stooq, WSJ, Nasdaq API)는 2026-07-04 모두 차단/상폐제거 확인됨. 아래 순서로 확보하되, 실데이터 없이는 이후 태스크가 무의미하므로 이 태스크는 **데이터 확보를 실제로 완료**해야 한다.

- [ ] **Step 1: 공개 미러 조사**

WebSearch/WebFetch로 다음을 탐색: "MIK Michaels Companies daily historical prices 2014 csv", GitHub의 미국 일봉 아카이브 리포(예: 대량 OHLCV 데이터셋), Kaggle NASDAQ 스냅샷 미러. 상폐 종목이므로 조정 없는 원시 OHLCV여야 함(미너비니 차트는 비조정 가격). 후보 소스를 찾으면 실제 내려받아 2014-11-06 행 존재를 확인.

- [ ] **Step 2: 미러 실패 시 사용자에게 브라우저 다운로드 요청**

Step 1이 실패하면 작업을 멈추고 사용자에게 요청:
> "MIK 상폐 데이터를 스크립트로 못 받습니다(봇 차단). 브라우저에서 이 링크를 열어 CSV를 받아 `public/data/_mik_raw.csv`로 저장해 주세요: `https://stooq.com/q/d/l/?s=mik.us&i=d` (전체 이력, 사람 브라우징은 봇 검증을 정상 통과합니다). 받으시면 알려주세요."

사용자가 파일을 제공할 때까지 대기. (subagent-driven 실행이면 이 태스크는 사용자 상호작용이 필요하므로 메인 세션에서 처리.)

- [ ] **Step 3: 변환 스크립트 작성**

`scripts/_build_mik_oracle.py` — 확보한 원시 소스(CSV 또는 미러 JSON)를 읽어 6키 형식으로 변환·저장. stooq CSV 헤더는 `Date,Open,High,Low,Close,Volume`.

```python
"""MIK 상폐 일봉 원시 소스 → vcp_oracle_mik.json 고정 파일 변환(일회성)."""
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "public" / "data" / "_mik_raw.csv"     # 실제 확보 경로에 맞게 조정
OUT = ROOT / "public" / "data" / "vcp_oracle_mik.json"

def main():
    rows = []
    with SRC.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = r.get("Date") or r.get("date")
            c = r.get("Close") or r.get("close")
            if not d or c in (None, "", "null"):
                continue
            rows.append((
                d.strip(),
                float(r.get("Open") or r.get("open") or c),
                float(r.get("High") or r.get("high") or c),
                float(r.get("Low") or r.get("low") or c),
                float(c),
                int(float(r.get("Volume") or r.get("volume") or 0)),
            ))
    rows.sort(key=lambda x: x[0])
    out = {"dates": [r[0] for r in rows], "opens": [r[1] for r in rows],
           "highs": [r[2] for r in rows], "lows": [r[3] for r in rows],
           "closes": [r[4] for r in rows], "volumes": [r[5] for r in rows]}
    OUT.write_text(json.dumps(out, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"rows={len(rows)} first={out['dates'][0]} last={out['dates'][-1]}")
    print("2014-11-06 in data:", "2014-11-06" in out["dates"])

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 변환 실행 및 무결성 확인**

Run: `python scripts/_build_mik_oracle.py`
Expected: `rows=` 400~500 사이(약 2년 미국 영업일), `first=2013-06-...`, `last=2015-06-...`, `2014-11-06 in data: True`

무결성 수동 점검(Python 한 줄):
```
python -c "import json; d=json.load(open('public/data/vcp_oracle_mik.json')); n=len(d['dates']); assert all(len(d[k])==n for k in d), 'length mismatch'; assert all(d['lows'][i]<=d['opens'][i]<=d['highs'][i] and d['lows'][i]<=d['closes'][i]<=d['highs'][i] for i in range(n)), 'OHLC invariant broken'; print('OK', n, 'rows,', d['dates'][0], '->', d['dates'][-1])"
```
Expected: `OK <n> rows, 2013-06-... -> 2015-06-...` (에러 없이)

- [ ] **Step 5: Commit**

```bash
git add public/data/vcp_oracle_mik.json scripts/_build_mik_oracle.py
git commit -m "data(vcp): MIK 상폐 일봉 고정 오라클 파일(2013-06~2015-06)"
```

---

## Task 2: 예시 로더 로컬 파일 분기 + 단위테스트

**Files:**
- Modify: `scripts/canslim_lib/vcp_audit.py:15-52` (`load_series`)
- Test: `tests/test_vcp_audit.py` (신규 테스트 추가)

**Interfaces:**
- Consumes: Task 1의 `public/data/vcp_oracle_mik.json`.
- Produces: `load_series(code, start, end, fdr_buffer_days=80, data_file=None)` — `data_file` 지정 시 FDR 대신 그 로컬 JSON을 읽어 start−버퍼~end 로 슬라이스한 6키 dict 반환(기존 한국 경로는 `data_file=None`이라 무변경). 파일 없음/키 누락 시 None.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_vcp_audit.py` 하단에 추가:

```python
def test_load_series_local_file(tmp_path):
    import json
    from canslim_lib import vcp_audit
    p = tmp_path / "mik.json"
    p.write_text(json.dumps({
        "dates": ["2014-01-02", "2014-01-03", "2014-01-06", "2014-01-07"],
        "opens": [10, 11, 12, 13], "highs": [11, 12, 13, 14],
        "lows": [9, 10, 11, 12], "closes": [10.5, 11.5, 12.5, 13.5],
        "volumes": [100, 200, 300, 400],
    }), encoding="utf-8")
    s = vcp_audit.load_series("MIK", "2014-01-03", "2014-01-07", data_file=str(p))
    assert s is not None
    # start=2014-01-03 부터(버퍼는 파일 시작에서 clamp), end=2014-01-07 까지 포함
    assert s["dates"][-1] == "2014-01-07"
    assert "2014-01-03" in s["dates"]
    assert len(s["closes"]) == len(s["dates"])


def test_load_series_local_file_missing_returns_none():
    from canslim_lib import vcp_audit
    assert vcp_audit.load_series("MIK", "2014-01-01", "2014-02-01",
                                 data_file="does/not/exist.json") is None
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd C:\Users\hanul\playground\my-stock-vcp-redesign && python -m pytest tests/test_vcp_audit.py::test_load_series_local_file -v`
Expected: FAIL (`load_series() got an unexpected keyword argument 'data_file'`)

- [ ] **Step 3: `load_series`에 data_file 분기 구현**

`scripts/canslim_lib/vcp_audit.py`의 `load_series` 시그니처와 본문 앞부분을 수정. 시그니처에 `data_file: str | None = None` 추가하고, 캐시/FDR 분기 사이에 로컬 파일 분기를 넣는다:

```python
def load_series(code: str, start: str | None = None, end: str | None = None,
                fdr_buffer_days: int = 80, data_file: str | None = None) -> dict | None:
    """start/end 없으면 캐시, data_file 있으면 로컬 JSON, 아니면 FDR. 키 통일."""
    if data_file:
        from pathlib import Path
        import json
        p = Path(data_file)
        if not p.is_absolute():
            p = Path(__file__).resolve().parents[2] / data_file
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        keys = ("dates", "opens", "highs", "lows", "closes", "volumes")
        if not all(k in raw for k in keys) or not raw.get("closes"):
            return None
        dates = raw["dates"]
        # start−버퍼 ~ end 슬라이스(버퍼는 파일 시작에서 clamp)
        lo = 0
        if start:
            s_dt = datetime.strptime(start, "%Y-%m-%d") - timedelta(days=int(fdr_buffer_days * 1.5))
            s_str = s_dt.strftime("%Y-%m-%d")
            cand = [i for i, d in enumerate(dates) if d >= s_str]
            lo = cand[0] if cand else 0
        hi = len(dates)
        if end:
            cand = [i for i, d in enumerate(dates) if d <= end]
            hi = (cand[-1] + 1) if cand else len(dates)
        return {k: raw[k][lo:hi] for k in keys}
    if not start and not end:
        s = ohlcv_matrix.get_series(code)
        ...  # 기존 캐시 경로 그대로
```

(기존 `if not start and not end:` 이하와 FDR 블록은 그대로 둔다.)

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_vcp_audit.py::test_load_series_local_file tests/test_vcp_audit.py::test_load_series_local_file_missing_returns_none -v`
Expected: 2 passed

- [ ] **Step 5: 전체 vcp_audit 테스트 회귀 확인**

Run: `python -m pytest tests/test_vcp_audit.py -v`
Expected: 모두 pass (기존 + 신규 2건)

- [ ] **Step 6: Commit**

```bash
git add scripts/canslim_lib/vcp_audit.py tests/test_vcp_audit.py
git commit -m "feat(vcp-audit): load_series 로컬 고정파일 분기(오라클 재현용)"
```

---

## Task 3: MIK 예시 항목 추가 + audit 스크립트 로컬파일 연결

**Files:**
- Modify: `public/data/vcp_examples.json` (MIK 항목 추가)
- Modify: `scripts/screen_vcp_audit.py:57-78` (예시 루프에서 data_file 전달)

**Interfaces:**
- Consumes: Task 2의 `load_series(..., data_file=...)`.
- Produces: MIK가 vcp-audit 예시 감사에 포함된 `sepa-vcp-audit.json` items.

> **책 명세 복원(사람 판단 필요):** 책엔 날짜만 있으므로 start/end/pivot을 실데이터로 복원한다. Step 1에서 산출한 값이 2014-11-06 돌파와 모순되면(그날 신고가 돌파 없음 등) 멈추고 사용자에게 보고.

- [ ] **Step 1: 실데이터로 베이스·피벗 복원**

`vcp_oracle_mik.json`을 읽어 2014-11-06 전후를 조사하는 진단 스크립트를 임시로 돌린다(별도 파일 저장 불필요, `python -c` 또는 scratchpad 스크립트):
- 2014-11-06의 종가·시가·고가·거래량과 직전 20~60일 흐름 출력.
- 돌파일 직전 횡보 구간(베이스)의 시작(`start`)·마지막 횡보일(`end`)·저항선(피벗 후보 = 베이스 고점 종가) 추정.
- 웹 조사(미너비니 MIK 차트 해설)와 대조해 베이스 구간을 확정.

산출: `start`(YYYY-MM-DD), `end`(2014-11-05 근처, 돌파 직전 마지막 횡보일), `breakout_date`="2014-11-06", `pivot`(달러 가격). 근거를 메모.

**모순 시 중단 조건:** 2014-11-06 종가가 직전 베이스 고점을 상향 돌파하지 않으면 진행 멈추고 사용자에게 실데이터 근거와 함께 보고.

- [ ] **Step 2: vcp_examples.json에 MIK 항목 추가**

`public/data/vcp_examples.json`의 `examples` 배열 끝에 추가(값은 Step 1 산출로 채움):

```json
    {
      "code": "MIK",
      "market": "US",
      "data_file": "public/data/vcp_oracle_mik.json",
      "start": "<Step1 start>",
      "end": "<Step1 end>",
      "breakout_date": "2014-11-06",
      "pivot": <Step1 pivot>,
      "note": "마이클스컴퍼니(미너비니 실전 예시) — 베이스·피벗 복원 근거: <메모>"
    }
```

- [ ] **Step 3: audit 스크립트가 data_file을 로더에 전달하도록 수정**

`scripts/screen_vcp_audit.py`의 예시 루프(line 65 부근) `load_series` 호출에 `data_file` 전달:

```python
            s = vcp_audit.load_series(e["code"], e.get("start"), fetch_end,
                                      data_file=e.get("data_file"))
```

(나머지 루프 로직은 그대로. `data_file` 없는 한국 예시는 None이라 FDR 경로 유지.)

- [ ] **Step 4: vcp-audit 실행 — MIK 5축 성적표 확인**

Run: `python scripts/screen_vcp_audit.py --no-detector`
Expected: 콘솔에 MIK 행이 나오고, 5축(prior_advance·contractions·contraction_volumes·dry_point·breakout) 통과 플래그 표시. `sepa-vcp-audit.json`에 MIK item 저장됨. 기존 한국 예시 5건도 여전히 렌더링(데이터 로드 실패 아님).

- [ ] **Step 5: Commit**

```bash
git add public/data/vcp_examples.json scripts/screen_vcp_audit.py
git commit -m "feat(vcp-audit): MIK 정답 예시 편입 + 로컬파일 로더 연결"
```

---

## Task 4: MIK 돌파일 as-of 코일 검출기 진단

**Files:**
- Create: `docs/superpowers/notes/2026-07-04-mik-oracle-diagnosis.md` (진단 리포트)

**Interfaces:**
- Consumes: `vcp_oracle_mik.json`, `canslim_lib.vcp.evaluate_vcp` / `detect_final_coil`, Task 3의 복원된 pivot.
- Produces: 축별 어긋남 리포트 — 검출기가 MIK를 통과/실패시키는지, 실패면 어느 게이트(코일 파라미터/인식 체인)가 막는지 확정.

- [ ] **Step 1: 돌파일·전일 as-of 판정 산출**

scratchpad 또는 `python -c`로, `vcp_oracle_mik.json`을 읽어 2014-11-06까지 슬라이스한 series로 `evaluate_vcp` 실행:

```python
import json, sys
from pathlib import Path
ROOT = Path("C:/Users/hanul/playground/my-stock-vcp-redesign")
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib.vcp import evaluate_vcp, detect_final_coil, volume_ma
d = json.load(open(ROOT / "public/data/vcp_oracle_mik.json"))
def asof(target):
    idx = [i for i, x in enumerate(d["dates"]) if x <= target][-1]
    sub = {k: d[k][:idx+1] for k in ("dates","opens","highs","lows","closes","volumes")}
    ev = evaluate_vcp(sub)
    print(target, "vcp=", ev["vcp_detected"], "status=", ev["status"],
          "pivot=", ev["pivot_price"], "reason=", ev["reason"],
          "coil_len=", ev["coil_len"], "coil_dry=", ev["coil_dry_mean"], "coil_range=", ev["coil_range_pct"])
for t in ("2014-11-05", "2014-11-06"):
    asof(t)
```

- [ ] **Step 2: 실패 지점 규명(실패한 경우)**

MIK가 돌파일에 vcp_detected=False거나 status≠breakout이면, 어느 게이트가 막는지 좁힌다:
- `reason` 값 확인(`no_contraction_chain` = 인식 체인 실패 / `no_tight_coil` 계열 = 코일 게이트).
- 코일 게이트면 `detect_final_coil`을 직접 호출해 반환 None의 원인(길이 부족/변동폭 초과/거래량 안 마름) 확인. 각 후보 코일 구간의 range_pct·dry_mean을 파라미터 임계와 대조.
- 인식 체인 실패면 `adaptive_zigzag`/`find_contraction_chain` 결과를 출력해 수축이 몇 개 잡히는지 확인.

- [ ] **Step 3: 진단 리포트 작성**

`docs/superpowers/notes/2026-07-04-mik-oracle-diagnosis.md`에 기록: MIK 복원 명세(start/end/pivot), 돌파일 as-of 판정 결과, 통과 여부, 실패면 정확한 게이트·수치. 켐트로스·다올1차의 미해결 구조 문제(횡보 거래량 안 마름)와 같은 뿌리인지 판단. **결론: 수정 불필요 / 파라미터 보정 / 구조 수정 중 하나를 명시.**

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/notes/2026-07-04-mik-oracle-diagnosis.md
git commit -m "docs(vcp): MIK 돌파일 as-of 진단 리포트"
```

---

## Task 5: 조건부 로직 수정 (진단이 시키는 만큼)

> **분기 태스크:** Task 4 결론에 따라 셋 중 하나. 결론이 "수정 불필요"면 이 태스크를 건너뛰고 Task 6으로. 수정을 하는 경우에만 아래 절차를 따른다.

**Files:**
- Modify: `scripts/canslim_lib/vcp.py` (`DEFAULT_PARAMS` 또는 `detect_final_coil` / 인식 로직)
- Modify: `tests/test_vcp.py` (MIK 회귀 테스트 추가)

**Interfaces:**
- Consumes: Task 4 진단 결론.
- Produces: MIK 돌파일 as-of vcp_detected=True·status=breakout(달성 가능한 경우), 회귀 가드 유지.

- [ ] **Step 1: MIK 고정 회귀 테스트 작성(실패 상태)**

`tests/test_vcp.py`에 MIK 돌파일 as-of 기대를 고정하는 테스트 추가. MIK 데이터를 로드해 2014-11-06 as-of `evaluate_vcp` 결과가 vcp_detected=True·status=breakout·피벗이 복원값 ±2% 임을 단언.

```python
def test_mik_oracle_breakout_asof():
    import json
    from pathlib import Path
    from canslim_lib.vcp import evaluate_vcp
    ROOT = Path(__file__).resolve().parents[1]
    d = json.load(open(ROOT / "public/data/vcp_oracle_mik.json", encoding="utf-8"))
    idx = [i for i, x in enumerate(d["dates"]) if x <= "2014-11-06"][-1]
    sub = {k: d[k][:idx+1] for k in ("dates","opens","highs","lows","closes","volumes")}
    ev = evaluate_vcp(sub)
    assert ev["vcp_detected"] is True
    assert ev["status"] == "breakout"
    PIVOT = <Task3 복원 pivot>
    assert abs(ev["pivot_price"] - PIVOT) / PIVOT <= 0.02
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_vcp.py::test_mik_oracle_breakout_asof -v`
Expected: FAIL (수정 전이므로 진단대로 실패)

- [ ] **Step 3: 최소 수정 적용**

Task 4 결론에 따라:
- **파라미터 보정이면:** `DEFAULT_PARAMS`의 해당 코일 파라미터(coil_tight_pct/coil_min_days/coil_max_days/coil_dry_max)를 MIK가 통과하는 최소폭으로 조정. 각 변경에 6예시+회귀 근거 주석.
- **구조 수정이면:** `detect_final_coil` 또는 인식 체인 로직을 수정하되 단위테스트(합성)로 새 동작을 먼저 고정.

- [ ] **Step 4: MIK 테스트 통과 확인**

Run: `python -m pytest tests/test_vcp.py::test_mik_oracle_breakout_asof -v`
Expected: PASS

- [ ] **Step 5: 회귀 가드 — 전체 vcp 테스트**

Run: `python -m pytest tests/test_vcp.py tests/test_vcp_audit.py tests/test_vcp_history.py -v`
Expected: 모두 pass(기존 3예시 PASS 테스트 포함).

- [ ] **Step 6: 70종목 find-vcp 분포 회귀 확인**

Run: `python scripts/screen_vcp.py`
Expected: status_distribution 출력. 수정 전 대비 vcp 수 비합리적 폭증 없음, 기가비스(420770) 조회 시 vcp_detected=False 유지.

기가비스 개별 확인: `python scripts/screen_vcp.py --ticker 420770`
Expected: vcp_detected=False

- [ ] **Step 7: Commit**

```bash
git add scripts/canslim_lib/vcp.py tests/test_vcp.py
git commit -m "tune(vcp): MIK 오라클 통과 위한 <파라미터/구조> 보정 + 회귀 테스트"
```

---

## Task 6: 문서 동기화 + 메모리 기록

**Files:**
- Modify: `docs/superpowers/specs/2026-06-30-vcp-final-coil-pivot-design.md` (§6 성공기준·§8 파라미터/미해결)
- Modify: `.claude/skills/find-vcp/SKILL.md` (로직 변경 시 파라미터·설명)
- Create/Modify: 메모리 파일 + `MEMORY.md` 인덱스 (메인 세션에서)

**Interfaces:**
- Consumes: Task 4·5 결과.
- Produces: 코드와 일치하는 스펙·스킬 문서, MIK 오라클 결과 메모리.

- [ ] **Step 1: final-coil 스펙 동기화**

`2026-06-30-vcp-final-coil-pivot-design.md`:
- §6 성공기준 표에 MIK 결과 추가(PASS/구조적 미충족).
- §8 파라미터 표를 수정값으로 갱신(수정한 경우), 이력에 "2026-07-04 MIK 6예시 편입" 표기.

- [ ] **Step 2: find-vcp 스킬 문서 동기화(로직 변경 시)**

`.claude/skills/find-vcp/SKILL.md`의 파라미터 기본값·설명이 코드와 어긋나면 갱신. 로직 무변경이면 건너뜀.

- [ ] **Step 3: 스펙 상태 라인 갱신**

`2026-07-04-vcp-mik-oracle-design.md` 상태 라인을 "구현 완료(feat/vcp-redesign), MIK <결과>"로 갱신.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-06-30-vcp-final-coil-pivot-design.md docs/superpowers/specs/2026-07-04-vcp-mik-oracle-design.md .claude/skills/find-vcp/SKILL.md
git commit -m "docs(vcp): MIK 오라클 결과로 스펙·스킬 동기화"
```

- [ ] **Step 5: 메모리 기록(메인 세션)**

`C:\Users\hanul\.claude\projects\C--Users-hanul-playground-my-stock\memory\`에 `find-vcp-oracle-mik.md` 작성(type: project): MIK 복원 명세, 돌파일 as-of 결과, 수정 내용, 켐트로스·다올1차 구조 문제와의 관계. `[[vcp-book-examples-gaps]]` `[[find-3c-oracle-nu]]` `[[doc-logic-sync]]` 링크. `MEMORY.md`에 한 줄 인덱스 추가.

---

## 검증 요약(플랜 완료 기준)

- `vcp_oracle_mik.json` 무결성 통과, 2014-11-06 포함.
- MIK vcp-audit 5축 성적표 산출.
- MIK 돌파일 as-of 진단 리포트 존재, 결론 명시.
- (수정한 경우) MIK 회귀 테스트 PASS + 기존 3예시 PASS 유지 + 70종목 분포·기가비스 가드 통과.
- 스펙·스킬·메모리 동기화.
