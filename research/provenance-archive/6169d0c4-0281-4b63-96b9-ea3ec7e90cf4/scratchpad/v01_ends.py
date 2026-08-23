# -*- coding: utf-8 -*-
import json, collections
for y in (2021, 2022, 2023, 2024, 2025, 2026):
    d = json.load(open('.cache/bt5y/out/paths_%d.json' % y, encoding='utf-8'))
    ends = collections.Counter(p['dates'][-1] for p in d['paths'])
    modal, nmodal = ends.most_common(1)[0]
    early = [(p['code'], p['name'], p['entry_date'], p['dates'][-1], len(p['c']), p['orig_result'])
             for p in d['paths'] if p['dates'][-1] != modal]
    print('%d: series_range=%s  경로 %d  최빈 종료일 %s (%d건)  다른 종료일 %d건'
          % (y, d['series_range'], len(d['paths']), modal, nmodal, len(early)))
    for e in sorted(early, key=lambda x: x[3])[:6]:
        print('    조기종료: %s %s 진입%s → %s (%d일, %s)' % e)
    # 휠라홀딩스 301일 사례
    for p in d['paths']:
        if p['code'] == '081660' and p['entry_date'] == '2023-05-11':
            print('    ★휠라홀딩스: 경로 %d일, 300일째 %s, 301일째 %s'
                  % (len(p['c']), p['dates'][299] if len(p['c']) > 299 else '-',
                     p['dates'][300] if len(p['c']) > 300 else '-'))
    del d
