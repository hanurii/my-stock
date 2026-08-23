# -*- coding: utf-8 -*-
import json,os,statistics as st
SP=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
rows=json.load(open(os.path.join(SP,'tradesB.json'),encoding='utf-8'))
rows.sort(key=lambda r:-r['net'])
print(f"{'순수익':>8} {'종목':<12} {'매수일':<10} {'보유':>3} {'prev':>5} {'asof':<10} {'same':>5} {'가장약한고리(prev)':<14} rs")
for r in rows:
    print(f"{r['net']:+8.2f} {r['name']:<12} {r['open_date']:<10} {r['hold']:>3} {r['score_prev']:5.1f} {r['asof_prev']:<10} {r['score_same']:5.1f} {str(r['tight_prev']):<14} {r['rs_prev']}")
print()
big_loss=['383220','122640','005950','034730','446540','131290','252990']
big_win=['007340','001540','222040','003690']
print('=== 8월 큰 손실 7건 ===')
for r in rows:
    if r['code'] in big_loss and r['net']<-8:
        print(f"  {r['name']:<10} {r['open_date']} net={r['net']:+.2f}% prev={r['score_prev']:.1f}(asof {r['asof_prev']}) same={r['score_same']:.1f} 약한고리={r['tight_prev']} allpass_prev={r['allpass_prev']}")
print('=== 큰 수익 4건 ===')
for r in rows:
    if r['code'] in big_win and r['net']>8:
        print(f"  {r['name']:<10} {r['open_date']} net={r['net']:+.2f}% prev={r['score_prev']:.1f}(asof {r['asof_prev']}) same={r['score_same']:.1f} 약한고리={r['tight_prev']} allpass_prev={r['allpass_prev']}")
bl=[r for r in rows if r['code'] in big_loss and r['net']<-8]
bw=[r for r in rows if r['code'] in big_win and r['net']>8]
print()
print('큰손실 prev 중앙값=%.1f 평균=%.1f'%(st.median([r['score_prev'] for r in bl]),st.mean([r['score_prev'] for r in bl])))
print('큰수익 prev 중앙값=%.1f 평균=%.1f'%(st.median([r['score_prev'] for r in bw]),st.mean([r['score_prev'] for r in bw])))
print('큰손실 same 중앙값=%.1f'%st.median([r['score_same'] for r in bl]))
print('큰수익 same 중앙값=%.1f'%st.median([r['score_same'] for r in bw]))
