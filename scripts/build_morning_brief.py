"""장전 브리핑 — 밤사이 미국 마감을 «우리 섹터 언어»로 옮긴다.

왜 필요한가:
  아침 09:00 에 무엇을 볼지 정하려면 두 가지가 필요하다.
  ① 밤사이 미국에서 «어느 테마»가 움직였나  ② 그게 «우리 감시 목록»의 어느 종목인가.
  시중 서비스는 ①까지만 말해 준다. ②는 우리 자료(어제 SEPA 가 뽑은 후보와 피벗)에만 있다.

🚨 코스피는 밤사이 미국 지수를 통째로 따라간다. 그래서 섹터 바스켓 수익률을 «그대로»
  쓰면 아홉 섹터가 전부 같은 말을 한다("장이 올랐다"). 반드시 «초과수익»을 본다 —
  바스켓 수익률에서 S&P500 수익률을 뺀 값. 그래야 섹터 «고유»의 움직임이 남는다.

⚠️ 이 도구는 「읽고 사람이 판단」하는 용도다(사용자 결정 26-09-21).
  자동매수 결정에 쓰지 않는다. 미국 초과수익이 다음날 한국 섹터를 «예측하는지»는
  아직 «안 쟀다». 안 쟀다는 것과 효과가 없다는 것은 다르다.

무엇을 내나:
  섹터 9개 × {미국 바스켓 등락, S&P500 대비 초과, 우리 감시 종목}
  바스켓이 빈 섹터(조선·백화점)는 「프록시 없음」으로 나온다. 억지로 채우지 않는다.

자료:
  · 미국 시세     FinanceDataReader (야후) — 직전 미국 거래일 종가 대비 그 전날 종가
  · 섹터 대응     public/data/us-sector-proxy.json  (사전 등록. 결과 보고 고치지 않는다)
  · 한국 섹터 배정 public/data/leading-sectors-config.json  (사용자 큐레이션, rank 1~9)
  · 감시 목록     pivot_alert.load_watch_universe()

산출: public/data/morning-brief-YYYYMMDD.json  (--save 일 때만)
실행: python -X utf8 scripts/build_morning_brief.py [--save] [--quiet]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

DATA = ROOT / "public" / "data"
# 섹터 축의 정본. «업종»이라 모든 종목에 붙는다(26-09-21: 2,871/2,871).
# scripts/build_sector_map.py 가 만든다.
SECTOR_MAP_FILE = DATA / "sector-map.json"
# 테마 축. 사용자가 손으로 고른 주도 섹터 9개라 «일부» 종목에만 붙는다. 겹쳐 보는 용도.
THEMES_FILE = DATA / "leading-sectors-config.json"

# 야후 일봉을 넉넉히 받아 «마지막 두 개»를 쓴다. 휴장은 행이 없어 스스로 걸러진다.
LOOKBACK_DAYS = 12


# ── 순수 로직 (시험 대상) ────────────────────────────────────

def pct(prev: float | None, cur: float | None) -> float | None:
    """전일 종가 대비 등락률(퍼센트). 둘 중 하나라도 없거나 0이면 None."""
    if prev is None or cur is None or prev == 0:
        return None
    return (cur / prev - 1.0) * 100.0


def basket_return(tickers: list[str], rets: dict[str, float | None]) -> dict:
    """동일가중 바스켓 등락률.

    시총가중을 «안» 쓰는 까닭: NVDA 한 종목이 반도체 바스켓을 통째로 먹는다.
    우리가 알고 싶은 건 「그 테마가 움직였나」지 「대장주가 움직였나」가 아니다.

    못 받은 티커는 세지 «않는다». 대신 몇 개를 못 받았는지 같이 돌려준다 —
    3개 중 2개를 못 받은 바스켓과 5개 다 받은 바스켓을 같은 수로 읽으면 안 된다.
    """
    used = [t for t in tickers if rets.get(t) is not None]
    missing = [t for t in tickers if rets.get(t) is None]
    if not used:
        return {"ret": None, "used": [], "missing": missing, "n": 0}
    avg = sum(rets[t] for t in used) / len(used)
    return {"ret": avg, "used": used, "missing": missing, "n": len(used)}


def excess(basket_ret: float | None, bench_ret: float | None) -> float | None:
    """바스켓에서 기준지수를 뺀 초과수익. 이것이 섹터 고유 신호다."""
    if basket_ret is None or bench_ret is None:
        return None
    return basket_ret - bench_ret


def rank_to_key(sectors: list[dict]) -> dict[int, str]:
    """leading-sectors-config 의 rank(1~9) → 테마 키. 테마 겹쳐보기에만 쓴다."""
    return {int(s["rank"]): s["key"] for s in sectors if s.get("rank") is not None}


def watch_by_bucket(assignments: dict, watch: list[dict]) -> dict[str, list[dict]]:
    """감시 종목을 «업종» 묶음별로 나눈다.

    sector-map 은 전 종목을 덮으므로 «_미분류로 새는 종목이 없어야 정상»이다.
    그래도 버리지 않고 '_미분류' 로 남긴다 — 새면 그게 관측이고 브리핑에 수가 찍힌다.
    """
    out: dict[str, list[dict]] = {}
    for r in watch:
        a = assignments.get(r["code"])
        out.setdefault((a or {}).get("bucket") or "_미분류", []).append(r)
    return out


def sector_rows(buckets: dict, rets: dict[str, float | None],
                bench_ret: float | None, by_bucket: dict) -> list[dict]:
    """업종 묶음을 초과수익 내림차순으로. 미국 대응이 없는 묶음은 맨 뒤에 따로.

    «감시 종목이 없는 묶음도 남긴다» — 오늘 우리 후보에 없다고 그 섹터가 안 움직인
    것은 아니다. 내일 후보에 들어올 수 있다.
    """
    rows = []
    for key, cfg in buckets.items():
        tickers = cfg.get("proxy") or []
        b = basket_return(tickers, rets)
        stocks = by_bucket.get(key) or []
        rows.append({
            "key": key,
            "label": cfg.get("label") or key,
            "tickers": tickers,
            "basket_ret": b["ret"],
            "excess": excess(b["ret"], bench_ret),
            "n_used": b["n"],
            "missing": b["missing"],
            "has_proxy": bool(tickers),
            "watch": [{"code": s["code"], "name": s["name"], "status": s.get("status"),
                       "pivot_price": s.get("pivot_price"), "pattern": s.get("pattern")}
                      for s in stocks],
        })
    rows.sort(key=lambda r: (not r["has_proxy"],
                             -(r["excess"] if r["excess"] is not None else -9e9)))
    return rows


def theme_overlay(assignments: dict, r2k: dict[int, str],
                  watch: list[dict]) -> dict[str, list[str]]:
    """감시 종목에 붙은 «테마»(주도 섹터 9개). 업종 축과 «겹쳐» 본다.

    업종은 「이 회사가 무엇을 만드나」, 테마는 「지금 시장이 무엇으로 묶어 보나」다.
    한미반도체는 업종으로 반도체고 테마로 HBM후공정이다. 둘 다 맞다.
    """
    out: dict[str, list[str]] = {}
    for r in watch:
        a = assignments.get(r["code"])
        if not a or a.get("rank") is None:
            continue
        k = r2k.get(int(a["rank"]))
        if k:
            out.setdefault(k, []).append(r["name"])
    return out


# ── 자료 받기 ────────────────────────────────────────────────

def fetch_returns(tickers: list[str], end: datetime) -> dict[str, float | None]:
    """직전 미국 거래일의 종가 대비 등락률. 못 받으면 None 으로 남긴다."""
    import FinanceDataReader as fdr
    start = (end - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    stop = end.strftime("%Y-%m-%d")
    out: dict[str, float | None] = {}
    for t in tickers:
        try:
            d = fdr.DataReader(t, start, stop)
            out[t] = pct(float(d["Close"].iloc[-2]), float(d["Close"].iloc[-1])) if len(d) >= 2 else None
        except Exception:
            out[t] = None
    return out


def us_session_date(tickers: list[str], end: datetime) -> str | None:
    """바스켓이 실제로 본 «미국 거래일». 날짜를 짐작하지 않고 자료에서 읽는다."""
    import FinanceDataReader as fdr
    for t in tickers:
        try:
            d = fdr.DataReader(t, (end - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d"),
                               end.strftime("%Y-%m-%d"))
            if len(d):
                return str(d.index[-1].date())
        except Exception:
            continue
    return None


def build(now: datetime) -> dict:
    """브리핑 한 장을 만든다."""
    import pivot_alert as pa

    smap = json.loads(SECTOR_MAP_FILE.read_text(encoding="utf-8"))
    themes = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
    buckets = smap["buckets"]
    bench = "^GSPC"

    all_t = sorted({t for c in buckets.values() for t in (c.get("proxy") or [])})
    rets = fetch_returns(all_t + [bench, "^IXIC", "EWY"], now)
    bench_ret = rets.get(bench)

    watch = pa.load_watch_universe()
    by_b = watch_by_bucket(smap.get("assignments") or {}, watch)

    return {
        "generated_at": f"{now:%Y-%m-%d %H:%M}",
        "us_session": us_session_date([bench], now),
        "benchmark": {"ticker": bench, "ret": bench_ret,
                      "nasdaq": rets.get("^IXIC"), "ewy": rets.get("EWY")},
        "sectors": sector_rows(buckets, rets, bench_ret, by_b),
        "themes": theme_overlay(themes.get("assignments") or {},
                                rank_to_key(themes["sectors"]), watch),
        "theme_labels": {s["key"]: s.get("short") or s["label"] for s in themes["sectors"]},
        "watch_total": len(watch),
        "unmapped": [{"code": s["code"], "name": s["name"]}
                     for s in (by_b.get("_미분류") or [])],
        "sector_map_coverage": smap.get("coverage", {}),
        "caveat": ("미국 초과수익이 다음날 한국 섹터를 예측하는지는 아직 안 쟀다. "
                   "읽고 사람이 판단하는 용도이고 자동매수 결정에 쓰지 않는다."),
    }


# ── 보여주기 ─────────────────────────────────────────────────

def _n(v: float | None, w: int = 6) -> str:
    return f"{v:+{w}.2f}" if v is not None else " " * (w - 1) + "—"


def render(b: dict) -> str:
    """사람이 읽는 한 장. 콘솔과 파일 양쪽에 같은 내용이 간다."""
    L = []
    bm = b["benchmark"]
    L.append(f"장전 브리핑 · {b['generated_at']} · 미국 {b['us_session']} 마감 기준")
    L.append(f"S&P500 {_n(bm['ret'])}%  나스닥 {_n(bm['nasdaq'])}%  EWY(한국ETF) {_n(bm['ewy'])}%")
    L.append("")
    L.append("업종              미국바스켓   S&P대비   감시종목")
    for s in b["sectors"]:
        if not s["has_proxy"]:
            L.append(f"{s['label'][:16]:16s} {'대응 없음':>10s} {'':>9s} {len(s['watch']):6d}개")
            continue
        miss = f"  (못받음 {len(s['missing'])})" if s["missing"] else ""
        L.append(f"{s['label'][:16]:16s} {_n(s['basket_ret'])}%  {_n(s['excess'])}%p "
                 f"{len(s['watch']):6d}개{miss}")
    L.append("")
    L.append("S&P500 을 앞선 업종의 감시 종목 (괄호는 피벗):")
    shown = 0
    for s in b["sectors"]:
        if not s["has_proxy"] or s["excess"] is None or not s["watch"] or shown >= 4:
            continue
        if s["excess"] <= 0:
            break
        names = "  ".join(f"{w['name']}({w['pivot_price']:,.0f})" if w.get("pivot_price")
                          else w["name"] for w in s["watch"][:8])
        L.append(f"  [{s['label']} {_n(s['excess'])}%p] {names}")
        shown += 1
    if not shown:
        L.append("  (초과수익이 양수인 업종에 감시 종목이 없다)")

    if b.get("themes"):
        L.append("")
        L.append("테마 겹쳐보기 (사용자 주도 섹터 9개 — 업종과 다른 축이다):")
        lab = b.get("theme_labels") or {}
        for k, names in sorted(b["themes"].items(), key=lambda x: -len(x[1])):
            L.append(f"  [{lab.get(k, k)}] {'  '.join(names[:8])}")

    L.append("")
    cov = b.get("sector_map_coverage") or {}
    L.append(f"감시 {b['watch_total']}종목 중 업종 안 붙은 것 {len(b['unmapped'])}종목 "
             f"(전 종목 분류율 {cov.get('rate', 0):.1f}퍼센트)")
    L.append(f"주의: {b['caveat']}")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="장전 브리핑 — 밤사이 미국 마감을 우리 섹터로 옮긴다")
    ap.add_argument("--save", action="store_true", help="public/data 에 날짜별 파일로 저장")
    ap.add_argument("--quiet", action="store_true", help="콘솔 출력 생략")
    a = ap.parse_args()

    import pivot_alert as pa
    now = datetime.now(pa.KST)
    b = build(now)

    if not a.quiet:
        print(render(b))

    if a.save:
        out = DATA / f"morning-brief-{now:%Y%m%d}.json"
        tmp = out.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
        json.loads(tmp.read_text(encoding="utf-8"))   # 읽히는지 확인하고 옮긴다
        tmp.replace(out)
        print(f"\n저장 {out}")


if __name__ == "__main__":
    main()
