# -*- coding: utf-8 -*-
import json, glob, collections
# (1) 짧은 경로의 실제 사유
short80 = []; short30 = []; early = []
for y in (2021,2022,2023,2024,2025,2026):
    d = json.load(open('.cache/bt5y/out/paths_%d.json'%y, encoding='utf-8'))
    ends = collections.Counter(p['dates'][-1] for p in d['paths'])
    modal = ends.most_common(1)[0][0]
    for p in d['paths']:
        n = len(p['c'])
        rec = (y, p['code'], p['name'], p['entry_date'], p['dates'][-1], n, p['orig_result'])
        if n < 80: short80.append(rec)
        if n < 30: short30.append(rec)
        if p['dates'][-1] != modal: early.append(rec)
    del d
print('경로 80일 미만 %d건 — 진입연도별 %s'
      % (len(short80), dict(collections.Counter(r[0] for r in short80))))
print('경로 30일 미만 %d건 — 진입연도별 %s'
      % (len(short30), dict(collections.Counter(r[0] for r in short30))))
print('연도 최빈 종료일보다 일찍 끝난 경로 %d건 — 연도별 %s'
      % (len(early), dict(collections.Counter(r[0] for r in early))))
print('  그중 80일 미만 %d건, 결과 분포 %s'
      % (sum(1 for r in early if r[5] < 80), dict(collections.Counter(r[6] for r in early))))
print('  2026년이 아닌데 80일 미만인 경로:')
for r in sorted([r for r in short80 if r[0] != 2026], key=lambda x: x[5])[:12]:
    print('    %d %s %s 진입%s → %s (%d일, %s)' % r)
print('  (2026 제외 80일 미만 총 %d건)' % len([r for r in short80 if r[0]!=2026]))

# (2) 후보 풀 9,334 검증
tot_skip = 0; tot_ev = 0
for f in sorted(glob.glob('.cache/bt5y/bt_*.json')):
    d = json.load(open(f, encoding='utf-8'))
    tot_skip += d['params']['skipped']['overlap']; tot_ev += len(d['events'])
print('\n기준선: 진입 %d + 중복차단 스킵 %d = %d' % (tot_ev, tot_skip, tot_ev + tot_skip))
for lab, pat in [('+30/-5','t30s5_*.json'), ('+20/-7','t20s7_*.json'), ('+50/-10','t50s10_*.json')]:
    s = e = 0
    for f in sorted(glob.glob('.cache/bt5y/exit/'+pat)):
        d = json.load(open(f, encoding='utf-8'))
        s += d['params']['skipped']['overlap']; e += len(d['events'])
    print('%-8s 진입 %d + 스킵 %d = %d' % (lab, e, s, e+s))
