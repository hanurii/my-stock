# 미국 전용 SEPA 스킬 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한국 `/sepa` 파이프라인과 같은 구조의 미국 전용 스킬 여섯을 만든다.

**Architecture:** Sharadar에서 310거래일을 추려 고정 뼈대(json)를 만들고, 야후에서 날마다 꼬리를
붙인다. 읽는 쪽 계약을 한국 `ohlcv_matrix`와 같게 지켜 관문 코드와 검출기 넷을 손대지 않는다.

**Tech Stack:** Python 3 · `zipfile`/`csv` 흘려 읽기 · `yfinance` 1.2.0 · pytest

**Spec:** `docs/superpowers/specs/2026-09-10-us-sepa-skill-design.md`

## Global Constraints

- **검출기·관문의 수를 하나도 바꾸지 않는다.** 27.4년 백테스트(커밋 `e8cd65ae`)가 그 값으로 돌았다.
- **야후는 `Close`를 쓴다.** `Adj Close`가 아니다.
- **310거래일.** `trend_template.py:44` `needed = window + end_offset`에서 온 수다. 고르지 않았다.
- **커밋·푸시는 사용자가 요청할 때만.** 구현자는 커밋하지 않는다 — 파일만 고치고 보고한다.
- Sharadar 원자료(`.cache/sharadar/`)는 저장소에 넣지 않는다.
- 사용자에게 보이는 글은 평이한 한국어. 이모지·과도한 굵은 글씨 금지.

## 이미 있어서 안 짓는 것

`scripts/us_loader.py`가 다음을 **이미** 한다. 다시 만들지 않는다.

| 함수 | 하는 일 |
|---|---|
| `load_tickers(variant="base")` | 유니버스 — 거래소 3곳 · 우선주/ADR/2차클래스 제외 · SPAC(6770) 제외 |
| `build_all(start, end, ...)` | 한 번 흘려 읽어 `(universe_by_date, packed_turnover, full_series, meta)` |
| `_iter_prices(codes, lo, hi)` | 가격 CSV 한 번 통과. 아무것도 쌓지 않음 |

`build_all`이 내는 series 모양은 `{dates, opens, highs, lows, closes, volumes}`다.
**`timestamps`가 빠져 있다** — `screen_trend_template.py:96`이 그것을 읽는다.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `scripts/canslim_lib/us_matrix.py` (새로) | 뼈대 만들기·저장·읽기. `ohlcv_matrix`의 읽기 계약을 맞춘다 |
| `scripts/us_seam.py` (새로) | 분할 검사 + 야후 꼬리 붙이기 |
| `scripts/verify_frozen_params.py` (새로) | 모든 수가 `e8cd65ae`와 같은지 검산 |
| `tests/test_us_matrix.py` (새로) | 위 셋의 시험 |
| `.claude/skills/update-data-us/SKILL.md` (새로) | 스킬 여섯 |
| `.claude/skills/find-trend-template-us/SKILL.md` | |
| `.claude/skills/find-vcp-us/SKILL.md` | |
| `.claude/skills/find-power-play-us/SKILL.md` | |
| `.claude/skills/find-3c-us/SKILL.md` | |
| ~~`.claude/skills/find-ipo-us/SKILL.md`~~ | 🔴 **취소됨 2026-09-11**(사용자 결정 — 27.4년이 IPO 트랙을 안 돌렸다. CLAUDE.md §7) |
| `.claude/skills/sepa-us/SKILL.md` | 부모 |

---

### Task 1: 뼈대 만들기

**Files:**
- Create: `scripts/canslim_lib/us_matrix.py`
- Test: `tests/test_us_matrix.py`

**Interfaces:**
- Consumes: `us_loader.build_all(start, end, variant, build_universe)` → `(universe, packed, full, meta)`
- Produces:
  - `BASE_PATH: Path` — `.cache/us/base.json`
  - `TRIM_BARS: int = 310`
  - `to_timestamp(d: str) -> int`
  - `trim_series(s: dict, n: int = TRIM_BARS) -> dict`
  - `build_base(start: str, end: str, out: Path | None = None) -> dict` — meta를 돌려준다
  - 저장 모양: `{"asof": str, "trim": int, "series": {code: {dates, opens, highs, lows, closes, volumes, timestamps}}}`

- [ ] **Step 1: 실패하는 시험을 쓴다**

```python
# tests/test_us_matrix.py
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib import us_matrix


def test_trim_keeps_last_n_bars():
    s = {"dates": [f"2026-01-{i:02d}" for i in range(1, 21)],
         "opens": list(range(20)), "highs": list(range(20)),
         "lows": list(range(20)), "closes": list(range(20)),
         "volumes": list(range(20))}
    out = us_matrix.trim_series(s, 5)
    assert out["dates"] == ["2026-01-16", "2026-01-17", "2026-01-18",
                            "2026-01-19", "2026-01-20"]
    assert out["closes"] == [15, 16, 17, 18, 19]
    assert len(out["timestamps"]) == 5


def test_trim_keeps_short_series_whole():
    s = {"dates": ["2026-01-01", "2026-01-02"], "opens": [1, 2], "highs": [1, 2],
         "lows": [1, 2], "closes": [1, 2], "volumes": [1, 2]}
    out = us_matrix.trim_series(s, 310)
    assert len(out["dates"]) == 2
```

- [ ] **Step 2: 시험이 실패하는지 돌려 본다**

