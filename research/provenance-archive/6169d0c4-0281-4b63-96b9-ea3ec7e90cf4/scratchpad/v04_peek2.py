import json, glob
f = sorted(glob.glob(r'.cache\bt5y\out\_04_score_cache\scores_*.json'))
d = json.load(open(f[0], encoding='utf-8'))
print("최상위 키:", list(d))
for k in d:
    v = d[k]
    print(" ", k, type(v).__name__, len(v) if hasattr(v, '__len__') else v)
body = d[[k for k in d if isinstance(d[k], (list, dict)) and k != 'year'][0]]
if isinstance(body, dict):
    kk = list(body)[0]
    print("본문 키 예:", kk, "→", json.dumps(body[kk], ensure_ascii=False)[:400])
else:
    print("본문 원소 예:", json.dumps(body[0], ensure_ascii=False)[:400])
