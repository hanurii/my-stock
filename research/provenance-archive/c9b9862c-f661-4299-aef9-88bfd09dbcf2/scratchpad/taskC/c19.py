import json,os,collections,math,sys
sys.path.insert(0,'scripts')
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
H=[r for r in rows if r.get('h10')]
print('10일창 표본 기간:',min(r['date'] for r in H),'~',max(r['date'] for r in H))
L=[r for r in rows if r['outcome']]
print('원장 표본 기간:',min(r['date'] for r in L),'~',max(r['date'] for r in L))
print('행/종목:',len(L),len({r['code'] for r in L}),'평균 반복',round(len(L)/len({r['code'] for r in L}),1))
# 다중비교 참고
print('tightest 코호트 종목수', {k:len({r['code'] for r in H if r['tightest']==k}) for k in '12345678'})
