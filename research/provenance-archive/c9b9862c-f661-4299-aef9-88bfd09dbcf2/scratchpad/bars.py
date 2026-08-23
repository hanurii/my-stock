import sys
sys.path.insert(0,'C:/Users/hanul/playground/my-stock/scripts')
from canslim_lib import ohlcv_matrix
for c,n in [('003550','LG'),('159010','아스플로'),('161390','한국타이어'),('010950','S-Oil'),('009420','한올'),('034730','SK'),('053260','금강철강'),('076610','해성옵틱스'),('094840','슈프리마'),('071200','인피니트'),('121440','골프존')]:
    s=ohlcv_matrix.get_series(c)
    print(f"== {c} {n}")
    for i in range(len(s['dates'])-10,len(s['dates'])):
        print(f"   {s['dates'][i]} O{s['opens'][i]:>12} H{s['highs'][i]:>12} L{s['lows'][i]:>12} C{s['closes'][i]:>12} V{s['volumes'][i]:>12}")