Run: `python -m pytest tests/test_us_matrix.py -v`
Expected: FAIL — `ModuleNotFoundError` 또는 `AttributeError: trim_series`

- [ ] **Step 3: 가장 작은 구현을 쓴다**

```python
# scripts/canslim_lib/us_matrix.py
"""미국(Sharadar) 시세 뼈대 — 한국 ohlcv_matrix 의 읽기 계약을 맞춘다.

★ 왜 있나: Sharadar 결제가 2026-09 로 끝난다. 뼈대를 한 번 만들어 얼리고
  야후 꼬리를 날마다 붙인다. 원본(45,317,834행·3~4GB)은 다시 열지 않는다.

★ 310 은 고른 수가 아니다 — trend_template.py:44 `needed = window + end_offset`.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_PATH = ROOT / ".cache" / "us" / "base.json"
TRIM_BARS = 310
KEYS = ("dates", "opens", "highs", "lows", "closes", "volumes")


def to_timestamp(d: str) -> int:
    """"YYYY-MM-DD" → 초 단위 UTC 타임스탬프. us_seam 도 쓴다(사적 이름 금지)."""
    return int(datetime.strptime(d, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def trim_series(s: dict, n: int = TRIM_BARS) -> dict:
    """마지막 n 봉만 남기고 timestamps 를 붙인다. n 보다 짧으면 그대로 둔다."""
    out = {k: list(s.get(k) or [])[-n:] for k in KEYS}
    out["timestamps"] = [to_timestamp(d) for d in out["dates"]]
    return out
```

- [ ] **Step 4: 시험이 통과하는지 돌려 본다**

Run: `python -m pytest tests/test_us_matrix.py -v`
Expected: PASS 2개

- [ ] **Step 5: `build_base` 를 더한다**

```python
def build_base(start: str, end: str, out: Path | None = None) -> dict:
    """Sharadar 를 한 번 흘려 읽어 뼈대를 만든다.

    start 는 넉넉히 잡는다(24개월). 종목마다 마지막 TRIM_BARS 봉으로 다듬으므로
    「몇 개월이면 되나」를 고를 필요가 없다.
    """
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import us_loader

    _, _, full, meta = us_loader.build_all(start, end, build_universe=False)
    series = {c: trim_series(s) for c, s in full.items() if s.get("dates")}
    asof = max((s["dates"][-1] for s in series.values() if s["dates"]), default="")
    path = out or BASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        {"asof": asof, "trim": TRIM_BARS, "series": series},
        ensure_ascii=False), encoding="utf-8")
    return {"asof": asof, "n_codes": len(series),
            "n_rows": sum(len(s["dates"]) for s in series.values()),
            "n_full": sum(1 for s in series.values()
                          if len(s["dates"]) >= TRIM_BARS),
            "path": str(path), **meta}
```

- [ ] **Step 6: 실제 자료로 한 번 돌려 수를 출력한다**

Run:
```bash
python -c "import sys; sys.path.insert(0,'scripts'); from canslim_lib import us_matrix; \
import json; m=us_matrix.build_base('2024-09-01','2026-12-31'); \
print(json.dumps({k:m[k] for k in ('asof','n_codes','n_rows','n_full')}, ensure_ascii=False))"
```
Expected: `asof`가 Sharadar 마지막 날과 같고, `n_codes` **4,648**,
`n_full` **4,078**(87.7%). (2026-09-11 정정 — 옛 「7,400·79%」는 거르기 «전» 수)

- [ ] **Step 7: 커밋** (사용자 요청이 있을 때만)

```bash
git add scripts/canslim_lib/us_matrix.py tests/test_us_matrix.py
git commit -m "feat(us): Sharadar 뼈대 빌더 — 310봉 다듬기 + timestamps"
```

---

### Task 2: 읽기 계약

**Files:**
- Modify: `scripts/canslim_lib/us_matrix.py`
- Modify: `tests/test_us_matrix.py`

**Interfaces:**
- Produces:
  - `load_base(path: Path | None = None) -> dict` — 한 번 읽어 캐시에 둔다
  - `get_series(code: str, days_back: int | None = None) -> dict | None`
    — `ohlcv_matrix.get_series`와 같은 계약. 없으면 `None`

- [ ] **Step 1: 실패하는 시험을 쓴다**

```python
def test_get_series_returns_none_for_unknown(tmp_path):
    p = tmp_path / "base.json"
    p.write_text('{"asof":"2026-09-09","trim":310,"series":{}}', encoding="utf-8")
    us_matrix.load_base(p)
    assert us_matrix.get_series("NOSUCH") is None


def test_get_series_has_all_consumer_keys(tmp_path):
    p = tmp_path / "base.json"
    s = {"dates": ["2026-09-08", "2026-09-09"], "opens": [1.0, 2.0],
         "highs": [1.0, 2.0], "lows": [1.0, 2.0], "closes": [1.0, 2.0],
         "volumes": [10.0, 20.0], "timestamps": [1, 2]}
    p.write_text(json.dumps({"asof": "2026-09-09", "trim": 310,
                             "series": {"AAPL": s}}), encoding="utf-8")
    us_matrix.load_base(p)
    got = us_matrix.get_series("AAPL")
    for k in ("dates", "opens", "highs", "lows", "closes", "volumes", "timestamps"):
        assert k in got, f"소비자가 읽는 키 {k} 가 없다"
```

- [ ] **Step 2: 시험이 실패하는지 돌려 본다**

