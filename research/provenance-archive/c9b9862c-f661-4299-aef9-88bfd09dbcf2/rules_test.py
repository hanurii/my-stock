# -*- coding: utf-8 -*-
import sim_core as SC, statistics as st, json
from canslim_lib import sell_rules as SR
from canslim_lib.pivot_backtest import truncate_series
SC.HORIZON=60
STATE={}
def fast_avg(volumes,i,window=50,min_days=5):
    pref,cnt=STATE["pref"],STATE["cnt"]
    lo=max(0,i-window)
    s=pref[i]-pref[lo]; c=cnt[i]-cnt[lo]
    if c<min_days: return None
    return s/c
SR.avg_volume=fast_avg

def prep_state(s):
    v=s["volumes"]; pref=[0.0]*(len(v)+1); cnt=[0]*(len(v)+1)
    for i,x in enumerate(v):
        ok = x is not None and x>0
        pref[i+1]=pref[i]+(x if ok else 0.0); cnt[i+1]=cnt[i]+(1 if ok else 0)
    STATE["pref"]=pref; STATE["cnt"]=cnt

RULES=["heavy_volume_pullback","consecutive_lower_lows","close_below_ma","weak_days_dominant","breakout_failure"]

def eval_day(st_, bi, pivot):
    out={}
    out["heavy_volume_pullback"]=SR.rule_heavy_volume_pullback(st_,bi)["status"]
    out["consecutive_lower_lows"]=SR.rule_consecutive_lower_lows(st_,bi)["status"]
    out["close_below_ma"]=SR.rule_close_below_ma(st_,bi)["status"]
    out["weak_days_dominant"]=SR.rule_weak_days_dominant(st_,bi)["status"]
    out["breakout_failure"]=SR.rule_breakout_failure(st_,bi,pivot,breakout_confirmed=True,start=bi)["status"]
    return out
