# scripts/screen_vcp_audit.py
"""vcp-audit — VCP 검출기 책 충실도 감사.

검출기가 찾은 종목(정밀도) + 사용자 정답 예시(재현율)를 책 5축으로 렌더링한다.
정의: docs/superpowers/specs/2026-06-30-vcp-book-audit-design.md
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

from canslim_lib.vcp import DEFAULT_PARAMS  # noqa: E402
from canslim_lib import vcp_audit  # noqa: E402

KST = timezone(timedelta(hours=9))
HISTORY = ROOT / "public" / "data" / "sepa-vcp-history.json"
EXAMPLES = ROOT / "public" / "data" / "vcp_examples.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-vcp-audit.json"
AXES = ("prior_advance", "contractions", "contraction_volumes", "dry_point", "breakout")


def _params(args) -> dict:
    return {"min_advance": args.min_advance, "mono_tol": args.mono_tol, "dry_max": args.dry_max,
            "breakout_vol": args.breakout_vol, "near": args.near, "vol_ma_window": args.vol_ma_window,
            "prior_lookback": 60, "right_frac": 0.34, "lookback_days": DEFAULT_PARAMS["lookback_days"],
            "zigzag_pct": args.zigzag_pct, "base_vol_cap": DEFAULT_PARAMS["base_vol_cap"]}


def _idx_on_or_before(dates, target):
    cand = [i for i, d in enumerate(dates) if d <= target]
    return cand[-1] if cand else None


def run(args) -> None:
    params = _params(args)
    items = []

    # 1) 정답 예시 (FDR)
    if not args.no_examples and EXAMPLES.exists():
        try:
            ex = json.loads(EXAMPLES.read_text(encoding="utf-8")).get("examples", [])
        except (OSError, json.JSONDecodeError) as e:
            print(f"⚠️ vcp_examples.json 읽기 실패: {e}")
            ex = []
        for e in ex:
            if str(e.get("code", "")).strip() in ("", "000000"):
                continue
            be = e.get("breakout_date") or e.get("end")
            try:
                fetch_end = (datetime.strptime(be, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d") if be else None
            except (ValueError, TypeError):
                fetch_end = be
            s = vcp_audit.load_series(e["code"], e.get("start"), fetch_end)
            if not s:
                items.append({"code": e["code"], "source": "example", "note": "데이터 로드 실패(FDR)"})
                continue
            b0 = _idx_on_or_before(s["dates"], e["start"])
            if b0 is None:
                items.append({"code": e["code"], "source": "example", "note": "기간 인덱스 실패(start)"})
                continue
            b1 = _idx_on_or_before(s["dates"], e.get("end"))   # 베이스 끝 = end (돌파일 아님)
            if b1 is None:
                items.append({"code": e["code"], "source": "example", "note": "기간 인덱스 실패(end)"})
                continue
            items.append(vcp_audit.audit_item(s, b0, b1, params,
                          {"code": e["code"], "name": e.get("note"), "source": "example"}))

    # 2) 검출기가 찾은 종목 (캐시)
    if not args.no_detector and HISTORY.exists():
        try:
            hist = json.loads(HISTORY.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"⚠️ sepa-vcp-history.json 읽기 실패: {e}")
            hist = {"stocks": []}
        for st in hist.get("stocks", []):
            if st.get("num_events", 0) <= 0:
                continue
            code = st["code"]
            s = vcp_audit.load_series(code)
            if not s:
                continue
            ev_date = st["events"][-1].get("confirm_date") or st["events"][-1]["date"]
            b1 = _idx_on_or_before(s["dates"], ev_date)
            if b1 is None:
                continue
            lb = params["lookback_days"]
            lo = max(0, b1 - lb + 1)
            b0 = lo + max(range(len(s["closes"][lo:b1 + 1])), key=lambda k: s["closes"][lo + k])
            items.append(vcp_audit.audit_item(s, b0, b1, params,
                          {"code": code, "name": st.get("name"), "source": "detector"}))

    pass_counts = {ax: sum(1 for it in items if it.get("axes", {}).get(ax, {}).get("pass")) for ax in AXES}
    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "params": params, "items": items,
        "summary": {"n_items": len(items), "axis_pass_counts": pass_counts},
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n💾 저장: {OUT_PATH.relative_to(ROOT)}")

    print(f"\n[VCP 책 충실도 감사] {len(items)}건  (축별 통과수: " +
          " · ".join(f"{ax} {pass_counts[ax]}" for ax in AXES) + ")")
    sym = {True: "O", False: "X", None: "-"}
    for it in items:
        ax = it.get("axes")
        if not ax:
            print(f"  {it['code']} ({it.get('source')}) — {it.get('note','평가불가')}")
            continue
        flags = " ".join(f"{a}:{sym.get(ax[a].get('pass'))}" for a in AXES)
        det = it["detector_verdict"]
        print(f"  {it['code']} {str(it.get('name'))[:10]:10s} ({it['source']:8s}) | {flags} "
              f"| 검출기 vcp={det['vcp_detected']}")


def main():
    ap = argparse.ArgumentParser(description="vcp-audit — VCP 책 충실도 감사")
    ap.add_argument("--no-examples", action="store_true")
    ap.add_argument("--no-detector", action="store_true")
    ap.add_argument("--min-advance", type=float, default=25.0)
    ap.add_argument("--dry-max", type=float, default=0.7)
    ap.add_argument("--breakout-vol", type=float, default=1.4)
    ap.add_argument("--near", type=float, default=5.0)
    ap.add_argument("--mono-tol", type=float, default=1.15)
    ap.add_argument("--vol-ma-window", type=int, default=50)
    ap.add_argument("--zigzag-pct", type=float, default=DEFAULT_PARAMS["zigzag_pct"])
    run(ap.parse_args())


if __name__ == "__main__":
    main()