Run: `python -m pytest tests/test_us_matrix.py -v`
Expected: FAIL — `AttributeError: load_base`

- [ ] **Step 3: 구현한다**

```python
_BASE: dict | None = None


def load_base(path: Path | None = None) -> dict:
    global _BASE
    p = path or BASE_PATH
    _BASE = json.loads(p.read_text(encoding="utf-8"))
    return _BASE


def get_series(code: str, days_back: int | None = None) -> dict | None:
    """한국 ohlcv_matrix.get_series 와 같은 계약."""
    if _BASE is None:
        load_base()
    s = (_BASE or {}).get("series", {}).get(code)
    if not s:
        return None
    if days_back is None:
        return s
    return {k: (v[-days_back:] if isinstance(v, list) else v)
            for k, v in s.items()}
```

- [ ] **Step 4: 시험이 통과하는지 돌려 본다**

Run: `python -m pytest tests/test_us_matrix.py -v`
Expected: PASS 4개

- [ ] **Step 5: 소비자가 읽는 키를 전수로 확인한다**

Run:
```bash
grep -rnoE '(series|mtx)(\.get\(|\[)"[a-z_]+"' \
  scripts/screen_trend_template.py scripts/canslim_lib/vcp.py \
  scripts/canslim_lib/power_play.py scripts/canslim_lib/cheat.py \
  scripts/canslim_lib/ipo_track.py | grep -oE '"[a-z_]+"' | sort -u
```
Expected: 나오는 키가 `KEYS + ("timestamps",)` 안에 다 있어야 한다.
`foreign_rates`가 나오면 한국 전용이므로 빈 리스트로 둔다.

- [ ] **Step 6: 커밋** (사용자 요청이 있을 때만)

```bash
git add scripts/canslim_lib/us_matrix.py tests/test_us_matrix.py
git commit -m "feat(us): 읽기 계약 — ohlcv_matrix.get_series 와 같은 모양"
```

---

### Task 3: 분할 검사

**Files:**
- Create: `scripts/us_seam.py`
- Modify: `tests/test_us_matrix.py`

**Interfaces:**
- Produces: `check_splits(codes: list[str], since: str, until: str) -> dict`
  — `{"splits": [{"code","date","ratio"}], "failed": [code, ...]}`
  🔴 **둘 다 비어야 이어 붙여도 된다.** `failed` 가 있으면 그 종목은
  「분할 없음」이 아니라 **「못 봤음」**이다 — 부르는 쪽이 «코드»로 그것을 가릴 수 있어야 한다.

- [ ] **Step 1: 실패하는 시험을 쓴다**

```python
def test_check_splits_empty_window_returns_empty(monkeypatch):
    import us_seam

    class FakeTicker:
        def __init__(self, code): pass
        @property
        def splits(self):
            import pandas as pd
            return pd.Series(dtype=float)

    monkeypatch.setattr(us_seam.yf, "Ticker", FakeTicker)
    assert us_seam.check_splits(["AAPL"], "2026-09-09", "2026-09-10") == []


def test_check_splits_finds_one(monkeypatch):
    import us_seam
    import pandas as pd

    class FakeTicker:
        def __init__(self, code): pass
        @property
        def splits(self):
            return pd.Series([2.0], index=pd.to_datetime(["2026-09-10"]))

    monkeypatch.setattr(us_seam.yf, "Ticker", FakeTicker)
    got = us_seam.check_splits(["APH"], "2026-09-09", "2026-09-11")
    assert got == [{"code": "APH", "date": "2026-09-10", "ratio": 2.0}]
```

- [ ] **Step 2: 시험이 실패하는지 돌려 본다**

Run: `python -m pytest tests/test_us_matrix.py -k split -v`
Expected: FAIL — `ModuleNotFoundError: us_seam`

- [ ] **Step 3: 구현한다**

```python
# scripts/us_seam.py
"""이음매 — Sharadar 뼈대에 야후 꼬리를 붙인다.

★ 붙이기 전에 그 창의 분할을 검사한다. 있으면 멈춘다.
   Sharadar 역사는 분할 전 가격이고 야후 꼬리는 분할 후 가격이라
   이음매에서 배수만큼 가짜 계단이 난다. 우리 규칙은 그것을 급락으로 읽는다.
   실측(2026-08-21 기준 20일 창): 분할 29개, 그중 대형주 하나(APH 2배).

★ 야후는 Close 를 쓴다. Adj Close 가 아니다.
   분할 없는 대형주 10개에서 Sharadar 와 최대 0.001% 안에서 맞았고,
   Adj Close 는 배당만큼 벌어진다(최대 1.331%).
"""
from __future__ import annotations

import yfinance as yf


def check_splits(codes: list[str], since: str, until: str) -> list[dict]:
    """[since, until) 안에 분할이 있는 종목을 낸다. 빈 리스트면 이어도 된다."""
    out = []
    for c in codes:
        try:
            sp = yf.Ticker(c).splits
        except Exception:
            continue
        if sp is None or len(sp) == 0:
            continue
        for ts, ratio in sp.items():
            d = str(ts)[:10]
            if since <= d < until:
                out.append({"code": c, "date": d, "ratio": float(ratio)})
    return out
```

- [ ] **Step 4: 시험이 통과하는지 돌려 본다**

Run: `python -m pytest tests/test_us_matrix.py -k split -v`
Expected: PASS 2개

