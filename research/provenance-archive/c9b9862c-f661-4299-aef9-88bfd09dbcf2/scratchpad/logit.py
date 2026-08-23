# -*- coding: utf-8 -*-
"""IRLS 로지스틱 + 종목 클러스터 강건 표준오차."""
import numpy as np
from scipy import stats

def fit_logit(X, y, maxit=200, tol=1e-10, ridge=1e-6):
    n,k = X.shape
    b=np.zeros(k)
    for _ in range(maxit):
        eta=X@b; p=1/(1+np.exp(-np.clip(eta,-30,30)))
        W=np.maximum(p*(1-p),1e-9)
        H=X.T@(X*W[:,None]) + ridge*np.eye(k)
        g=X.T@(y-p) - ridge*b
        step=np.linalg.solve(H,g)
        b=b+step
        if np.max(np.abs(step))<tol: break
    eta=X@b; p=1/(1+np.exp(-np.clip(eta,-30,30)))
    W=np.maximum(p*(1-p),1e-9)
    H=X.T@(X*W[:,None]) + ridge*np.eye(k)
    Hinv=np.linalg.inv(H)
    return b,p,Hinv

def cluster_se(X,y,p,Hinv,clusters):
    u=(y-p)[:,None]*X
    meat=np.zeros((X.shape[1],X.shape[1]))
    for c in np.unique(clusters):
        s=u[clusters==c].sum(0)
        meat+=np.outer(s,s)
    G=len(np.unique(clusters)); n=len(y); k=X.shape[1]
    adj=(G/(G-1))*((n-1)/(n-k))
    V=Hinv@meat@Hinv*adj
    return np.sqrt(np.diag(V))

def report(names,b,se,title):
    print(f"\n### {title}")
    print(f"{'변수':<22}{'계수':>9}{'표준오차':>10}{'z':>7}{'p':>9}   {'오즈비 95%CI':>22}")
    for nm,bb,ss in zip(names,b,se):
        z=bb/ss; p=2*(1-stats.norm.cdf(abs(z)))
        lo,hi=np.exp(bb-1.96*ss),np.exp(bb+1.96*ss)
        print(f"{nm:<22}{bb:+9.3f}{ss:10.3f}{z:+7.2f}{p:9.3f}   {np.exp(bb):6.2f} [{lo:5.2f}, {hi:5.2f}]")
