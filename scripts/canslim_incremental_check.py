"""DART 새 공시 + 신규 상장 종목 식별 + stock_cache 부분 무효화.

매일 /make-hero 스킬의 첫 단계. 이 스크립트가 무효화한 종목만 다음
screen_canslim.py 풀스캔에서 새로 fetch 되므로 풀스캔 시간이 단축된다.

조건:
  - DART list.json 으로 최근 N일(default 2) 정기보고서·잠정실적 공시 corp_code 수집
  - 우리 universe 의 corp_code 매핑 적용
  - 신규 상장 종목 (이전 candidates JSON 에 없던 코드) 추가
  - 합집합의 stock_cache (`.cache/canslim_stocks/<code>.json`) 만 삭제

사용:
  python scripts/canslim_incremental_check.py             # 실제 무효화
  python scripts/canslim_incremental_check.py --dry-run   # 대상만 출력, 삭제 안 함
  python scripts/canslim_incremental_check.py --days-back 7  # 일주일치 조회
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
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

from canslim_lib.fetch import dart_get, load_corp_code_map  # noqa: E402
from canslim_lib.pykrx_universe import fetch_universe_with_cap  # noqa: E402
from canslim_lib import stock_cache  # noqa: E402

C_DATA = ROOT / "public" / "data" / "can-slim-candidates.json"


def fetch_disclosure_corp_codes(bgn_de: str, end_de: str, pblntf_ty: str,
                                 max_pages: int = 10) -> set[str]:
    """기간 내 특정 공시 유형으로 보고된 corp_code 셋.

    DART list.json 페이지네이션 처리 (page_count=100, 최대 max_pages).
    last_reprt_at=Y (정정 보고서가 있으면 최종본만).
    """
    out: set[str] = set()
    for page_no in range(1, max_pages + 1):
        items = dart_get("list", {
            "bgn_de": bgn_de,
            "end_de": end_de,
            "pblntf_ty": pblntf_ty,
            "page_no": str(page_no),
            "page_count": "100",
            "last_reprt_at": "Y",
        })
        if not items:
            break
        for it in items:
            cc = (it.get("corp_code") or "").strip()
            if cc:
                out.add(cc)
        if len(items) < 100:
            break
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days-back", type=int, default=2,
                    help="DART 공시 조회 시작일 (오늘로부터 N일 전, default 2 = 어제~오늘)")
    ap.add_argument("--dry-run", action="store_true",
                    help="캐시 삭제 안 함, 대상 목록만 출력")
    args = ap.parse_args()

    if "DART_API_KEY" not in os.environ:
        print("❌ DART_API_KEY 환경변수 없음 — .env 확인.")
        sys.exit(1)

    today = datetime.now()
    bgn = today - timedelta(days=args.days_back)
    bgn_de = bgn.strftime("%Y%m%d")
    end_de = today.strftime("%Y%m%d")

    print(f"📡 DART 공시 조회: {bgn_de} ~ {end_de}")
    print("  pblntf_ty=A (정기보고서: 사업·반기·1·3분기 보고서)")
    a_codes = fetch_disclosure_corp_codes(bgn_de, end_de, "A")
    print(f"    → corp_code {len(a_codes)}개")
    print("  pblntf_ty=I (거래소공시: 잠정실적·주요사항 등)")
    i_codes = fetch_disclosure_corp_codes(bgn_de, end_de, "I")
    print(f"    → corp_code {len(i_codes)}개")
    dart_corp_codes = a_codes | i_codes
    print(f"  ── 합계 corp_code: {len(dart_corp_codes)}개")

    print("\n📦 DART corp_code ↔ 종목코드 매핑")
    corp_map = load_corp_code_map()  # {stock_code: corp_code}
    code_by_corp: dict[str, str] = {}
    for stock_code, corp_code in corp_map.items():
        code_by_corp[corp_code] = stock_code
    changed_stock_codes = {code_by_corp[cc] for cc in dart_corp_codes if cc in code_by_corp}
    print(f"  우리 universe 매핑된 종목: {len(changed_stock_codes)}개")

    print("\n🆕 신규 상장 종목 식별")
    universe = fetch_universe_with_cap("all")
    universe_codes = {u["code"] for u in universe}
    if C_DATA.exists():
        prev = json.loads(C_DATA.read_text(encoding="utf-8"))
        prev_codes: set[str] = set()
        for c in prev.get("candidates", []):
            prev_codes.add(c["code"])
        for f in prev.get("failed_stocks", []):
            prev_codes.add(f.get("code", ""))
        prev_codes.discard("")
    else:
        prev_codes = set()
        print("  ⚠️ 이전 can-slim-candidates.json 없음 — 전체 universe 가 신규로 처리됨")
    new_listed = universe_codes - prev_codes
    print(f"  신규 상장 종목: {len(new_listed)}개")

    invalidate = changed_stock_codes | new_listed
    print(f"\n🎯 갱신 대상 (DART 새 공시 ∪ 신규 상장): {len(invalidate)}종목")

    if args.dry_run:
        print("\n[dry-run] 캐시 삭제 안 함. 대상 종목 일부 미리보기:")
        sample = sorted(invalidate)[:30]
        uni_by_code = {u["code"]: u for u in universe}
        for code in sample:
            u = uni_by_code.get(code)
            name = u["name"] if u else "(universe 외)"
            market = u["market"] if u else "?"
            tag = " [신규]" if code in new_listed else ""
            print(f"  {code} {name[:18]:18s} {market:6s}{tag}")
        if len(invalidate) > 30:
            print(f"  ... 외 {len(invalidate) - 30}종목")
        return

    print("\n🗑  stock_cache 부분 무효화")
    cache_dir = stock_cache.CACHE_DIR
    removed = 0
    missing = 0
    for code in invalidate:
        p = cache_dir / f"{code}.json"
        if p.exists():
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
        else:
            missing += 1
    print(f"  무효화 완료: {removed}/{len(invalidate)} (캐시 없던 종목 {missing})")
    print(f"\n✅ 다음 screen_canslim.py 풀스캔에서 무효화한 {removed}종목만 새로 fetch 됩니다.")


if __name__ == "__main__":
    main()
