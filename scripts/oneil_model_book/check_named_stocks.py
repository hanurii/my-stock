"""지정 종목의 '폭발 직전' 시점 + 한국식 CAN SLIM/타이밍 부합 여부 검증.

추측 금지 — 5y 종가 캐시·지수·네이버 수급으로 실측. 종목별:
  · 5y 창 최대 종가=peak, 그 *이전* 최저=trough(= 폭발 직전 저점)
  · 규칙진입후보 = trough 이후 *첫 추세확인일*(종가>상승50일선 & >20일전)
  · 그 진입후보일에 축 평가: L(RS 백분위, 전 종목 동일일 기준), M(지수 국면),
    52주고가 위치, 50일선 과열도, 신선도, 경과율, I(외인/기관 60일)
거래량은 캐시에 없음 → 정성(차트) 확인 필요로 명시(환각 금지).

사용:  python check_named_stocks.py 005930 000660 009150
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cyclecfg  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402
from canslim_lib.fetch import (fetch_yahoo_chart, resolve_corp_code,  # noqa: E402
                               load_corp_code_map)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_variables import yoy_pct  # noqa: E402

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles" / "c2024-12"

_IDXC: dict = {}


def _ep(date_str):
    return int(datetime.strptime(date_str, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def pit_qkey(date_str):
    """date 시점에 *공시 가용*했던 최근 분기 qkey=YYYYMM (point-in-time).
    Q1/2/3 보고서 ≈ 분기말+45일, Q4(연간) ≈ +90일 가정."""
    y, m, dd = (int(x) for x in date_str.split("-"))
    best = None
    for yy in (y, y - 1):
        for qm, lag in ((12, 90), (9, 45), (6, 45), (3, 45)):
            qend = datetime(yy, qm, 28) + timedelta(days=4)
            avail = qend + timedelta(days=lag)
            if avail <= datetime(y, m, dd):
                if best is None or (yy, qm) > best:
                    best = (yy, qm)
    return f"{best[0]}{best[1]:02d}" if best else None


def sma(c, j, w):
    return sum(c[j - w + 1:j + 1]) / w if j >= w - 1 else None


def confirmed(c, d):
    if d < 60:
        return False
    m, mp = sma(c, d, 50), sma(c, d - 10, 50)
    return (m is not None and mp is not None and c[d] > m and m > mp
            and c[d] > c[d - 20])


def regime(sym, date_str):
    """장기조회(2017~) 지수로 date 시점 50/200일선 국면 — 옛 날짜 결손 해소."""
    if sym not in _IDXC:
        ch = fetch_yahoo_chart(sym, period1=_ep("2017-01-01"),
                               period2=_ep("2026-12-31"), interval="1d")
        _IDXC[sym] = ch or {}
    ch = _IDXC[sym]
    ts, c = ch.get("timestamps"), ch.get("closes")
    if not ts or not c:
        return "결손(지수조회 실패)"
    ds = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d") for t in ts]
    i = max((k for k in range(len(ds)) if ds[k] <= date_str), default=None)
    if i is None or i < 200:
        return "결손(200일 이력 부족)"
    px, m50, m200 = c[i], sum(c[i-49:i+1])/50, sum(c[i-199:i+1])/200
    return "상승추세" if (px > m50 > m200 and px > m200) else (
        "중립" if px > m200 else "하락추세")


def main():
    codes = sys.argv[1:] or ["005930", "000660", "009150"]
    U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    w = json.loads((CY / "winners.json").read_text(encoding="utf-8"))
    nm = {r["code"]: (r["name"], r["market"]) for r in w["ranked_valid"]}
    corp_map = load_corp_code_map()
    last_cache = U[list(U)[0]]["d"][-1]

    out = ["지정 종목 — 폭발 직전 시점 & 한국식 CAN SLIM/타이밍 부합 검증",
           f"(5y 종가 캐시 {U[list(U)[0]]['d'][0]}~{U[list(U)[0]]['d'][-1]}, "
           "RS=동일일 전종목 52주수익률 백분위. 거래량=캐시無, 차트 확인 요)",
           ""]
    for code in codes:
        s = U.get(code)
        name, mkt = nm.get(code, ("?", "?"))
        if not s or len(s.get("c", [])) < 300:
            out.append(f"### {name}({code}) — 데이터 부족\n")
            continue
        d, c = s["d"], s["c"]
        pi = max(range(len(c)), key=lambda k: c[k])           # 최대 종가일
        ti = min(range(0, pi + 1), key=lambda k: c[k])        # 그 이전 최저=폭발직전 저점
        # 규칙진입후보 = trough 이후 첫 추세확인일
        gi = next((x for x in range(ti, pi) if confirmed(c, x)), None)

        seg = f"\n### {name}({code}/{mkt})\n"
        seg += (f"- 5y 최저(폭발 직전 저점): {d[ti]} @ {c[ti]:,.0f}\n"
                f"- 5y 최고(폭발 후 고점): {d[pi]} @ {c[pi]:,.0f}  "
                f"→ 저점대비 ×{c[pi]/c[ti]:.1f}\n")
        if gi is None:
            seg += "- 규칙 진입후보: 추세확인일 없음(=조용한 조기 진입 신호 부재)\n"
            out.append(seg)
            continue

        T = d[gi]
        # L: 같은 날짜 T 기준 전 종목 52주 수익률 백분위
        rets = {}
        for cc, ss in U.items():
            dd, ccl = ss.get("d"), ss.get("c")
            if not dd or not ccl:
                continue
            j = max((k for k in range(len(dd)) if dd[k] <= T), default=None)
            if j is None or j < 252 or ccl[j-252] <= 0:
                continue
            rets[cc] = ccl[j] / ccl[j-252] - 1
        rspct = None
        if code in rets:
            order = sorted(rets, key=lambda k: rets[k])
            rspct = round(100 * order.index(code) / (len(order)-1), 1)
        hi52 = max(c[max(0, gi-252):gi+1])
        pct_hi = round(c[gi]/hi52*100, 1) if hi52 else None
        ext = round((c[gi]/sma(c, gi, 50)-1)*100, 1)
        cross = next((x for x in range(gi, 60, -1)
                      if confirmed(c, x) and not confirmed(c, x-1)), gi)
        elapsed = round((gi-ti)/(pi-ti), 2) if pi > ti else None
        resid = round((c[pi]/c[gi]-1)*100, 1)
        # 선별(L=RS≥80) 이 *처음* 켜지는 날 — 폭발저점 이후 주간 스캔
        def rs_at(idx):
            tt = d[idx]
            rr = {}
            for cc, ss in U.items():
                dd, ccl = ss.get("d"), ss.get("c")
                if not dd or not ccl:
                    continue
                jj = max((k for k in range(len(dd)) if dd[k] <= tt), default=None)
                if jj is None or jj < 252 or ccl[jj-252] <= 0:
                    continue
                rr[cc] = ccl[jj] / ccl[jj-252] - 1
            if code not in rr:
                return None
            oo = sorted(rr, key=lambda k: rr[k])
            return round(100 * oo.index(code) / (len(oo)-1), 1)
        rule_i = None
        for x in range(ti, pi, 5):
            if x < 252 or not confirmed(c, x):
                continue
            rv = rs_at(x)
            if rv is not None and rv >= 80:
                rule_i = x
                break
        m_now = regime("%5EKS11" if mkt == "KOSPI" else "%5EKQ11", T)
        # I: 캐시최신~T 거리만큼 frgn 페이지 확대(과거 도달). 1p≈20거래일.
        from datetime import date as _date
        dgap = (_date.fromisoformat(last_cache) - _date.fromisoformat(T)).days
        pages = min(90, max(8, dgap // 28 + 6))
        ipass, fg, og = None, None, None
        try:
            rows = fetch_naver_org_flow(code, pages=pages, sleep_ms=180)
            sel = [r for r in rows if r["date"] <= T][:60]
            if len(sel) >= 30:                       # 충분 도달했을 때만 판정
                fg = sum(r.get("fgn_net") or 0 for r in sel)
                og = sum(r.get("org_net") or 0 for r in sel)
                ipass = (fg > 0) or (og > 0)
        except Exception:
            pass
        i_txt = (f"외인 {fg:,} / 기관 {og:,} ({len(sel)}일) → "
                 f"{'충족' if ipass else '미충족'}"
                 if ipass is not None
                 else f"결손(frgn {pages}p로도 미도달 — 추정 안 함)")
        # C: point-in-time 최근 분기 EPS YoY (DART)
        cq = pit_qkey(T)
        cval, csrc = (None, "qkey 산출 실패")
        if cq:
            cc_corp, _ = resolve_corp_code(code, corp_map)
            if cc_corp:
                cval, csrc = yoy_pct(cc_corp, cq, "eps", code)
        c_txt = (f"{cq} EPS YoY {cval}% ({csrc}) → "
                 f"{'충족(>0)' if isinstance(cval,(int,float)) and cval>0 else '미충족/결손'}"
                 if cq else "결손")

        L_ok = rspct is not None and rspct >= 80
        seg += (
            f"- **규칙 진입후보(첫 추세확인): {T} @ {c[gi]:,.0f}** "
            f"(전환후 {gi-cross}일, 상승경과율 {elapsed}, 이후 잔존상승 +{resid}%)\n"
            f"  · L 상대강도: RS {rspct}%  → {'충족(≥80)' if L_ok else '미충족'}\n"
            f"  · M 시장국면({mkt}, {T}): {m_now}  "
            f"→ {'충족' if m_now=='상승추세' else '미충족/부분'}\n"
            f"  · I 수급(60일): {i_txt}\n"
            f"  · C 실적: {c_txt}\n"
            f"  · 타이밍: 52주고가 대비 {pct_hi}%  / 50일선 위 {ext}%  "
            f"→ {'조용·아래(부합)' if (pct_hi or 0)<=88 and ext<=20 else '신고가 근접/과열(이미 늦음)'}\n"
            f"  · 거래량: 캐시 미수록 — 그날 거래량이 평균 *이하*였는지 차트 확인 요\n")
        if rule_i is not None:
            g0 = round((c[rule_i]/c[ti]-1)*100, 1)
            rr = round((c[pi]/c[rule_i]-1)*100, 1)
            seg += (f"- **선별까지 충족(L RS≥80 최초) : {d[rule_i]} @ "
                    f"{c[rule_i]:,.0f}** — 폭발저점 대비 이미 +{g0}%, "
                    f"이후 잔존 +{rr}% (조기 진입후보보다 *늦은* 선별확정)\n")
        else:
            seg += ("- 선별까지 충족(L RS≥80): 폭발 구간 내 도달 시점 없음 "
                    "— 이 종목은 *주도주(L) 기준으론 끝까지 비주도*\n")
        out.append(seg)

    txt = "\n".join(out)
    (CY / "_named_check.txt").write_text(txt, encoding="utf-8")
    print(f"saved: {CY/'_named_check.txt'} ({len(codes)} codes)", file=sys.stderr)


if __name__ == "__main__":
    main()