- [ ] **Step 5: 커밋** (사용자 요청이 있을 때만)

```bash
git add scripts/us_seam.py tests/test_us_matrix.py
git commit -m "feat(us): 이음매 분할 검사"
```

---

### Task 4: 야후 꼬리 붙이기

**Files:**
- Modify: `scripts/us_seam.py`
- Modify: `tests/test_us_matrix.py`

**Interfaces:**
- Consumes: `check_splits(codes, since, until)`
- Produces:
  - `TAIL_PATH: Path` — `.cache/us/tail.json`
  - `fetch_tail(codes: list[str], since: str) -> dict` — `{code: {dates, opens, highs, lows, closes, volumes}}`
  - `attach(base: dict, tail: dict) -> dict` — 뼈대에 꼬리를 붙여 새 dict 를 낸다.
    같은 날짜가 겹치면 **뼈대를 남긴다**(Sharadar 가 정본)

- [ ] **Step 1: 실패하는 시험을 쓴다**

```python
def test_attach_appends_and_keeps_base_on_overlap():
    import us_seam
    base = {"series": {"AAPL": {
        "dates": ["2026-09-08", "2026-09-09"], "opens": [1.0, 2.0],
        "highs": [1.0, 2.0], "lows": [1.0, 2.0], "closes": [1.0, 2.0],
        "volumes": [10.0, 20.0], "timestamps": [1, 2]}}}
    tail = {"AAPL": {
        "dates": ["2026-09-09", "2026-09-10"], "opens": [99.0, 3.0],
        "highs": [99.0, 3.0], "lows": [99.0, 3.0], "closes": [99.0, 3.0],
        "volumes": [99.0, 30.0]}}
    got = us_seam.attach(base, tail)["series"]["AAPL"]
    assert got["dates"] == ["2026-09-08", "2026-09-09", "2026-09-10"]
    assert got["closes"] == [1.0, 2.0, 3.0], "겹친 날은 뼈대가 남아야 한다"
    assert len(got["timestamps"]) == 3
```

- [ ] **Step 2: 시험이 실패하는지 돌려 본다**

Run: `python -m pytest tests/test_us_matrix.py -k attach -v`
Expected: FAIL — `AttributeError: attach`

- [ ] **Step 3: 구현한다**

```python
import json
from pathlib import Path

from canslim_lib.us_matrix import KEYS, to_timestamp

ROOT = Path(__file__).resolve().parents[1]
TAIL_PATH = ROOT / ".cache" / "us" / "tail.json"


def fetch_tail(codes: list[str], since: str) -> dict:
    """since 다음날부터 오늘까지. Close 를 쓴다(Adj Close 아님)."""
    df = yf.download(codes, start=since, interval="1d", auto_adjust=False,
                     group_by="ticker", threads=True, progress=False)
    out = {}
    for c in codes:
        try:
            d = df[c].dropna(how="all")
        except Exception:
            continue
        if d.empty:
            continue
        out[c] = {
            "dates": [str(i)[:10] for i in d.index],
            "opens": [float(x) for x in d["Open"]],
            "highs": [float(x) for x in d["High"]],
            "lows": [float(x) for x in d["Low"]],
            "closes": [float(x) for x in d["Close"]],
            "volumes": [float(x) for x in d["Volume"]],
        }
    return out


def attach(base: dict, tail: dict) -> dict:
    """뼈대에 꼬리를 붙인다. 겹친 날짜는 뼈대를 남긴다(Sharadar 가 정본)."""
    out = {k: v for k, v in base.items() if k != "series"}
    ser = {}
    for c, s in base.get("series", {}).items():
        t = tail.get(c)
        if not t:
            ser[c] = s
            continue
        have = set(s["dates"])
        add = [i for i, d in enumerate(t["dates"]) if d not in have]
        if not add:
            ser[c] = s
            continue
        new = {k: list(s[k]) + [t[k][i] for i in add] for k in KEYS}
        new["timestamps"] = [to_timestamp(d) for d in new["dates"]]
        ser[c] = new
    out["series"] = ser
    out["asof"] = max((s["dates"][-1] for s in ser.values() if s["dates"]),
                      default=base.get("asof", ""))
    return out
```

- [ ] **Step 4: 시험이 통과하는지 돌려 본다**

Run: `python -m pytest tests/test_us_matrix.py -v`
Expected: PASS 7개

- [ ] **Step 5: 커밋** (사용자 요청이 있을 때만)

```bash
git add scripts/us_seam.py tests/test_us_matrix.py
git commit -m "feat(us): 야후 꼬리 붙이기 — 겹친 날은 Sharadar 를 남긴다"
```

---

### Task 5: 값 동결 검산기

**Files:**
- Create: `scripts/verify_frozen_params.py`

**Interfaces:**
- Produces: `main() -> int` — 다르면 1, 같으면 0. 표를 찍는다.

설계 문서: "스킬을 만들 때 모든 수가 `e8cd65ae`의 값과 같은지 출력으로 검산한다."

- [ ] **Step 1: 구현한다**

