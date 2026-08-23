# -*- coding: utf-8 -*-
from engine import *
base=run_rule()
print("── 사용자 실제 손익비(1.18) 재현: 조기익절 +8% × 조기손절 -6.6% ──")
for tp_,st_ in ((8.0,-6.6),(7.83,-6.64),(8.0,-10.0),(20.0,-10.0)):
    r=run_rule(tp=tp_ if tp_<20 else None, target=20.0, stop=st_)
    s=stats(r)
    rr=abs(s["avg_win"]/s["avg_loss"])
    print(f"  익절+{tp_:<5} 손절{st_:>6}: 평균 {s['avg']:>6.2f}%  승률 {s['win_rate']:>4.1f}%  평균익 {s['avg_win']:>5.2f} 평균손 {s['avg_loss']:>6.2f}  실현손익비 {rr:.2f}  총합 {s['sum']:>7.1f}%p  평균 {s['avg_days']:.1f}일")
print()
print("── 총액 관점 (슬롯 1,000만원 가정, 614거래 누적 %p) ──")
for lbl,kw in (("현행 +20/-10",{}),("조기익절 +8%",{"tp":8.0}),("조기익절 +10%",{"tp":10.0}),
               ("조기익절 +8% + 최소보유 5일",{"tp":8.0,"min_hold":5}),
               ("조기익절 +8% + 최소보유 10일",{"tp":8.0,"min_hold":10})):
    s=stats(run_rule(**kw))
    print(f"  {lbl:<28} 총 {s['sum']:>7.1f}%p   거래당 {s['avg']:>6.2f}%  (1,000만 슬롯 환산 거래당 {s['avg']*10:>6.1f}만원, 누적 {s['sum']*10/100:>6.0f}만원)")
print()
print("── '+20% 목표를 지켰다면' 사용자 21승 근사 검증: 승자만의 평균이익 ──")
b=stats(base); print("  현행 승자 평균이익", b["avg_win"], "% / 사용자 실제", 7.83, "%")
