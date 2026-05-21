"""[생존자편향] 상장폐지 *진짜 실패* 보통주 코호트 + 폐지 전 일별가격 수집.

도플갱어 부검의 구조적 공백을 메운다: build_control_sample 의 비위너 풀은
trough/peak/n_days≥60 으로 걸러 *상폐로 고점을 못 만든 종목이 애초에
배제* 됨 → "사망 도플갱어 0"은 생존자 편향의 가시화였다. 이 스크립트는
그 빠진 코호트를 FinanceDataReader(KRX 아카이브, API키 불필요)로 복원.

수집 원칙(기존 파이프라인 컨벤션 동일):
 · 환각 금지·추정 금지 — 가격/사유 없으면 결손대로 기록.
 · *진짜 실패* 만: 감사의견거절·상폐기준해당·자본잠식·파산·횡령 등.
   ETF신탁만료·합병·완전자회사화·지주전환·스팩청산·신주인수권만료 =
   −100% 손실 아님 → 제외(과대보정 방지).
 · I축(외인/기관 수급)은 폐지종목 비제공 → 본 코호트는 가격기반
   스크린(L·선행상승·신고가)만 대상, I 결손은 분석단에서 명시.

출력: research/oneil-model-book/cycles/<cycle>-delisted/
        _universe_prices.json  (ctrl500 과 동일 {code:{d:[],c:[]}} 스키마)
        delisted_meta.json     ({code:{name,market,delisting_date,reason,
                                  listing_date,n_days,first,last,last_close}})
재실행 안전: 이미 가격 있는 종목은 건너뜀(--refresh 로 강제 재수집).

사용: python scripts/oneil_model_book/collect_delisted.py --cycle c2024-12
      python scripts/oneil_model_book/collect_delisted.py --all
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CYDIR = ROOT / "research" / "oneil-model-book" / "cycles"

# 진짜 실패(−100% 성격) — 사유에 아래 키워드 포함이면 후보
FAIL_KW = (
    "상장폐지기준", "감사의견", "의견거절", "감사범위", "계속기업",
    "자본전액잠식", "자본잠식", "부도", "회생절차", "파산", "해산사유",
    "횡령", "배임", "매출액 미달", "매출액미달", "시가총액 미달",
    "시가총액미달", "관리종목 지정 후", "관리종목지정 후", "불성실공시",
)
# 실패 아님(가치보전/단순소멸) — 사유/이름에 포함이면 무조건 제외(override)
EXCL_KW = (
    "수익증권", "신탁", "피흡수합병", "흡수합병", "합병상장", "합병으로",
    "완전자회사", "지주회사", "신주인수권", "전환사채", "교환사채",
    "액면", "분할", "스팩", "기업인수목적", "정리매매 종료 후 단순",
    "단순분할", "재상장", "이전상장", "공개매수",
)


def cycle_window(cid):
    ci = json.loads((CYDIR / "cycles_index.json").read_text(encoding="utf-8"))
    lst = ci["cycles"] if isinstance(ci, dict) else ci
    for c in lst:
        if c["cycle_id"] == cid:
            return c["anchor"], c["cycle_end"]
    raise SystemExit(f"cycle {cid} not in cycles_index.json")


def _shift_years(iso, yrs):
    y, m, d = iso.split("-")
    return f"{int(y)+yrs:04d}-{m}-{d}"


def is_fail(reason, name):
    r = reason if isinstance(reason, str) else ""
    n = name if isinstance(name, str) else ""
    if any(k in r for k in EXCL_KW) or any(k in n for k in EXCL_KW):
        return False
    return any(k in r for k in FAIL_KW)


def collect(cid, fdr, dl, refresh):
    import pandas as pd
    anchor, cend = cycle_window(cid)
    px_start = _shift_years(anchor, -3)            # 선행상승·252일 RS 여유
    # 폐지일이 사이클 앵커 이후(=사이클 동안 거래되다 죽음). 상한=오늘.
    sub = dl[(dl["DelistingDate"] >= pd.Timestamp(anchor))
             & (dl["Symbol"].astype(str).str.fullmatch(r"\d{6}"))
             & (dl["SecuGroup"].astype(str).str.contains("주권"))
             & (dl["Market"].isin(["KOSPI", "KOSDAQ"]))].copy()
    sub = sub[[is_fail(rr, nn) for rr, nn
               in zip(sub["Reason"], sub["Name"])]]
    sub = sub.sort_values("DelistingDate")

    out = CYDIR / f"{cid}-delisted"
    out.mkdir(parents=True, exist_ok=True)
    px_p, meta_p = out / "_universe_prices.json", out / "delisted_meta.json"
    PX = json.loads(px_p.read_text(encoding="utf-8")) if px_p.exists() else {}
    META = (json.loads(meta_p.read_text(encoding="utf-8"))
            if meta_p.exists() else {})

    n = len(sub)
    print(f"[{cid}] 진짜실패 보통주 후보 {n} "
          f"(폐지창 {anchor}~ / 가격 {px_start}~폐지일)", file=sys.stderr)
    miss = []
    for i, (_, r) in enumerate(sub.iterrows(), 1):
        code = str(r["Symbol"])
        ddate = str(r["DelistingDate"].date())
        if code in PX and not refresh:
            continue
        try:
            df = fdr.DataReader(code, px_start, ddate)
        except Exception as e:
            META[code] = {"name": r["Name"], "market": r["Market"],
                          "delisting_date": ddate, "reason": r["Reason"],
                          "error": f"{type(e).__name__}:{str(e)[:60]}"}
            miss.append(code)
            continue
        if df is None or df.empty or "Close" not in df or len(df) < 60:
            META[code] = {"name": r["Name"], "market": r["Market"],
                          "delisting_date": ddate, "reason": r["Reason"],
                          "error": "결손(가격 없음/60일 미만)",
                          "n_days": 0 if df is None else len(df)}
            miss.append(code)
            continue
        df = df[df["Close"].notna() & (df["Close"] > 0)]
        d = [x.strftime("%Y-%m-%d") for x in df.index]
        c = [float(x) for x in df["Close"]]
        PX[code] = {"d": d, "c": c}
        lst_dt = (str(r["ListingDate"].date())
                  if not pd.isna(r["ListingDate"]) else None)
        META[code] = {
            "name": r["Name"], "market": r["Market"],
            "delisting_date": ddate, "reason": r["Reason"],
            "listing_date": lst_dt, "n_days": len(c),
            "first": d[0], "last": d[-1], "last_close": c[-1]}
        if i % 15 == 0:
            print(f"  .. {i}/{n} (수집 {len(PX)}, 결손 {len(miss)})",
                  file=sys.stderr)
        time.sleep(0.15)

    px_p.write_text(json.dumps(PX, ensure_ascii=False), encoding="utf-8")
    meta_p.write_text(json.dumps(META, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print(f"[{cid}] 저장: {px_p.name} {len(PX)}종 · {meta_p.name} "
          f"(결손 {len(miss)}) → {out}", file=sys.stderr)
    return cid, anchor, cend, n, PX, META, miss


def review(cid, anchor, cend, n_cand, PX, META, miss):
    """검수용 요약 — 코호트·사유·가격커버·붕괴폭 예시."""
    from collections import Counter
    ok = [m for m in META.values() if not m.get("error")]
    rc = Counter()
    for m in META.values():
        rs = (m.get("reason") or "결손")
        rc[rs.split("(")[0][:24]] += 1
    L = [f"───── 검수: {cid}-delisted (폐지창 {anchor}~, 가격~폐지일) ─────",
         f"진짜실패 보통주 후보 {n_cand} → 가격수집 {len(ok)} · 결손 {len(miss)}",
         "폐지사유 분포(상위):"]
    for k, v in rc.most_common(8):
        L.append(f"  {v:3d}  {k}")
    # 붕괴폭: 폐지창 내 최고가 대비 마지막 체결가
    ex = []
    for code, m in META.items():
        if m.get("error"):
            continue
        s = PX.get(code)
        if not s:
            continue
        seg = [c for d, c in zip(s["d"], s["c"]) if d >= anchor]
        if not seg:
            continue
        hi = max(seg)
        drop = m["last_close"] / hi - 1 if hi else None
        ex.append((drop, code, m["name"], m["delisting_date"],
                   m["reason"], m["last_close"], hi))
    ex.sort(key=lambda x: (x[0] if x[0] is not None else 0))
    L.append(f"가격커버 종목 {len(ex)} · 폐지창 내 고점→마지막 붕괴폭 "
             "(샘플 — 깊은 순):")
    L.append("  코드  종목            폐지일      고점→마지막   사유")
    for drop, code, nm, dd, rs, lc, hi in ex[:12]:
        L.append(f"  {code} {str(nm)[:12]:12s} {dd} "
                 f"{(drop*100 if drop is not None else 0):+7.1f}%  "
                 f"({hi:,.0f}→{lc:,.0f})  {str(rs)[:22]}")
    if len(ex) > 12:
        md = sorted(d for d, *_ in ex if d is not None)
        L.append(f"  ... 총 {len(ex)}종, 붕괴폭 중앙 "
                 f"{md[len(md)//2]*100:+.1f}% (전부 도플갱어 부검 사망코호트 후보)")
    L += ["주: 가격기반 스크린(L·선행상승·신고가)만 적용 예정 — 폐지종목",
          "  외인/기관 수급 비제공 → I축 결손(분석단 명시). 사유경계·",
          "  스팩혼입 가능성은 한계로 표기. 추정 없음·결손은 결손대로.",
          ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", default=None)
    ap.add_argument("--all", action="store_true",
                    help="c2024-12, c2020-03 둘 다")
    ap.add_argument("--refresh", action="store_true",
                    help="이미 수집한 종목도 강제 재수집")
    a = ap.parse_args()
    try:
        import FinanceDataReader as fdr
    except ModuleNotFoundError:
        raise SystemExit("finance-datareader 미설치 → "
                         "pip install finance-datareader")
    import pandas as pd

    cycles = (["c2024-12", "c2020-03"] if a.all
              else [a.cycle or "c2024-12"])
    print("KRX-DELISTING 명단 적재 중...", file=sys.stderr)
    dl = fdr.StockListing("KRX-DELISTING")
    dl["DelistingDate"] = pd.to_datetime(dl["DelistingDate"], errors="coerce")
    dl["ListingDate"] = pd.to_datetime(dl["ListingDate"], errors="coerce")
    dl = dl[dl["DelistingDate"].notna()]
    print(f"전체 상장폐지 {len(dl)}종 적재.", file=sys.stderr)

    reports = []
    for cid in cycles:
        reports.append(review(*collect(cid, fdr, dl, a.refresh)))
    rpt = "\n".join(reports)
    out = ROOT / "research" / "oneil-model-book" / "_delisted_cohort.txt"
    out.write_text(rpt, encoding="utf-8")
    print(f"\nsaved review: {out}", file=sys.stderr)
    print("\n" + rpt)


if __name__ == "__main__":
    main()
