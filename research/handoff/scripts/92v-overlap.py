# -*- coding: utf-8 -*-
r"""92v — **92 의 승자 칸이 85 의 `atr_band ④` 와 «같은 것»인가.**

검증 세션 지적(`8a3cae58`):
> 85 ㉯ 승자가 `atr_band ④` 였고 더블 6.57% vs 기준 1.76% = 3.7배인데 **거래당 +1.184% = 꼴찌**.
> 86 에서 그 칸이 `atr20 5분위`에 **100.0% 포함**됐다.
> **92 가 「실적」을 잰 것인지 「변동성」을 다시 잰 것인지는 «겹침을 재기 전에는» 모른다.**

🚨 **이것은 «검정»이 아니라 «서술»이다** — 예산 0.
   특징이 «무엇인지» 재는 것은 가설 검정이 아니라 **정의 확인**이다(86 의 자카드 측정과 같은 자리).
   ⚠️ **서술 «결과»로 결론을 바꾸는 순간 그건 검정이 된다.** 여기서는 «겹치는가»만 적는다.

`atr_band` 는 **경로 레코드에 그대로 들어 있다** — 시세를 다시 안 읽는다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("m92", HERE / "92-us-fundamentals.py")
m = _u.module_from_spec(_s)
_s.loader.exec_module(m)


def main() -> int:
    print("=" * 100, flush=True)
    print("92v — 승자 칸이 85 의 `atr_band ④` 와 «같은 것»인가  (서술 · 판정에 안 씀)", flush=True)
    print("=" * 100, flush=True)

    fund = json.loads(m.FUND.read_text(encoding="utf-8"))["by"]
    packs = []
    for lab, (d0, d1), yrs in (
            ("고르기", m.PICK, range(1999, 2013)),
            ("판정①", m.TEST1, range(2012, 2018)),
            ("판정②", m.TEST2, range(2017, 2027))):
        rows, _miss, _n = m.build(tuple(yrs), d0, d1, fund)
        packs.append((lab, rows))
        print("  %s 진입 %s" % (lab, "{:,}".format(len(rows))), flush=True)

    rowsP = packs[0][1]
    # 분위 경계는 «고르기 창»에서 — 92 와 «같은» 것을 쓴다
    sel = {}
    for ax, want in (("roe", 0), ("dilution", 4)):
        cuts, nc, f = m.cells_for(rowsP, ax)
        sel[ax] = (f, want, nc)
        print("  %s → %d분위 (경계 %s)"
              % (ax, want + 1, " · ".join("%.4f" % c for c in cuts)), flush=True)

    for lab, rows in packs:
        print("\n" + "─" * 100, flush=True)
        print("### %s  (n=%s)" % (lab, "{:,}".format(len(rows))), flush=True)
        band = [r[0].get("_band") for r in rows]
        n = len(rows)
        bc = Counter(b for b in band if b)
        print("  atr_band 분포: %s"
              % " · ".join("%s %.1f%%" % (k, 100.0 * v / n) for k, v in sorted(bc.items())),
              flush=True)

        is4 = [bool(b and b.startswith("④")) for b in band]
        p4 = sum(is4) / n
        print("  atr_band ④(변동 매우 큼) 비율 **%.1f%%**" % (100 * p4), flush=True)

        for ax, (f, want, _nc) in sel.items():
            inax = [f(r[0][ax]) == want for r in rows]
            pa = sum(inax) / n
            both = sum(1 for a, b in zip(inax, is4) if a and b)
            either = sum(1 for a, b in zip(inax, is4) if a or b)
            print("\n  **%s %d분위**  (%.1f%% 의 진입)" % (ax, want + 1, 100 * pa), flush=True)
            print("     ④ 안에 든 비율   P(④ | %s) = **%.1f%%**  (전체 ④ 비율 %.1f%%)"
                  % (ax, 100.0 * both / max(1, sum(inax)), 100 * p4), flush=True)
            print("     거꾸로            P(%s | ④) = %.1f%%" % (ax, 100.0 * both / max(1, sum(is4))),
                  flush=True)
            print("     자카드            %.1f%%" % (100.0 * both / max(1, either)), flush=True)

            # ★ 층화 — 변동성을 «묶어 두고» 실적이 여전히 가르는가
            print("     ── 변동성을 «고정»하고 봐도 가르는가 (더블 도달률) ──", flush=True)
            for bk in sorted(bc):
                g = [(a, r) for a, b, r in zip(inax, band, rows) if b == bk]
                if len(g) < 200:
                    continue
                yin = [r[2] for a, r in g if a]
                yout = [r[2] for a, r in g if not a]
                if len(yin) < 30 or len(yout) < 30:
                    continue
                print("        %-12s n=%5d  %s 안 %5.2f%% (n=%4d) vs 밖 %5.2f%% (n=%5d)  차 %+5.2f%%p"
                      % (bk, len(g), ax, 100 * st.mean(yin), len(yin),
                         100 * st.mean(yout), len(yout),
                         100 * (st.mean(yin) - st.mean(yout))), flush=True)
    print("\n" + "=" * 100, flush=True)
    print("읽는 법: P(④ | 승자칸) 이 «전체 ④ 비율»과 비슷하면 겹치지 «않는» 것이고,", flush=True)
    print("        훨씬 높으면 92 는 85 의 발견을 «다른 이름»으로 다시 찾은 것이다.", flush=True)
    print("        층화 표에서 «각 변동성 칸 안»의 차가 0 에 가까우면 실적은 «껍데기»다.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
