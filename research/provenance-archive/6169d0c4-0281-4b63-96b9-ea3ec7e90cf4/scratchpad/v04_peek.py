import json, glob, os
f = sorted(glob.glob(r'.cache\bt5y\out\_04_score_cache\scores_*.json'))
print("파일 %d개" % len(f))
d = json.load(open(f[0], encoding='utf-8'))
print("타입:", type(d).__name__, "길이", len(d))
if isinstance(d, dict):
    k = list(d)[0]
    print("키 예:", k)
    print("값 예:", json.dumps(d[k], ensure_ascii=False)[:400])
else:
    print("원소 예:", json.dumps(d[0], ensure_ascii=False)[:400])
