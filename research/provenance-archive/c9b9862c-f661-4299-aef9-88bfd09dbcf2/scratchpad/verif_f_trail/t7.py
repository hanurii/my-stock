import json, random, statistics
from collections import defaultdict
oos=json.load(open("oos_rows2.json"))
PIL0="2025-11-26"
lead_pre=[r for r in oos if r["lead"] and r["entry"]<PIL0]
lead_pil=[r for r in oos if r["lead"] and r["entry"]>=PIL0]
lead_all=[r for r in oos if r["lead"]]
pilot=json.load(open("rows_mh60.json"))
dp=[r["tr_ret"]-r["base_ret"] for r in pilot]
obs=sum(dp)/len(dp)
print(f"파일럿 614건 관측 차이/건 = {obs:+.3f}%p")
random.seed(11)
def sampling_test(pool, lab, N=614, B=20000):
    d=[r["tr"]-r["base"] for r in pool]
    mu=sum(d)/len(d)
    hits=0; means=[]
    for _ in range(B):
        s=sum(random.choice(d) for _ in range(N))/N
        means.append(s)
        if s>=obs: hits+=1
    means.sort()
    print(f"  {lab}: 모집단 평균 {mu:+.3f}%p (n={len(d)}) → 614건 표본평균 분포 5~95% [{means[int(.05*B)]:+.2f}, {means[int(.95*B)]:+.2f}], P(표본≥{obs:+.2f}) = {hits/B*100:.1f}%")
print("\n[가설: 참값이 광의 주도주 돌파 유니버스 수준일 때, 614건에서 +1.85 가 나올 확률]")
sampling_test(lead_pre, "OOS 주도주(2021-10~2025-11)")
sampling_test(lead_pil, "파일럿창 주도주(2025-11-26~)")
sampling_test(lead_all, "주도주 전체")
sampling_test([r for r in oos if r["entry"]<PIL0], "OOS 전체 돌파")
