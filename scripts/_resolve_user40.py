# -*- coding: utf-8 -*-
import json, glob, sys
names = ["일산방직","원익QnC","미래나노텍","광주신세계","한국콜마","헝셩그룹","로스웰","키스트론","조선내화","벡트","지니틱스","소룩스","파라택시스이더리움","앤디포스","동양파일","토박스코리아","알테오젠","신스틸","남화산업","해태제과식품","동우팜투테이블","동양고속","와토스코리아","비엘팜텍","시지메드텍","경남제약","금강철강","국순당","피에스케이홀딩스","부국철강","차ai헬스케어","베뉴지","모헨즈","미창석유","진흥기업우B","대한제당우","보해양조","화천기공","천일고속","엑스게이트"]

# 1) 기존 코드맵
codemap = {}
codemap.update(json.load(open('scripts/_codes_0623sig.json',encoding='utf-8')))
# 2) pdata 전종목 (name->code)
f = sorted(glob.glob('.cache/pdata/*.json'))[-1]
pd = json.load(open(f,encoding='utf-8'))
name2code = {}
for code, r in pd.items():
    nm = r.get('itmsNm')
    if nm: name2code[nm] = code.zfill(6) if code.isdigit() else code
print('pdata file:', f, 'entries:', len(name2code))

def norm(s): return s.replace(' ','').lower()
n2c_norm = {norm(k):v for k,v in name2code.items()}

resolved={}; miss=[]
for nm in names:
    if nm in codemap: resolved[nm]=codemap[nm]; continue
    if nm in name2code: resolved[nm]=name2code[nm]; continue
    if norm(nm) in n2c_norm: resolved[nm]=n2c_norm[norm(nm)]; continue
    # contains match
    cands=[(k,v) for k,v in name2code.items() if norm(nm) in norm(k) or norm(k) in norm(nm)]
    if len(cands)==1: resolved[nm]=cands[0][1]; print(f'  ~fuzzy {nm} -> {cands[0][0]} {cands[0][1]}'); continue
    miss.append((nm, cands[:5]))

print('\n=== RESOLVED', len(resolved), '/', len(names), '===')
for nm in names:
    if nm in resolved: print(f'  {resolved[nm]}  {nm}')
print('\n=== MISSING ===')
for nm,c in miss: print(f'  {nm}   cands={c}')
json.dump(resolved, open('scripts/_codes_user40.json','w',encoding='utf-8'), ensure_ascii=False)
