# scripts/screen_holdings_feedback.py
"""SEPA 보유 종목 점검 — 미너비니 매도 규칙 위반 피드백.

입력: public/data/sepa-holdings.json (매수 목록, 사용자 관리)
      sepa-vcp-candidates.json / sepa-power-play-candidates.json (피벗, vcp 우선)
출력: public/data/sepa-holdings-feedback.json
정의: docs/superpowers/specs/2026-07-03-sepa-holdings-feedback-design.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import ohlcv_matrix  # noqa: E402
from canslim_lib.sell_rules import evaluate_holding, find_breakout_index  # noqa: E402

KST = timezone(timedelta(hours=9))
IN_PATH = ROOT / "public" / "data" / "sepa-holdings.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-holdings-feedback.json"
SIGNAL_LABEL = {"stop_loss": "🔴 손절", "early_sell": "🟠 조기매도",
                "hold": "🟢 정상보유", "no_data": "⚫ 데이터없음"}


def load_pivots() -> dict:
    """code → [{pivot, source, market}, ...] 후보 목록 (vcp 우선 순서)."""
    out = {}
    for fname, source in (("sepa-vcp-candidates.json", "vcp"),
                          ("sepa-power-play-candidates.json", "power_play")):
        p = ROOT / "public" / "data" / fname
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for c in data.get("candidates", []):
            if c.get("pivot_price") is not None:
                out.setdefault(c["code"], []).append(
                    {"pivot": c["pivot_price"], "source": source,
                     "market": c.get("market")})
    return out


def _write_empty(out_path: Path, default_stop: int = -4) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": None, "stop_loss_pct_default": default_stop, "holdings": [],
    }
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"💾 저장(빈 결과): {out_path.relative_to(ROOT)}")


def run(out_path: Path) -> None:
    if not IN_PATH.exists():
        print(f"⏭️  매수 목록 없음({IN_PATH.relative_to(ROOT)}) — 빈 결과로 종료")
        _write_empty(out_path)
        return
    data = json.loads(IN_PATH.read_text(encoding="utf-8"))
    if not data.get("holdings"):
        print("⏭️  보유 종목 0개 — 빈 결과로 종료")
        _write_empty(out_path, data.get("stop_loss_pct_default", -4))
        return
    default_stop = data.get("stop_loss_pct_default", -4)
    pivots = load_pivots()

    out_holdings, asof = [], None
    for h in data.get("holdings", []):
        code = h["code"]
        buy_date = h["buy_datetime"][:10]
        stop_pct = h.get("stop_loss_pct", default_stop)
        options = pivots.get(code, [])
        s = ohlcv_matrix.get_series(code)
        chosen = None
        if h.get("pivot_price") is not None:
            # 매수 시점 피벗 스냅샷이 있으면 최우선 — 이후 스캔에서 후보 피벗이
            # 바뀌거나 사라져도 "내가 산 근거"로 일관되게 판정한다.
            chosen = {"pivot": h["pivot_price"], "source": "manual",
                      "market": options[0].get("market") if options else None}
        elif s and s.get("closes"):
            # 실제 돌파가 확인되는 피벗 우선(vcp→power_play), 없으면 첫 후보
            for opt in options:
                _, est = find_breakout_index(s, buy_date, opt["pivot"])
                if not est:
                    chosen = opt
                    break
        if chosen is None and options:
            chosen = options[0]
        base = {
            "code": code, "name": h.get("name"),
            "market": chosen.get("market") if chosen else None,
            "buy_date": buy_date, "buy_price": h["buy_price"],
            "quantity": h.get("quantity"), "stop_loss_pct": stop_pct,
            "pivot_price": chosen.get("pivot") if chosen else None,
            "pivot_source": chosen.get("source") if chosen else None,
        }
        if not s or not s.get("closes"):
            out_holdings.append({**base, "signal": "no_data", "violation_count": 0,
                                 "rules": []})
            continue
        r = evaluate_holding(s, buy_date, h["buy_price"], stop_pct,
                             pivot_price=base["pivot_price"])
        if asof is None or s["dates"][-1] > asof:
            asof = s["dates"][-1]
        out_holdings.append({**base, **r})

    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": asof,
        "stop_loss_pct_default": default_stop,
        "holdings": out_holdings,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"💾 저장: {out_path.relative_to(ROOT)} (기준일 {asof})\n")
    for x in out_holdings:
        label = SIGNAL_LABEL.get(x["signal"], x["signal"])
        extra = f" 위반 {x['violation_count']}건" if x["signal"] == "early_sell" else ""
        print(f"  [{label}{extra}] {x['code']} {x['name']} "
              f"매수 {x['buy_price']:,} → 현재 {x.get('current_price') or '?'} "
              f"({x.get('profit_pct', '?')}%)")
        for r in x.get("rules", []):
            mark = {"violation": "✗", "pass": "✓"}.get(r["status"], "―")
            print(f"      {mark} {r['id']}: {r['detail']}")


def main():
    ap = argparse.ArgumentParser(description="SEPA 보유 종목 매도 규칙 점검")
    ap.add_argument("--out", default=None, help=f"출력(default {OUT_PATH.name})")
    args = ap.parse_args()
    out_path = (Path(args.out) if args.out and Path(args.out).is_absolute()
                else ROOT / args.out if args.out else OUT_PATH)
    run(out_path)


if __name__ == "__main__":
    main()
