"""미국(Sharadar) 시세 뼈대 — 한국 ohlcv_matrix 의 읽기 계약을 맞춘다.

★ 왜 있나: Sharadar 결제가 2026-09 로 끝난다. 뼈대를 한 번 만들어 얼리고
  야후 꼬리를 날마다 붙인다. 원본(45,317,834행·3~4GB)은 다시 열지 않는다.

★ 310 은 고른 수가 아니다 — trend_template.py:43 `needed = window + end_offset`.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_PATH = ROOT / ".cache" / "us" / "base.json"
# 꼬리를 붙인 «합본». `/update-data-us` 가 여기에 쓴다.
# ★ 경로가 «여기» 있는 까닭: us_seam 이 us_matrix 를 import 하므로 반대로
#   부르면 순환이 된다. 그래서 경로를 이쪽에 두고 us_seam 이 가져다 쓴다.
#   ⛔ 자가 둘이 되면 안 된다 — «여기가 정본»이다.
TAIL_PATH = ROOT / ".cache" / "us" / "tail.json"
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


_BASE: dict | None = None
# 주의: 이 전역 변수는 시험끼리 «샐» 수 있다. 각 시험이 로드하기 전에
# load_base(path) 를 호출하면 격리된다.


def load_base(path: Path | None = None) -> dict:
    """뼈대 파일을 한 번 읽어 전역 캐시 _BASE 에 둔다.

    🔴 소비자는 이것이 아니라 `load_latest()` 를 불러라. base 는 «얼린» 뼈대다 —
       꼬리가 붙은 합본(TAIL_PATH)이 있어도 이 함수는 그것을 «안» 본다.

    같은 경로를 여러 번 로드하면 캐시 재사용.
    path 가 None 이면 BASE_PATH 를 사용한다.
    """
    global _BASE
    p = path or BASE_PATH
    _BASE = json.loads(p.read_text(encoding="utf-8"))
    return _BASE


def load_latest() -> tuple[dict, Path]:
    """소비자가 «실제로» 읽어야 하는 것 — 합본이 있으면 그것, 없으면 뼈대.

    ★ 왜 있나: `/update-data-us` 는 꼬리를 붙인 «합본»을 TAIL_PATH 에 쓰는데
      소비자가 BASE_PATH 를 읽으면 **갱신이 아무 효과가 없다** — 예외도 경고도
      없이 옛 자료로 돈다. 2026-09-11 검토에서 발견했을 때 저장소 전체에서
      tail.json 을 «읽는» 자리가 «0개»였다.
      ⇒ 고르는 자리를 «한 곳»에 둔다. 소비자마다 `if tail.exists()` 를 적으면
        다음 소비자가 또 빠뜨린다.

    반환: (자료, 실제로 읽은 파일 경로) — 부르는 쪽이 «어느 것을 읽었는지»
          찍을 수 있어야 이 병이 또 조용해지지 않는다.
    """
    p = TAIL_PATH if TAIL_PATH.exists() else BASE_PATH
    return load_base(p), p


def get_series(code: str) -> dict | None:
    """한국 ohlcv_matrix.get_series 와 같은 계약.

    code 를 찾지 못하면 None 반환.
    _BASE 가 로드되지 않았으면 자동으로 로드한다 — 이때 `load_latest()` 를 쓴다.
    🔴 2026-09-11: 여기가 `load_base()` 였다. 그러면 합본(TAIL_PATH)이 있어도
       «안» 본다. 1단계 각본은 load_latest() 를 «먼저» 불러 우연히 맞고
       있었을 뿐이다 — 「먼저 부른다」는 «순서»이지 «계약»이 아니다.
       부르는 쪽이 load_latest() 를 잊으면 예외도 경고도 없이 옛 자료로 돈다.
    파일이 하나도 없으면 None 반환 (다른 예외는 전파).
    """
    if _BASE is None:
        try:
            load_latest()
        except FileNotFoundError:
            return None
    s = (_BASE or {}).get("series", {}).get(code)
    if not s:
        return None
    return s


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
    # meta 안의 turnover_usd 는 종목마다 (날짜, 달러) 배열을 통째로 들고 있어
    # 무겁다 — 여기서는 시세 뼈대만 다루므로 펼치지 않고 뺀다.
    # meta 의 n_rows 는 다듬기 «전» 원시 창 전체의 행 수(us_loader.py:225)라
    # 아래에서 직접 계산하는(다듬은 뒤의) n_rows 와 이름은 같고 뜻이 다르다.
    # **meta_light 를 펼칠 때 뒤에 나온 값이 앞을 덮으므로, 여기서 미리 빼
    # 두지 않으면 반환값의 n_rows 가 계산값이 아니라 meta 의 원시값으로
    # 조용히 바뀐다(검토에서 잡힘 — 겹치는 키는 n_rows 하나뿐, 위에서 확인).
    meta_light = {k: v for k, v in meta.items()
                  if k not in ("turnover_usd", "n_rows")}
    return {"asof": asof, "n_codes": len(series),
            "n_rows": sum(len(s["dates"]) for s in series.values()),
            "n_full": sum(1 for s in series.values()
                          if len(s["dates"]) >= TRIM_BARS),
            "path": str(path), **meta_light}
