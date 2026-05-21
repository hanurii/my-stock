"""2단계 손절 전환점 캘리브레이션 — 종가 기준·인과(미래 비참조).

사용자 수렴 규칙: 매수 직후 −8% = 잘못 진입 → 즉시 매도(초기 하드손절).
일단 의미있게 오르면 한국 변동성 감안 고점 대비 ~20% 흔들림 견디고 보유.
→ 비워둔 칸 = '언제 −8%를 풀어 트레일링으로 승격하나' 를 실측 캘리브.

인과 진입(단일): 사이클저점 이후 *첫 종가>20일이동평균* 일(미래 비참조).
정책(전환점만 다름):
  ONEIL    −8% 상시 + +20%매도(≤15거래일 빠른상승→40거래일 보유)  [참조]
  WIDE0    초기없이 처음부터 재해−15% + 트레일링(고점−20%)            [참조]
  2S@+15   초기 −8% → 수익 +15% 도달 시 트레일링(고점−20%)로 승격
  2S@+20   〃 +20%
  2S@+25   〃 +25%
  2S@8주   초기 −8% → 40거래일 생존 시 트레일링 승격(시간 기준)
지표(NON/MID/WIN): 평균·중앙 실현, 승률, 초기−8%로 잘린 비율, 그중
*나중에 크게 갈(+100%↑) 종목* 비율=−8%의 비용, *진짜 불량(+20%↑ 못 감)*
비율=이득, 포착중앙, 최악거래. (위너여부는 평가 진단용으로만, 규칙은 인과.)

시세(Yahoo 종가)만·저관리. 사이클내 사후·인-샘플·상폐제외·비용 미반영.
환각 금지.  사용: python analyze_stop2stage.py [--n 60] [--seed 7]
"""
import argparse
import bisect
import json
import random
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cyclecfg  # noqa: E402
from canslim_lib.fetch import yahoo_symbol  # noqa: E402

CY = cyclecfg.DIR
FAST, W8 = 15, 40


def nidx(d, ds):
    i = bisect.bisect_right(d, ds) - 1
    return i if i >= 0 else None


def ma(c, x, w):
    return sum(c[x - w + 1:x + 1]) / w if x >= w - 1 else None


def causal_entry(c, ti, n):
    """사이클저점 이후 첫 '종가 > 20일이동평균' (과거 20봉만 사용=인과)."""
    for x in range(max(ti, 20), n - 5):
        m = ma(c, x, 20)
        if m and c[x] > m:
            return x
    return None