```python
# scripts/verify_frozen_params.py
"""검출기·관문의 수가 27.4년 백테스트 때와 같은지 검산한다.

★ 왜: 27.4년 백테스트(커밋 e8cd65ae)가 그 값으로 돌았다.
  바꾸면 그 검증이 이 스킬의 검증이 아니게 된다.
  주장으로 두지 않고 출력값으로 낸다.
"""
from __future__ import annotations

import ast
import subprocess
import sys

FROZEN = "e8cd65ae"
TARGETS = [
    ("scripts/canslim_lib/vcp.py", "DEFAULT_PARAMS"),
    ("scripts/canslim_lib/power_play.py", "DEFAULT_PARAMS"),
    ("scripts/canslim_lib/cheat.py", "DEFAULT_PARAMS"),
    ("scripts/canslim_lib/ipo_track.py", "DEFAULT_PARAMS"),
]


def _dict_at(src: str, name: str) -> dict:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                tgt = getattr(t, "id", None) or getattr(t, "attr", None)
                if tgt == name:
                    return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign):
            if getattr(node.target, "id", None) == name and node.value:
                return ast.literal_eval(node.value)
    return {}


def main() -> int:
    bad = 0
    for path, name in TARGETS:
        now = _dict_at(open(path, encoding="utf-8").read(), name)
        old_src = subprocess.run(["git", "show", f"{FROZEN}:{path}"],
                                 capture_output=True, text=True,
                                 encoding="utf-8").stdout
        old = _dict_at(old_src, name)
        keys = sorted(set(now) | set(old))
        diff = [k for k in keys if now.get(k) != old.get(k)]
        mark = "같음" if not diff else "다름"
        print(f"{path}  {name}  {len(keys)}개  {mark}")
        for k in diff:
            print(f"    {k}: {FROZEN}={old.get(k)!r}  지금={now.get(k)!r}")
            bad += 1
    print(f"\n다른 값 {bad}개")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 돌려 본다**

Run: `python scripts/verify_frozen_params.py`
Expected: 네 파일 다 "같음", 마지막 줄 `다른 값 0개`, 종료 코드 0.

- [ ] **Step 3: 일부러 틀리게 해서 잡히는지 본다** (질 수 있는 관문인지 확인)

Run:
```bash
cp scripts/canslim_lib/vcp.py /tmp/vcp.bak
sed -i 's/"dry_max": 0.82/"dry_max": 0.83/' scripts/canslim_lib/vcp.py
python scripts/verify_frozen_params.py; echo "종료 코드=$?"
cp /tmp/vcp.bak scripts/canslim_lib/vcp.py
```
Expected: `dry_max` 줄이 찍히고 종료 코드 1. 되돌린 뒤 다시 돌리면 0.

- [ ] **Step 4: 커밋** (사용자 요청이 있을 때만)

```bash
git add scripts/verify_frozen_params.py
git commit -m "feat(us): 검출기 값 동결 검산기"
```

---

### Task 6: `update-data-us` 스킬

**Files:**
- Create: `.claude/skills/update-data-us/SKILL.md`

**Interfaces:**
- Consumes: `us_matrix.build_base` · `us_seam.check_splits` · `us_seam.fetch_tail` · `us_seam.attach`
- Produces: `.cache/us/base.json` · `.cache/us/tail.json`

- [ ] **Step 1: 스킬 파일을 쓴다**

```markdown
---
name: update-data-us
description: 미국(Sharadar+야후) 시세 뼈대와 꼬리를 갱신한다. Sharadar 를 한 번 흘려 읽어 310거래일 뼈대를 만들고(9월에 한 번), 그 뒤로는 야후에서 꼬리만 날마다 붙인다. 붙이기 전에 그 창의 분할을 검사하고 있으면 멈춘다. 사용자가 "/update-data-us", "미국 시세 갱신", "sepa-us 전에 데이터 업데이트" 등을 요청할 때 사용.
---

# update-data-us

## 순서

1. `.cache/us/base.json` 이 없으면 뼈대를 만든다:
   `us_matrix.build_base("2024-09-01", "2026-12-31")`
   실측(2026-09-10) 126초. 종목 4,648 · 그중 310봉을 채우는 것 4,078(87.7%).
   (옛 수 「7,400 · 79%」는 유니버스 규칙을 걸기 «전» 수다.
    시간은 까닭이 «다르다» — 「54초」는 «재는 자리»가 달랐고 자료도 옛 것이었다.
    거르면 종목이 «줄어드니» 거르기가 «느려지는» 까닭일 수는 없다.
    정본: 설계 문서 95-99행. 2026-09-11 정정)
2. 뼈대 `asof` 다음날부터 오늘까지 **분할을 검사한다**:
   `r = us_seam.check_splits(codes, since=asof, until=today)`
3. **`r["splits"]` 가 비어 있지 않으면 멈추고 사용자에게 알린다.** 목록을 보인다.
   해결: Sharadar 를 다시 받아 뼈대를 새로 만든다(2026-09 까지만 가능).
4. 🔴 **`r["failed"]` 가 비어 있지 않아도 멈춘다.** 그 종목들은 「분할 없음」이 아니라
   **「못 봤음」**이다. 몇 개인지와 종목을 보이고, 다시 돌릴지 사용자에게 묻는다.
5. 둘 다 비었으면 꼬리를 받아 붙인다: `fetch_tail` → `attach` → `.cache/us/tail.json`

## 왜 이런가

- Sharadar 결제가 2026-09 로 끝난다. 뼈대는 그때 얼고 꼬리만 자란다.
- 야후는 `Close` 를 쓴다. `Adj Close` 는 배당만큼 벌어진다.
- 겹친 날짜는 뼈대(Sharadar)를 남긴다.
- 분할 검사를 건너뛰면 이음매에서 배수만큼 가짜 계단이 난다.
  야후가 분할을 반영하지 않는 종목이 있다(표본 10개 중 2개).

