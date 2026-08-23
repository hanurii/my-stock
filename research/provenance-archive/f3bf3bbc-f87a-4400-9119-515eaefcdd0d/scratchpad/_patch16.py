# -*- coding: utf-8 -*-
import pathlib

p = pathlib.Path("research/handoff/scripts/16-selection-edge.py")
t = p.read_text(encoding="utf-8")
NL = chr(92) + "n"

old = """            for arm in ARMS:
                if arm == "alpha":
                    cand = pool
                else:
                    cand = [c for c in pool if get(c, D, arm) is not None]"""
new = """            # C·B 용 풀 (β1 진입으로 통일)
            b1 = ("beta", 1)
            pool_pass = [c for c in pool if c in passed]
            pool_fail = [c for c in pool if c not in passed]
            for nm, pl in (("C:관문통과β1", pool_pass), ("B:관문미통과β1", pool_fail)):
                cd = [c for c in pl if get(c, D, b1) is not None]
                if len(cd) < k:
                    diag["beta_pool_short"][nm] += 1
                    diag["beta_trades_short"][nm] += k - len(cd)
                if not cd:
                    continue
                rp = []
                for _ in range(N_REP):
                    pick = (rnd.sample(cd, k) if len(cd) >= k
                            else [cd[rnd.randrange(len(cd))] for _ in range(k)])
                    rp.append(st.mean([net(get(c, D, b1)["gain"]) for c in pick]))
                lvl[nm][E] = st.mean(rp)
            if E in lvl["C:관문통과β1"]:
                day_pairs["C 우리-관문통과"][E] = our_net - lvl["C:관문통과β1"][E]
                if E in lvl["B:관문미통과β1"]:
                    day_pairs["B 관문통과-미통과"][E] = (lvl["C:관문통과β1"][E]
                                                  - lvl["B:관문미통과β1"][E])
            # 우리 종목 x β1 문턱 (실행 가능한 분해)
            ov = []
            for e in ours:
                r = get(e["code"], D, b1)
                if r is None:
                    diag["ours_beta1_no_breakout"] += 1
                else:
                    ov.append(net(r["gain"]))
            if ov:
                day_pairs["우리종목xβ1"][E] = our_net - st.mean(ov)

            for arm in ARMS:
                if arm == "alpha":
                    cand = pool
                else:
                    cand = [c for c in pool if get(c, D, arm) is not None]"""
assert t.count(old) == 1
t = t.replace(old, new)

old2 = """                if reps:
                    ctrl = st.mean(reps)
                    day_pairs[ARMN[arm]][E] = our_net - ctrl
                    absol[ARMN[arm]].append(ctrl)"""
new2 = """                if reps:
                    ctrl = st.mean(reps)
                    day_pairs[ARMN[arm]][E] = our_net - ctrl
                    absol[ARMN[arm]].append(ctrl)
                # 분포 표본 — 첫 복제 한 벌만(우리와 같은 규모의 n 을 만든다)
                if arm == "alpha" or arm == ("beta", 1):
                    pk = (rnd.sample(cand, k) if len(cand) >= k else list(cand[:k]))
                    for c in pk:
                        s = full.get(c)
                        di = _di(s, D) if s else None
                        if di is not None:
                            av = atr_pct_at(s, di)
                            if av is not None:
                                atr_dist[ARMN[arm]].append(av)
                        cp = cap_at.get(D, {}).get(c)
                        if cp:
                            cap_dist[ARMN[arm]].append(cp)"""
assert t.count(old2) == 1
t = t.replace(old2, new2)

t = t.replace('''    diag = {"days_pool_eq_k": 0, "trades_pool_eq_k": 0,''',
              '''    lvl = defaultdict(dict)
    diag = {"days_pool_eq_k": 0, "trades_pool_eq_k": 0, "ours_beta1_no_breakout": 0,''')

old3 = """    need_be = STOP / (TARGET + STOP) * 100"""
new3 = """    # ★ 필요 본전 승률은 **비용 반영 순수익**으로 계산한다.
    #   33.33%(=10/(20+10))는 수수료·세금을 무시한 값이라 여유를 과대평가한다.
    w_net = st.mean([r["net"] for r in ours_rows if r["net"] > 0])
    l_net = st.mean([r["net"] for r in ours_rows if r["net"] <= 0])
    need_be = (-l_net) / (w_net - l_net) * 100
    need_be_naive = STOP / (TARGET + STOP) * 100"""
assert t.count(old3) == 1
t = t.replace(old3, new3)
t = t.replace('''        "required_win_rate": need_be,''',
              '''        "required_win_rate": need_be, "required_naive": need_be_naive,
        "mean_win_net": w_net, "mean_loss_net": l_net,''')

old_pr = '''    print("  n %d · 승률 %.2f%% · 순수익>0 %.2f%% · 필요 본전 %.2f%% · **여유 %+.2f%%p** · "
          "거래당 %+.4f%%p · 중앙 %+.4f"
          % (a["n"], a["win_rate"], a["breakeven_rate"], a["required_win_rate"],
             a["margin"], a["per_trade"], a["median"]), flush=True)'''