def run(c, e, n, policy):
    """단일매매 → (실현수익, 종료태그). 종가 기준 인과."""
    end = n - 1
    peak = c[e]
    promoted = (policy == "WIDE0")
    for k in range(e + 1, end + 1):
        if c[k] > peak:
            peak = c[k]
        g = c[k] / c[e] - 1
        if policy == "ONEIL":
            if c[k] <= c[e] * 0.92:
                return g, "init8"
            if g >= 0.20:
                return (c[k] / c[e] - 1, "tp20") if (k - e) > FAST \
                    else (c[min(end, e + W8)] / c[e] - 1, "hold8w")
            continue
        if policy == "WIDE0":
            if c[k] <= c[e] * 0.85:
                return g, "dis15"
            if c[k] <= peak * 0.80:
                return g, "trail"
            continue
        # 2단계: 미승격 = 초기 −8%, 승격 조건 충족 시 트레일링
        if not promoted:
            if c[k] <= c[e] * 0.92:
                return g, "init8"
            if policy == "2S@8주":
                if k - e >= W8:
                    promoted = True
            else:
                thr = {"2S@+15": 0.15, "2S@+20": 0.20, "2S@+25": 0.25}[policy]
                if g >= thr:
                    promoted = True
        if promoted:
            if c[k] <= peak * 0.80:
                return g, "trail"
    return c[end] / c[e] - 1, "end"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    wf = json.loads((CY / "winners_final.json").read_text(encoding="utf-8"))
    winners = wf["winners"]
    wc = {x["code"] for x in winners}
    rv = json.loads((CY / "winners.json").read_text(encoding="utf-8"))["ranked_valid"]

    def ok(r):
        return (not r.get("exclude_reason") and r.get("trough_date")
                and r.get("n_days", 0) >= 60 and r.get("raw_multiple"))
    rest = [r for r in rv if r["code"] not in wc and ok(r)]
    NON = [r for r in rest if r["raw_multiple"] < 1.5]
    MID = [r for r in rest if 1.5 <= r["raw_multiple"] < 3.0]
    random.seed(args.seed)
    tiers = {"NON 안오름": random.sample(NON, min(args.n, len(NON))),
             "MID 중간": random.sample(MID, min(args.n, len(MID))),
             "WIN 위너": random.sample(winners, min(args.n, len(winners)))}
    POLS = ["ONEIL", "WIDE0", "2S@+15", "2S@+20", "2S@+25", "2S@8주"]

    out = [f"[c2024-12] 2단계 손절 전환점 캘리브 — 단계별 {args.n}종목 "
           f"(seed {args.seed})",
           "인과 진입=사이클저점 후 첫 종가>20일선(미래 비참조)·1매매·종가 기준.",
           "초기−8% 잘림의 비용=그중 이후 +100%↑ 갈 종목 비율 / 이득=이후",
           "+20%도 못 간 진짜 불량 비율. (위너판정은 진단용, 규칙은 인과.)",
           ""]
    for tag, lst in tiers.items():
        ser = []
        for w in lst:
            ch = cyclecfg.yahoo(yahoo_symbol(w["code"], w["market"]))
            if not ch or not ch.get("closes"):
                continue
            ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
                  for t in ch["timestamps"]]
            c = ch["closes"]
            ti = nidx(ts, w["trough_date"]) or 0
            e = causal_entry(c, ti, len(c))
            if e is None:
                continue
            emax = max(c[e:]) / c[e] - 1
            ser.append((c, e, len(c), emax))
        out.append(f"== {tag} (종목 {len(ser)}) ==")
        out.append("정책 | 평균실현% | 중앙% | 승률 | 초기-8%잘림 | "
                   "잘린것중 미래위너 | 잘린것중 진짜불량 | 포착중앙 | 최악%")
        for p in POLS:
            rr, tags, caps = [], [], []
            for c, e, n, emax in ser:
                g, tg = run(c, e, n, p)
                rr.append(g * 100)
                tags.append((tg, emax))
                caps.append((g / emax) if emax > 1e-9 else (1.0 if g >= 0 else 0.0))
            m = len(rr)
            cut = [em for tg, em in tags if tg == "init8"]
            ncut = len(cut)
            fut = sum(1 for em in cut if em >= 1.0)        # 잘렸지만 +100%↑ 갈
            bad = sum(1 for em in cut if em < 0.20)        # 잘려도 +20%도 못 감
            out.append(
                f"{p:8s} | {round(st.mean(rr),1)}% | {round(st.median(rr),1)}% | "
                f"{round(100*sum(1 for v in rr if v>0)/m)}% | "
                f"{round(100*ncut/m)}% | "
                f"{(str(round(100*fut/ncut))+'%') if ncut else '-'} | "
                f"{(str(round(100*bad/ncut))+'%') if ncut else '-'} | "
                f"{round(st.median(caps),2)} | {round(min(rr),1)}%")
        be = sum(1 for _, _, _, em in ser if em >= 1.0)
        out.append(f"  (참고: 이 그룹 진입의 {round(100*be/len(ser)) if ser else 0}%"
                   f"가 이후 +100%↑ 종목 — 비용 해석 맥락)")
        out.append("")
    out += ["== 해석(쉽게) ==",
            "평균·중앙 실현↑·포착↑·최악 견딜만하면 좋은 전환점. 초기−8%",
            "잘림 중 '미래위너' 비율 높으면 −8%가 큰 종목을 죽이는 비용 큼",
            "→ 전환점을 낮춰 빨리 풀어주는 게 유리. '진짜불량' 비율 높으면",
            "−8% 필터가 제 역할(불량 거름). WIDE0(초기 타이트 없음)와 비교해",
            "초기 −8%가 실익 있는지 판단.",
            "== 한계 ==",
            "사이클내 사후·인-샘플·상폐제외·표본무작위·세금/비용 미반영·",
            "단일 인과진입(검증 5신호 아님)·종가만. 방향 참고용."]
    fn = f"_stop2stage_n{args.n}s{args.seed}.txt"
    (CY / fn).write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fn}", file=sys.stderr)


if __name__ == "__main__":
    main()