## 안 하는 것

- 유니버스 다시 세우기 — `us_loader.load_tickers` 가 한다
- 종목 정보 갱신 — Sharadar 가 2026-09 로 멈춘다. 신규 상장이 안 들어온다(미해결)
```

- [ ] **Step 2: 스킬이 읽히는지 본다**

Run: `ls .claude/skills/update-data-us/SKILL.md && head -3 .claude/skills/update-data-us/SKILL.md`
Expected: 파일이 있고 frontmatter `name` 이 보인다.

- [ ] **Step 3: 커밋** (사용자 요청이 있을 때만)

```bash
git add .claude/skills/update-data-us/SKILL.md
git commit -m "feat(us): update-data-us 스킬"
```

---

### Task 7: `find-trend-template-us` 스킬

**Files:**
- Create: `.claude/skills/find-trend-template-us/SKILL.md`
- Create: `scripts/screen_trend_template_us.py`

**Interfaces:**
- Consumes: `us_matrix.get_series` · `us_loader.load_tickers` · `trend_template.evaluate` · `minervini_filter`
- Produces: `public/data/sepa-us-trend-candidates.json`

- [ ] **Step 1: 한국 스크립트가 무엇을 부르는지 센다**

Run:
```bash
grep -nE "^(from|import)|ohlcv_matrix\.|trend_template\.|minervini_filter\." \
  scripts/screen_trend_template.py | head -30
```
Expected: 부르는 함수 목록. 이 중 시세를 얻는 자리만 `us_matrix.get_series` 로 바꾼다.

- [ ] **Step 2: 미국판 스크립트를 쓴다**

한국 `screen_trend_template.py`(766줄)를 본떠 만든다. Step 1 에서 센 목록을 놓고
**바꾸는 자리만** 바꾼다. 나머지는 그대로 옮긴다.

| 무엇 | 한국 | 미국 |
|---|---|---|
| 시세 | `ohlcv_matrix.get_series(code, days_back)` | `us_matrix.get_series(code)` |
|  |  | 🔴 **`days_back` 인자가 «없다»**(2026-09-11 정정). 한국은 「오늘 기준 달력일 bisect」인데
|  |  | 우리 뼈대는 «고정 날짜»에 얼어 있어 뜻이 달라진다. 자를 일이 있으면 부르는 쪽이 자른다 |
| 유니버스 | 공유 후보 파일 | `us_loader.load_tickers("base")` |
| 출력 | `trend-template-candidates.json` | `sepa-us-trend-candidates.json` |
| 국면 필터 | `fetch_market_status` | **뺀다** |
| 거래정지 «보고서» | `_save_halted_report` | **뺀다**(한국 정지 «자료원»이 없다) |
| 거래정지 «관문» | `liveness.is_halted` | 🔴 **넣는다**(2026-09-11 정정) |
|  |  | ★ 「거래정지」에 «자가 둘»이었다(유형 67). 한국 정지 «플래그»는 없지만
|  |  | `is_halted` 는 **거래량으로 «계산»**한다 — 뼈대에 `volumes` 가 있으므로 «된다**.
|  |  | ⛔ **27.4년 하네스가 관문 «앞»에서 이것을 부른다**
|  |  | (`backtest_volatility_pilot_us.py:357` — 유동성보다도 «먼저»).
|  |  | 빼면 **백테스트가 «걸러낸» 종목이 후보로 올라온다** = 관문 집합을 바꾼 것 |
| 외국인 | `ohlcv_matrix.get_foreign` | **뺀다**(대응물 없다) |

관문 판정 자체(`trend_template.evaluate`)와 RS 계산(`_compute_rs_for_all`)은
**한 줄도 바꾸지 않는다.** 그 수가 27.4년이 돌던 값이다.

### 🔴 RS 를 «언제» 재는가 — 한국판과 «일부러» 다르다 (사용자 결정 2026-09-11)

⛔ **`_compute_rs_for_all` 을 정지·유동성을 «다 거른 뒤»에 부른다.** 함수 자체도
`MIN_RS_COMPARISON_POOL` 도 «안» 바꾼다 — 바꾸는 것은 **「언제 부르는가」 하나**다.

| | RS 비교풀 | 풀 | 통과 |
|---|---|---|---|
| 한국 규약 | 거르기 «전» 전 시장 | 3,882 | 321 |
| ✅ **하네스 규약(채택)** | «거른 뒤» 생존자 | **3,431** | **302** |

까닭 셋:
① **27.4년의 수가 그 규약에서 나왔다** — 하네스가 `stD`(다 거른 뒤)로 부른다
   (`backtest_volatility_pilot_us.py:352-371`). 전 시장으로 재면
   **백테스트가 «본 적 없는» 19종목**이 후보로 올라온다(실측·㉯⊆㉮ 확인).
② 한국 규약은 「더 낫다」는 **설계 주장**이지 «검정»된 것이 아니다.
③ ★ **한국 근거의 «크기»가 미국에 없다** — 그 주석이 든 수는 「저유동이 시장의 ~57%」인데
   미국 실측은 **457/3,918 = 11.7%**(다섯 배). 게다가 한국 결과를 미국 판단의
   근거로도 «예상»으로도 쓰지 않는다(사용자 결정 2026-09-09).

🔴 **머리말 주석에 이 판정을 박는다.** 안 적으면 다음 사람이 「한국판과 다르네」 하고 «되돌린다».
🔴 **출력·JSON 에 「RS 비교풀 크기」를 찍는다.** 이게 «안 보여서» 19종목이 숨어 있었다.

★★ **교훈(유형 등재 후보): 관문 «목록»이 같아도 「모집단 통계」를 «어디서» 재느냐로
   결과가 갈린다. 검산기는 «수»가 같은지만 보지 «순서»는 안 본다.**

```python
# scripts/screen_trend_template_us.py 머리말
"""미국 SEPA 1단계 — 8관문 + RS 80.

★ 뺀 것과 까닭 (설계 문서 §"미국 결과로 재구성"의 실체):
  - 국면 자동 필터: 60·112 — 미국 등가중 20MA 로 MDD −36.2 → −55.4% 악화
  - DART 실적: 자료원 교체(Sharadar)
  - 외국인 지분율: 미국에 대응물 없음
★ 검출기·관문의 수는 하나도 바꾸지 않는다. verify_frozen_params.py 로 검산한다.
"""
```

- [ ] **Step 3: 값 동결 검산을 먼저 돌린다**

Run: `python scripts/verify_frozen_params.py`
Expected: `다른 값 0개`

- [ ] **Step 4: 돌려서 통과 수를 낸다**

Run: `python scripts/screen_trend_template_us.py`
Expected: 통과 종목 수와 유니버스 분모가 찍힌다.
분모가 무엇인지(유니버스 전체인지 310봉을 채운 것인지) 출력에 적는다.

- [ ] **Step 5: 스킬 파일을 쓴다**

```markdown
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
```

- [ ] **Step 6: 커밋** (사용자 요청이 있을 때만)

```bash
git add scripts/screen_trend_template_us.py .claude/skills/find-trend-template-us/SKILL.md
git commit -m "feat(us): find-trend-template-us — 8관문 + RS 80"
```

---

### Task 8: 검출기 스킬 넷

**Files:**
- Create: `.claude/skills/find-vcp-us/SKILL.md`
- Create: `.claude/skills/find-power-play-us/SKILL.md`
- Create: `.claude/skills/find-3c-us/SKILL.md`
- ~~Create: `.claude/skills/find-ipo-us/SKILL.md`~~ 🔴 **취소됨 2026-09-11**(사용자 결정 — 27.4년이 IPO 트랙을 안 돌렸다. CLAUDE.md §7)
- Create: `scripts/screen_detectors_us.py`

**Interfaces:**
- Consumes: `us_matrix.get_series` · `vcp.evaluate_vcp` · `power_play.evaluate_power_play` ·
  `cheat.evaluate_cheat` · ~~`ipo_track`~~ · `sepa-us-trend-candidates.json` 🔴 **취소됨 2026-09-11**(사용자 결정 — 27.4년이 IPO 트랙을 안 돌렸다. CLAUDE.md §7)
- Produces: `public/data/sepa-us-{vcp,power-play,3c}-candidates.json`   🔴 ipo 취소 2026-09-11

넷이 한 스크립트를 공유하고 `--kind` 로 갈린다. 검출기 코드는 한국과 **같은 모듈**을 쓴다.

- [ ] **Step 1: 검출기 함수 이름을 확인한다**

Run:
```bash
grep -nE "^def evaluate" scripts/canslim_lib/vcp.py scripts/canslim_lib/power_play.py \
  scripts/canslim_lib/cheat.py scripts/canslim_lib/ipo_track.py