new_pr = '''    print("  n %d · 승률 %.2f%% · 순수익>0 %.2f%%"
          % (a["n"], a["win_rate"], a["breakeven_rate"]), flush=True)
    print("  이긴 거래 평균 %+.3f%%p · 진 거래 평균 %+.3f%%p → **필요 본전 승률 %.2f%%** "
          "(비용 무시하면 %.2f%%)" % (w_net, l_net, need_be, need_be_naive), flush=True)
    print("  → **여유 %+.2f%%p** · 거래당 %+.4f%%p · 중앙 %+.4f"
          % (a["margin"], a["per_trade"], a["median"]), flush=True)'''
assert t.count(old_pr) == 1
t = t.replace(old_pr, new_pr)

old4 = '    print("' + NL + '═══ 우리 거래 절대 성적'
new4 = ('    print("' + NL + '═══ B · C · 부가 팔 (전부 β1 진입으로 통일) ═══", flush=True)\n'
        '    res["BC"] = {}\n'
        '    for i, nm in enumerate(("C 우리-관문통과", "B 관문통과-미통과", "우리종목xβ1")):\n'
        '        if day_pairs.get(nm):\n'
        '            res["BC"][nm] = day_stat(day_pairs[nm], dates_all, nm, BOOT_SEED + 50 + i)\n'
        '    if "C 우리-관문통과" in res["BC"] and "B 관문통과-미통과" in res["BC"]:\n'
        '        p_gate = 172764 / 2109931\n'
        '        cb = res["BC"]["C 우리-관문통과"]["mean"]\n'
        '        bb = res["BC"]["B 관문통과-미통과"]["mean"]\n'
        '        ab = res["A"].get("β1일고가", {}).get("mean")\n'
        '        rhs = cb + (1 - p_gate) * bb\n'
        '        res["identity_check"] = {"p_gate": p_gate, "C": cb, "B": bb,\n'
        '                                 "A_beta1": ab, "C_plus_(1-p)B": rhs,\n'
        '                                 "residual": (ab - rhs) if ab is not None else None}\n'
        '        print("' + NL + '  [검산] A_β1 %+.4f  vs  C %+.4f + (1-%.4f)xB %+.4f = %+.4f · 잔차 %+.4f"\n'
        '              % (ab, cb, p_gate, bb, rhs, ab - rhs), flush=True)\n'
        '        print("  ※ 이 점검은 **검산이며 불일치는 판정 사유가 아니다** — 세 비교의 "\n'
        '              "표본이 다르므로 잔차는 오류가 아니라 상호작용이다(검증 [5]).", flush=True)\n'
        '\n'
        '    print("' + NL + '═══ 우리 거래 절대 성적')
assert t.count(old4) == 1, t.count(old4)
t = t.replace(old4, new4)

old5 = '    if cap_dist["ours"]:'
new5 = ('    for nm in ("α시가", "β1일고가"):\n'
        '        v = [x for x in atr_dist[nm] if x is not None]\n'
        '        if v:\n'
        '            res["atr"][nm] = {"median": st.median(v), "n": len(v),\n'
        '                              "bands": {b: sum(1 for x in v if atr_band(x) == b)\n'
        '                                        / len(v) * 100\n'
        '                                        for b in ("①조용 <2.5%", "②보통 2.5~4%",\n'
        '                                                  "③큼 4~6%", "④매우큼 6%+")}}\n'
        '            print("  %-8s ATR 중앙 %.2f%% (n=%d) · 구간 %s"\n'
        '                  % (nm, st.median(v), len(v),\n'
        '                     {k: round(x, 1) for k, x in res["atr"][nm]["bands"].items()}),\n'
        '                  flush=True)\n'
        '\n'
        '    if cap_dist["ours"]:')
assert t.count(old5) == 1
t = t.replace(old5, new5)

old6 = '        print("' + NL + '  우리 시점 시총 중앙 %.0f억 (n=%d)" % (st.median(co), len(co)), flush=True)'
new6 = ('        print("' + NL + '═══ 시점 시총 분포 (검증 [3] · 문턱 사전 등록) ═══", flush=True)\n'
        '        cut = sorted(co)[int(len(co) * 2 / 3)]\n'
        '        print("  우리 중앙 %.0f억 (n=%d) · 상위3분위 경계 %.0f억"\n'
        '              % (st.median(co), len(co), cut), flush=True)\n'
        '        for nm in ("α시가", "β1일고가"):\n'
        '            v = cap_dist.get(nm)\n'
        '            if not v:\n'
        '                continue\n'
        '            ratio = st.median(co) / st.median(v)\n'
        '            top_o = sum(1 for x in co if x >= cut) / len(co) * 100\n'
        '            top_c = sum(1 for x in v if x >= cut) / len(v) * 100\n'
        '            trip = ratio > 2 or ratio < 0.5 or abs(top_o - top_c) > 20\n'
        '            res.setdefault("cap_cmp", {})[nm] = {\n'
        '                "ctrl_median": st.median(v), "ratio": ratio,\n'
        '                "top_tercile_ours": top_o, "top_tercile_ctrl": top_c,\n'
        '                "triggers_matched_arm": bool(trip)}\n'
        '            print("  %-8s 중앙 %.0f억 · 비율 %.2f배 · 상위3분위 우리 %.1f%% vs 대조 "\n'
        '                  "%.1f%% → 맞춤 대조 문턱 %s"\n'
        '                  % (nm, st.median(v), ratio, top_o, top_c,\n'
        '                     "**넘음(돌려야 함)**" if trip else "안 넘음(안 돌림)"), flush=True)')
assert t.count(old6) == 1
t = t.replace(old6, new6)

p.write_text(t, encoding="utf-8")
print("patched")
