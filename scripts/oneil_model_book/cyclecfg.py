"""사이클 컨텍스트 — 모든 파이프라인 스크립트가 공유.

활성 사이클은 환경변수 OMB_CYCLE(cycle_id, 기본 c2024-12).
cycles_index.json 에서 앵커·종료를 읽어 사이클별 출력 디렉터리와
날짜구간 Yahoo 시세를 제공한다. (과거 사이클 재현의 단일 진입점.)
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib.fetch import fetch_yahoo_chart  # noqa: E402

KST = timezone(timedelta(hours=9))
RESEARCH = ROOT / "research" / "oneil-model-book"
CYCLES_INDEX = RESEARCH / "cycles" / "cycles_index.json"

CYCLE_ID = os.environ.get("OMB_CYCLE", "c2024-12")   # 가격창·앵커 결정(cycles_index)
_OUTDIR = os.environ.get("OMB_OUTDIR")               # 출력 폴더만 분리(선택)
                                                     # — 대조군을 원사이클 창으로
                                                     #   수집하되 별 폴더에 쓸 때


def _load_cycle() -> dict:
    if CYCLES_INDEX.exists():
        idx = json.loads(CYCLES_INDEX.read_text(encoding="utf-8"))
        for c in idx.get("cycles", []):
            if c["cycle_id"] == CYCLE_ID:
                return c
    # 폴백: 기존 2024-12 계엄 사이클(레거시 호환)
    return {"cycle_id": "c2024-12", "anchor": "2024-12-09",
            "cycle_end": datetime.now(KST).strftime("%Y-%m-%d"), "ongoing": True,
            "label": "2024-12 계엄 사이클(레거시 기본)"}


_C = _load_cycle()
ANCHOR = _C["anchor"]                                   # 'YYYY-MM-DD' (각 종목 저점 기준일)
ONGOING = bool(_C.get("ongoing"))
CYCLE_END = (datetime.now(KST).strftime("%Y-%m-%d") if ONGOING
             else _C.get("cycle_end") or datetime.now(KST).strftime("%Y-%m-%d"))
LABEL = _C.get("label", CYCLE_ID)
DIR = RESEARCH / "cycles" / (_OUTDIR or CYCLE_ID)       # 산출 디렉터리
                                                        # (OMB_OUTDIR 우선)
DIR.mkdir(parents=True, exist_ok=True)


def _ep(date_str: str, addsec: int = 0) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp()) + addsec


def anchor_ts() -> int:
    """앵커일 자정(KST) unix ts — discover의 사이클 시작 필터용."""
    return int(datetime.strptime(ANCHOR, "%Y-%m-%d").replace(tzinfo=KST).timestamp())


# 시세 조회 창: 앵커 2년 전(52주 RS·base 룩백 여유) ~ 사이클 종료(+5일)
_P1 = _ep(ANCHOR) - 730 * 86400
_P2 = _ep(CYCLE_END) + 5 * 86400


def yahoo(symbol: str, interval: str = "1d"):
    """사이클 구간 [앵커-2y, 종료+5d] 일봉. (과거 사이클이면 자동 과거 조회.)"""
    return fetch_yahoo_chart(symbol, period1=_P1, period2=_P2, interval=interval)


def banner() -> str:
    return (f"[사이클 {CYCLE_ID}] {LABEL} | 앵커 {ANCHOR} → 종료 {CYCLE_END}"
            f"{' (진행중)' if ONGOING else ''} | 출력 {DIR}")


if __name__ == "__main__":
    print(banner())
