# -*- coding: utf-8 -*-
"""16번에 ATR 구간 맞춤 대조를 붙인다(검증 [1] — 무조건 산출).

우리 거래는 ATR 중앙 5.62%인데 대조군은 4.4%다. 청산이 퍼센트(+20/−10)라
**변동성이 높으면 양쪽 문턱에 더 자주·더 빨리 닿는다.** 맞추지 않으면
A·C가 "선별 실력"이 아니라 **"변동성 기울기"**를 잡을 수 있다.

맞춤 방식: 우리 거래 **한 건마다** 같은 날 **같은 ATR 구간**의 대조 후보에서 하나 뽑는다.
구간이 비면 **인접 구간으로 물러나고 그 횟수를 센다**(조용한 실패 방지).
"""
import pathlib

p = pathlib.Path("research/handoff/scripts/16-selection-edge.py")
t = p.read_text(encoding="utf-8")
NL = chr(92) + "n"

old = """            # 우리 종목 x β1 문턱 (실행 가능한 분해)"""
new = """            # ── ATR 구간 맞춤 대조 (검증 [1]) — 우리 거래 한 건마다 같은 구간에서 뽑는다
            our_bands = []
            for e in ours:
                s_ = full.get(e["code"])
                di_ = _di(s_, D) if s_ else None
                av_ = atr_pct_at(s_, di_) if di_ is not None else None
                our_bands.append(atr_band(av_))
            for nm, pl in (("A ATR맞춤β1", pool), ("C ATR맞춤β1", pool_pass)):
                by_band = {}
                for c in pl:
                    if get(c, D, b1) is None:
                        continue
                    s_ = full.get(c)
                    di_ = _di(s_, D) if s_ else None
                    if di_ is None:
                        continue
                    av_ = atr_pct_at(s_, di_)
                    if av_ is None:
                        continue
                    by_band.setdefault(atr_band(av_), []).append(c)
                if not by_band:
                    continue
                order = ["①조용 <2.5%", "②보통 2.5~4%", "③큼 4~6%", "④매우큼 6%+"]
                rp = []
                for _ in range(N_REP):
                    vv = []
                    for bd in our_bands:
                        cd = by_band.get(bd)
                        if not cd:
                            diag["atr_band_fallback"][nm] += 1
                            if bd in order:
                                j = order.index(bd)
                                for step in (1, 2, 3):
                                    for jj in (j - step, j + step):
                                        if 0 <= jj < len(order) and by_band.get(order[jj]):
                                            cd = by_band[order[jj]]
                                            break
                                    if cd:
                                        break
                            if not cd:
                                continue
                        vv.append(net(get(cd[rnd.randrange(len(cd))], D, b1)["gain"]))
                    if vv:
                        rp.append(st.mean(vv))
                if rp:
                    day_pairs[nm][E] = our_net - st.mean(rp)

            # 우리 종목 x β1 문턱 (실행 가능한 분해)"""
assert t.count(old) == 1
t = t.replace(old, new)

t = t.replace('''"ours_beta1_no_breakout": 0,''',
              '''"ours_beta1_no_breakout": 0,
            "atr_band_fallback": defaultdict(int),''')

old2 = ('    for i, nm in enumerate(("C 우리-관문통과", "B 관문통과-미통과", "우리종목xβ1")):')
new2 = ('    for i, nm in enumerate(("C 우리-관문통과", "B 관문통과-미통과", "우리종목xβ1",\n'
        '                           "A ATR맞춤β1", "C ATR맞춤β1")):')
assert t.count(old2) == 1
t = t.replace(old2, new2)

old3 = '    print("  대조군 소멸(마지막 종가·200일 미만) %s" % dict(diag["vanished"]), flush=True)'
new3 = ('    print("  대조군 소멸(마지막 종가·200일 미만) %s" % dict(diag["vanished"]), flush=True)\n'
        '    print("  우리 종목이 β1(전일 고가)을 못 넘어 진입 못 한 건 %d / %d"\n'
        '          % (diag["ours_beta1_no_breakout"], len(ours_rows)), flush=True)\n'
        '    print("  ATR 맞춤에서 구간이 비어 인접 구간으로 물러난 횟수 %s"\n'
        '          % dict(diag["atr_band_fallback"]), flush=True)')
assert t.count(old3) == 1
t = t.replace(old3, new3)

t = t.replace('''                    "diag": {k: (dict(v) if isinstance(v, defaultdict) else v)''',
              '''                    "diag": {k: (dict(v) if isinstance(v, defaultdict) else v)''')
p.write_text(t, encoding="utf-8")
print("patched")