```
Expected: 넷의 정확한 함수 이름과 인자. 계획의 이름과 다르면 **코드를 따른다**.

- [ ] **Step 2: 공용 스크립트를 쓴다**

```python
# scripts/screen_detectors_us.py
"""미국 SEPA 2단계 — 검출기 넷. --kind 로 갈린다.

★ 검출기 코드와 값은 한국과 같은 모듈을 그대로 쓴다.
  27.4년 백테스트가 그 값으로 돌았다(커밋 e8cd65ae).
★ Step 1 에서 확인한 진짜 함수 이름을 EVALS 에 적는다. 계획의 이름과 다르면 코드를 따른다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import cheat, power_play, us_matrix, vcp  # noqa: E402
# 🔴 ipo_track 은 «안» 가져온다 — find-ipo-us 취소(2026-09-11). CLAUDE.md §7

IN_PATH = ROOT / "public" / "data" / "sepa-us-trend-candidates.json"
OUT = {k: ROOT / "public" / "data" / f"sepa-us-{k}-candidates.json"
       for k in ("vcp", "power-play", "3c")}   # 🔴 ipo 취소 2026-09-11 — CLAUDE.md §7

# Step 1 에서 확인한 이름으로 채운다
EVALS = {
    "vcp": vcp.evaluate_vcp,
    "power-play": power_play.evaluate_power_play,
    "3c": cheat.evaluate_cheat,
}


def run(kind: str) -> int:
    fn = EVALS[kind]
    cands = json.loads(IN_PATH.read_text(encoding="utf-8"))
    out = []
    for c in cands.get("candidates", []):
        s = us_matrix.get_series(c["code"])
        if not s:
            continue
        r = fn(s)
        if r and r.get("status") in ("breakout", "actionable", "forming"):
            out.append({**c, **r})
    OUT[kind].write_text(json.dumps({"candidates": out}, ensure_ascii=False,
                                    indent=1), encoding="utf-8")
    print(f"{kind}: 입력 {len(cands.get('candidates', []))} → 검출 {len(out)}")
    return len(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=sorted(EVALS))
    run(ap.parse_args().kind)
```

⚠️ 위 `EVALS` 와 `status` 값은 **Step 1 에서 확인한 것으로 바꾼다.** 코드가 정본이다.

- [ ] **Step 3: 값 동결 검산 → 넷 다 돌린다**

Run:
```bash
python scripts/verify_frozen_params.py && \
for k in vcp power-play 3c; do python scripts/screen_detectors_us.py --kind $k; done
```
Expected: 넷 다 후보 파일이 생기고 각각 검출 수가 찍힌다.

- [ ] **Step 4: 스킬 파일 넷을 쓴다**

한국 `find-vcp` 등의 frontmatter 를 본떠 `-us` 판을 만든다.
각 파일은 `python scripts/screen_detectors_us.py --kind <종류>` 하나를 부른다.

- [ ] **Step 5: 커밋** (사용자 요청이 있을 때만)

```bash
git add scripts/screen_detectors_us.py .claude/skills/find-*-us/SKILL.md
git commit -m "feat(us): 검출기 스킬 넷 — 값은 한국 모듈 그대로"
```

---

### Task 9: `sepa-us` 부모 스킬

**Files:**
- Create: `.claude/skills/sepa-us/SKILL.md`

**Interfaces:**
- Consumes: 위 스킬 여섯을 Skill 도구로 부른다. 직접 계산하지 않는다.

- [ ] **Step 1: 스킬 파일을 쓴다**

```markdown
---
name: sepa-us
description: 미국 SEPA 파이프라인 오케스트레이터. update-data-us → find-trend-template-us → 검출기 넷을 순서대로 돌리고 통합 요약한다. 직접 계산하지 않고 하위 스킬을 부른다. 사용자가 "/sepa-us", "미국 세파 돌려줘", "오늘 미국 후보" 등을 요청할 때 사용.
---

# sepa-us

## 순서
1. `update-data-us` — **분할이 있으면 여기서 멈춘다**
2. `find-trend-template-us` (관문)
3. `find-vcp-us` · `find-power-play-us` · `find-3c-us` (병렬 가능)
   🔴 **`find-ipo-us` 는 «없다»**(사용자 결정 2026-09-11). 부르지 마라.
   까닭: 27.4년 백테스트가 `ipo_track` 을 한 번도 «안 돌렸다** — 하네스는
   vcp·cheat·power_play 셋만 쓴다. 자료가 «없어서»가 «아니다»(대상 349종목이 있다).
   나중에 할 일로 남겼다 — CLAUDE.md §7.
4. 통합 요약

## 이 방법이 무엇을 하고 무엇을 안 하는가

확정된 매매 방식은 `CLAUDE.md` §2 에 있다. 요약:
피벗 예약매수 · 손절 −10% 시장가 · +30% 에 절반 · 25일 저가 추격 ·
매도 규칙 다섯은 점검 표시만(자동 매도 안 함).

**뺀 것과 까닭** (안 적으면 다음 세션이 다시 짓는다):

| 뺀 것 | 까닭 |
|---|---|
| 국면 자동 필터 | 60·112 — 미국 등가중 20MA 로 MDD −36.2 → −55.4% 악화 |
| 실적임박 표시 | 257b — 예고일 자료가 세상에 없다. 대용 달력 오차 P90 49일 |
| 매도 규칙 자동 집행 | 253 −17.955%p/해. 사용자가 껐다(79e463fb) |
| 장중 거래량·분봉·자동매수봇 | 사용자가 장중 거래량을 안 본다. 봇 미사용 |
| DART 실적 · 원화 유동성 단위 | 자료원 교체 |

**미해결**: 10월부터 Sharadar 종목 정보가 안 갱신된다. 신규 상장이 유니버스에 안 들어오고
IPO 트랙이 죽는다. 나스닥 공개 목록으로 일부는 메우지만 SPAC 은 못 거른다.

## 자동 커밋 안 함
커밋은 사용자가 요청할 때만.
```

- [ ] **Step 2: 스킬 목록에 뜨는지 본다**

Run: `ls .claude/skills/ | grep -- -us`
Expected: **여섯** 개(`update-data-us` · `find-trend-template-us` · 검출기 **셋** · `sepa-us`)
  🔴 2026-09-11 정정 — `find-ipo-us` 취소로 「일곱」이 「여섯」이 됐다. CLAUDE.md §7

- [ ] **Step 3: 커밋** (사용자 요청이 있을 때만)

```bash
git add .claude/skills/sepa-us/SKILL.md
git commit -m "feat(us): sepa-us 부모 스킬"
```

---

## 다 지은 뒤 확인

- [ ] `python -m pytest tests/test_us_matrix.py -v` — 전부 통과
- [ ] `python scripts/verify_frozen_params.py` — `다른 값 0개`
- [ ] `ls .claude/skills/ | grep -- -us | wc -l` — 7
- [ ] `sepa-us` 를 한 번 돌려 후보 파일 **넷**이 생기는지 본다
      🔴 2026-09-11 정정 — `find-ipo-us` 취소로 「다섯」이 「넷」이 됐다
- [ ] 한국 후보 파일(`public/data/sepa-*-candidates.json` 중 `-us` 없는 것)이
      **안 바뀌었는지** `git status` 로 확인한다
