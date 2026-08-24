# -*- coding: utf-8 -*-
import json, glob
names = ["계양전기","남화산업","삼기에너지솔루션","원익QnC","서호전기","에이테크솔루션","시노펙스","키스트론","넥스턴앤롤콜리아","미코","해성디에스","제이티","광주신세계","알테오젠","서암기계공업","베뉴지","피에스케이홀딩스","파라리서치","에프앤가이드","엑사이엔씨","동양파일","gs리테일","아이텍","한국콜마","국순당","유니드비티플러스","아진전자부품","한국철강","송원산업","비아트론","조선내화","db하이텍","jtc","더존비즈온","휴젤","벡트","파두","금강철강","깨끗한나라우","대양금속","한주에이알티","삼진엘앤디","이오테크닉스","보해양조","비비안","부국철강"]
codemap = {}
codemap.update(json.load(open('scripts/_codes_0623sig.json',encoding='utf-8')))
codemap.update(json.load(open('scripts/_codes_user40.json',encoding='utf-8')))
pd = json.load(open(sorted(glob.glob('.cache/pdata/*.json'))[-1],encoding='utf-8'))
name2code = {r['itmsNm']: (c.zfill(6) if c.isdigit() else c) for c,r in pd.items() if r.get('itmsNm')}
def norm(s): return s.replace(' ','').lower()
n2c={norm(k):v for k,v in name2code.items()}
nm2 = {norm(k):k for k,v in name2code.items()}
resolved={}; miss=[]
for nm in names:
    if nm in codemap: resolved[nm]=codemap[nm]; continue
    if norm(nm) in n2c: resolved[nm]=n2c[norm(nm)]; continue
    cands=[(k,v) for k,v in name2code.items() if norm(nm) in norm(k) or norm(k) in norm(nm)]
    if len(cands)==1: resolved[nm]=cands[0][1]; print(f'~fuzzy {nm} -> {cands[0][0]} {cands[0][1]}'); continue
    miss.append((nm,[c[0] for c in cands[:6]]))
print(f'\nRESOLVED {len(resolved)}/{len(names)}')
print('MISSING:')
for nm,c in miss: print(f'  {nm}  후보={c}')
json.dump(resolved, open('scripts/_codes_0623day.json','w',encoding='utf-8'), ensure_ascii=False)
