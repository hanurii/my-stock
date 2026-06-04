"""KIS 통합시세(NXT 반영)로 C 게이트 통과 종목의 현재가·신고가 대비를 갱신.

입력 : public/data/can-slim-candidates.json (메인 풀스캔 결과)
조건 : criteria.C.pass = true (passesCGate) 통과 종목만
호출 : 종목별 KIS `inquire-price` (FID_COND_MRKT_DIV_CODE=UN, 통합시세)
갱신 :
  - public/data/can-slim-candidates.json
      · current_price → KIS current
      · pct_from_52w_high → (current − high_52w) / high_52w × 100  (high_52w 시계열 max 그대로)
  - public/data/trend-template-candidates.json (해당 종목이 트렌드 평가에도 있는 경우)
      · current_price → KIS current
  - public/data/trend-template-c-scored.json (해당 종목)
      · trend_current_price → KIS current
산출 : 콘솔에 갱신 종목 수 / 신고가 갱신이 풀린 종목 보고.

키 없거나 토큰 실패 시 즉시 종료 — 페이지는 KRX 종가 그대로 fallback.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
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


def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

from canslim_lib.kis_api import get_access_token, fetch_integrated_price  # noqa: E402

KST = timezone(timedelta(hours=9))
C_DATA = ROOT / "public" / "data" / "can-slim-candidates.json"
TT_DATA = ROOT / "public" / "data" / "trend-template-candidates.json"
TT_C = ROOT / "public" / "data" / "trend-template-c-scored.json"
MAX_WORKERS = 4  # KIS rate limit (초당 ~8회) 안전 마진


def passes_c_gate(cand: dict) -> bool:
    return (cand.get("criteria") or {}).get("C", {}).get("pass") is True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="디버그용 — 처음 N종목만")
    ap.add_argument("--dry-run", action="store_true",
                    help="JSON 저장 안 함, 결과만 출력")
    args = ap.parse_args()

    if not os.environ.get("KIS_APP_KEY") or not os.environ.get("KIS_APP_SECRET"):
        print("⚠️  KIS_APP_KEY / KIS_APP_SECRET 환경변수 없음 — KRX 종가 그대로 두고 종료.")
        sys.exit(0)

    if not C_DATA.exists():
        print(f"❌ {C_DATA.relative_to(ROOT)} 없음 — screen_canslim.py --save 먼저 실행.")
        sys.exit(1)

    print(f"🔑 KIS 토큰 발급/확인")
    token = get_access_token()
    if not token:
        print("⚠️  KIS 토큰 발급 실패 — 키 만료/네트워크 점검 후 재시도. KRX 종가 그대로 둡니다.")
        sys.exit(0)
    print(f"  ✓ OK")

    print(f"\n📂 입력 로드: {C_DATA.relative_to(ROOT)}")
    c_data = json.loads(C_DATA.read_text(encoding="utf-8"))
    gate_pass = [c for c in c_data["candidates"] if passes_c_gate(c)]
    if args.limit > 0:
        gate_pass = gate_pass[:args.limit]
    print(f"  C 게이트 통과: {len(gate_pass)}종목")

    # 트렌드 결과 로드 (옵션)
    tt_data = None
    if TT_DATA.exists():
        tt_data = json.loads(TT_DATA.read_text(encoding="utf-8"))
        tt_by_code = {c["code"]: c for c in tt_data.get("candidates", [])}
    else:
        tt_by_code = {}
    tt_c_data = None
    if TT_C.exists():
        tt_c_data = json.loads(TT_C.read_text(encoding="utf-8"))
        tt_c_by_code = {c["code"]: c for c in tt_c_data.get("candidates", [])}
    else:
        tt_c_by_code = {}

    print(f"\n💎 KIS 통합시세 fetch (병렬 {MAX_WORKERS}워커)")

    def task(cand: dict) -> tuple[str, dict | None]:
        return cand["code"], fetch_integrated_price(cand["code"], token=token, market_div="UN")

    results: dict[str, dict] = {}

    def run_batch(items: list, label: str) -> int:
        completed = 0
        success = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            for code, res in ex.map(task, items):
                completed += 1
                if res:
                    results[code] = res
                    success += 1
                if completed % 50 == 0 or completed == len(items):
                    print(f"  [{label}] 진행 {completed}/{len(items)} (성공 {success})")
        return success

    success = run_batch(gate_pass, "1차")

    # 실패한 종목 재시도 (rate limit 영향 줄이려 1초 sleep + 재실행)
    failed = [c for c in gate_pass if c["code"] not in results]
    if failed:
        import time as _t
        _t.sleep(1.0)
        print(f"  실패 {len(failed)}종목 재시도")
        retry_success = run_batch(failed, "2차")
        success += retry_success

    if success == 0:
        print("\n⚠️  KIS 호출 모두 실패 — KRX 종가 그대로 둡니다. (토큰/키 확인)")
        sys.exit(0)
    print(f"\n  KIS 시세 수신: {success}/{len(gate_pass)}")

    # ── 메인 candidates 갱신 ─────────
    changed = 0
    de_high: list[tuple[str, str, int, int, float]] = []  # 신고가 풀린 종목
    high_52w_by_code: dict[str, float | int | None] = {}
    for cand in c_data["candidates"]:
        code = cand["code"]
        if code not in results:
            continue
        new_cur = results[code]["current"]
        old_cur = cand.get("current_price")
        # high_52w 는 trend extras 에 있으나 메인 candidates 에는 직접 없음 — 다만
        # pct_from_52w_high 가 이미 (last - high_52w)/high_52w * 100 로 저장됨.
        # 역산: high_52w = old_cur / (1 + old_pct/100). 그러나 old_pct 가 정확하므로
        # 더 단순하게 trend 의 extras.high_52w 가용 시 그것 사용.
        high_52w = None
        tt_row = tt_by_code.get(code)
        if tt_row:
            high_52w = (tt_row.get("extras") or {}).get("high_52w")
        if high_52w is None:
            # 폴백: 역산
            old_pct = cand.get("pct_from_52w_high")
            if old_cur and old_pct is not None:
                denom = 1.0 + (old_pct / 100.0)
                if denom > 0:
                    high_52w = old_cur / denom
        high_52w_by_code[code] = high_52w

        new_pct = None
        if high_52w and high_52w > 0:
            new_pct = round((new_cur - high_52w) / high_52w * 100.0, 2)
            cand["pct_from_52w_high"] = new_pct
        was_at_high = (cand.get("pct_from_52w_high") is None) or False
        old_pct = cand.get("pct_from_52w_high")
        cand["current_price"] = new_cur
        cand["_price_source"] = "KIS_UN"
        if new_pct is not None:
            cand["pct_from_52w_high"] = new_pct
        # 변화 감지
        if old_cur and old_cur != new_cur:
            changed += 1
            # KIS current < high_52w 이고 KRX current ≈ high_52w 였던 케이스 = 신고가 풀린 종목
            if high_52w and high_52w > 0 and old_cur >= high_52w * 0.9995 and new_cur < high_52w * 0.995:
                de_high.append((code, cand.get("name", "?"), int(old_cur), int(new_cur),
                                round((new_cur - high_52w) / high_52w * 100.0, 2)))

    # ── 트렌드 candidates 갱신 (해당 종목만) ─────────
    tt_changed = 0
    if tt_data:
        for tcand in tt_data.get("candidates", []):
            if tcand["code"] in results:
                tcand["current_price"] = results[tcand["code"]]["current"]
                tcand["_price_source"] = "KIS_UN"
                tt_changed += 1

    # ── 트렌드 c-scored 갱신 ─────────
    ttc_changed = 0
    if tt_c_data:
        for ccand in tt_c_data.get("candidates", []):
            if ccand["code"] in results:
                ccand["trend_current_price"] = results[ccand["code"]]["current"]
                ccand["_price_source"] = "KIS_UN"
                ttc_changed += 1

    # ── 저장 ─────────
    if not args.dry_run:
        c_data["_kis_refined_at"] = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
        c_data["_kis_refined_count"] = success
        C_DATA.write_text(json.dumps(c_data, ensure_ascii=False, indent=2), encoding="utf-8")
        if tt_data:
            tt_data["_kis_refined_at"] = c_data["_kis_refined_at"]
            TT_DATA.write_text(json.dumps(tt_data, ensure_ascii=False, indent=2), encoding="utf-8")
        if tt_c_data:
            tt_c_data["_kis_refined_at"] = c_data["_kis_refined_at"]
            TT_C.write_text(json.dumps(tt_c_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 저장:")
        print(f"  - {C_DATA.relative_to(ROOT)} (current_price·pct_from_52w_high {success}종목 갱신)")
        if tt_data:
            print(f"  - {TT_DATA.relative_to(ROOT)} ({tt_changed}종목)")
        if tt_c_data:
            print(f"  - {TT_C.relative_to(ROOT)} ({ttc_changed}종목)")
    else:
        print(f"\n[dry-run] 저장 안 함. 갱신 종목: {changed}")

    # ── 신고가 풀린 종목 보고 ─────────
    if de_high:
        print(f"\n🔻 KIS 통합시세 적용 후 신고가 갱신이 풀린 종목 ({len(de_high)}건):")
        de_high.sort(key=lambda x: x[4])  # 가장 많이 떨어진 순
        for code, name, krx, kis, new_pct in de_high[:20]:
            diff = kis - krx
            print(f"  {code} {name[:14]:14s} KRX {krx:>10,} → KIS {kis:>10,} ({diff:+,}) | 신고가 대비 {new_pct:+.2f}%")
        if len(de_high) > 20:
            print(f"  ... 외 {len(de_high) - 20}건")
    else:
        print(f"\n  (신고가 갱신이 풀린 종목 없음)")


if __name__ == "__main__":
    main()
