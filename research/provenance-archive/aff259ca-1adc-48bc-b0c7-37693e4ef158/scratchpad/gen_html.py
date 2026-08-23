# -*- coding: utf-8 -*-
"""TASK 4: earnings-classify.html — dark single-theme artifact page."""
import json
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

SCRATCH = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"

with open(os.path.join(SCRATCH, "ec_final_v2.json"), encoding="utf-8") as f:
    final = json.load(f)
rows = final["rows"]

ORDER = ["쇼크", "부진(YoY)", "서프라이즈", "호실적(YoY)", "부합", "무난(YoY)"]
POS = {"서프라이즈", "호실적(YoY)"}
NEG = {"쇼크", "부진(YoY)"}
PILL = {"서프라이즈": "g", "호실적(YoY)": "g", "부합": "y", "무난(YoY)": "y",
        "쇼크": "r", "부진(YoY)": "r"}


def sort_key(r):
    cls = r["classification"]
    v = r["beat_pct"] if r["beat_pct"] is not None else (r["yoy_pct"] if r["yoy_pct"] is not None else 0)
    gi = ORDER.index(cls)
    if cls in NEG:
        return (gi, v)
    return (gi, -v)


rows_sorted = sorted(rows, key=sort_key)


def md(d):
    return f"{int(d[5:7])}/{int(d[8:10])}" if d else "?"


def fmt_basis(r):
    if r["method"] == "consensus":
        return f"beat {r['beat_pct']:+.1f}%"
    if r["yoy_case"] and r["yoy_case"] != "yoy":
        return f"YoY {r['yoy_case']}"
    if r["yoy_pct"] is not None:
        return f"YoY {r['yoy_pct']:+.1f}%"
    return "—"


def fmt_op(r):
    v = r["q2_op_actual_eok"]
    return f"{v:,.0f}" if v is not None else "—"


cls_dist = Counter(r["classification"] for r in rows)
timing_dist = Counter(r["timing"]["timing_class"] for r in rows)
kind_timing = defaultdict(Counter)
cross = defaultdict(Counter)
for r in rows:
    kind_timing[r["reaction"]["reveal_kind"]][r["timing"]["timing_class"]] += 1
    cross[r["classification"]][r["timing"]["timing_class"]] += 1
dir_obs = [r for r in rows if r["timing"]["observable_v2"] and r["classification"] in POS | NEG]
dir_c = Counter(r["concord_v2"] for r in dir_obs)
n_814 = sum(1 for r in rows if r["reaction"]["reveal_date"] == "2026-08-14")
n_814_obs = sum(1 for r in rows if r["reaction"]["reveal_date"] == "2026-08-14" and r["timing"]["observable_v2"])
obs_v2 = sum(1 for r in rows if r["timing"]["observable_v2"])
intraday = timing_dist["장전"] + timing_dist["장중"]

H = []
H.append("<title>실적 분류 92</title>")
H.append("""<style>
  :root{
    --bg:#0f131b; --surface:#171c26; --text:#e3e8f2; --muted:#a8b5d0;
    --green:#34d399; --gold:#e9c176; --red:#ffb4ab;
    --pill-g:rgba(52,211,153,.13); --pill-y:rgba(233,193,118,.13); --pill-r:rgba(255,180,171,.13);
    --line:rgba(168,181,208,.14);
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);
    font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif;
    line-height:1.6;padding:40px 20px 64px}
  main{max-width:960px;margin:0 auto}
  h1{font-size:1.7rem;font-weight:700;letter-spacing:-.01em;text-wrap:balance}
  h2{font-size:1.12rem;font-weight:700;margin:40px 0 14px;letter-spacing:-.005em}
  .sub{color:var(--muted);font-size:.9rem;margin-top:6px}
  .num{font-variant-numeric:tabular-nums}
  /* 결론 */
  .lede{background:var(--surface);border:1px solid var(--line);border-radius:10px;
    padding:18px 22px;margin-top:22px}
  .lede ul{list-style:none;display:flex;flex-direction:column;gap:9px}
  .lede li{padding-left:1.05em;position:relative;font-size:.94rem}
  .lede li::before{content:"—";position:absolute;left:0;color:var(--muted)}
  .lede b{color:var(--green);font-weight:700}
  /* 요약 카드 */
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
  .card{background:var(--surface);border:1px solid var(--line);border-radius:10px;
    padding:14px 16px;display:flex;flex-direction:column;gap:2px}
  .card .k{font-size:.78rem;letter-spacing:.02em;color:var(--muted)}
  .card .v{font-size:1.65rem;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.2}
  .card.g .v{color:var(--green)} .card.y .v{color:var(--gold)} .card.r .v{color:var(--red)}
  /* 테이블 공통 */
  .tw{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}
  table{border-collapse:collapse;width:100%;font-size:.885rem}
  th{color:var(--muted);font-weight:600;font-size:.795rem;letter-spacing:.03em;
    text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
  td{padding:8px 12px;border-bottom:1px solid var(--line);white-space:nowrap;vertical-align:middle}
  tr:last-child td{border-bottom:none}
  td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
  td.c,th.c{text-align:center}
  .mut{color:var(--muted)}
  .up{color:var(--green)} .dn{color:var(--red)}
  tfoot td,td.tot{color:var(--text);font-weight:700}
  /* 분류 pill */
  .pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.78rem;font-weight:600}
  .pill.g{background:var(--pill-g);color:var(--green)}
  .pill.y{background:var(--pill-y);color:var(--gold)}
  .pill.r{background:var(--pill-r);color:var(--red)}
  .chk{font-weight:700}
  .chk.ok{color:var(--green)} .chk.bad{color:var(--red)} .chk.na{color:var(--muted)}
  footer{color:var(--muted);font-size:.8rem;margin-top:28px;line-height:1.7}
</style>""")
H.append("<main>")
H.append('<h1>실적 분류 92종목 — 발표시각 반영 v2</h1>')
H.append('<p class="sub">2026-08-17 · 2분기 실적 캘린더 92종목 · 발표시각 출처 KIND 공시시각(92/92 확보)</p>')

# 결론
H.append('<section class="lede"><ul>')
H.append(f'<li>발표시각 <b>92/92 전수 확보</b>(KIND 상장공시시스템). 시각미상 0건.</li>')
H.append(f'<li>발표시점: 장전 {timing_dist["장전"]} · 장중 {timing_dist["장중"]} · 장후 {timing_dist["장후"]} — <b>{intraday}건({100*intraday/len(rows):.0f}%)이 장전·장중 발표</b>. 반응은 "다음날"이 아니라 <b>당일</b>에 봐야 맞는 종목이 다수.</li>')
H.append(f'<li>반응일 재배정 {intraday}건(다음날→당일). 8/14 공시 {n_814}건 중 <b>{n_814_obs}건이 당일 데이터로 관측 가능</b>해졌고, 장후 발표 {n_814-n_814_obs}건만 8/18 대기.</li>')
H.append(f'<li>관측 {obs_v2}/92. 방향성 분류(서프라이즈·호실적·쇼크·부진) 관측 {len(dir_obs)}건의 정합: <b>✓ {dir_c["✓"]}</b> · ✗ {dir_c["✗"]} · ±8% 미만 {dir_c["·"]} — ±8% 이상 움직였을 때 정합이 역행의 8배.</li>')
H.append(f'<li>잠정·반기 모두 장중 발표 최다(잠정 {kind_timing["잠정"]["장중"]}/{sum(kind_timing["잠정"].values())} · 반기 {kind_timing["반기보고서"]["장중"]}/{sum(kind_timing["반기보고서"].values())}). "실적은 장 마감 후"라는 통념과 달리 <b>3분의 2가 장전·장중 공개</b>.</li>')
H.append('</ul></section>')

# 분포 카드
H.append('<h2>분류 분포</h2>')
H.append('<div class="cards">')
for c in ORDER:
    H.append(f'<div class="card {PILL[c]}"><span class="k">{c}</span><span class="v">{cls_dist[c]}</span></div>')
H.append('</div>')

# 발표시점 분포
H.append('<h2>발표시점 분포 <span class="mut" style="font-weight:400;font-size:.85rem">장전 &lt;09:00 · 장중 09:00~15:30 · 장후 &gt;15:30</span></h2>')
H.append('<div class="tw"><table>')
H.append('<thead><tr><th>종류</th><th class="n">장전</th><th class="n">장중</th><th class="n">장후</th><th class="n">시각미상</th><th class="n">계</th></tr></thead><tbody>')
for k in ["잠정", "반기보고서"]:
    c = kind_timing[k]
    H.append(f'<tr><td>{k}</td><td class="n">{c["장전"]}</td><td class="n">{c["장중"]}</td><td class="n">{c["장후"]}</td><td class="n">{c["시각미상"]}</td><td class="n">{sum(c.values())}</td></tr>')
H.append(f'<tr><td class="tot">계</td><td class="n tot">{timing_dist["장전"]}</td><td class="n tot">{timing_dist["장중"]}</td><td class="n tot">{timing_dist["장후"]}</td><td class="n tot">{timing_dist["시각미상"]}</td><td class="n tot">{len(rows)}</td></tr>')
H.append('</tbody></table></div>')

# 교차표
H.append('<h2>분류 × 발표시점</h2>')
H.append('<div class="tw"><table>')
H.append('<thead><tr><th>분류</th><th class="n">장전</th><th class="n">장중</th><th class="n">장후</th><th class="n">계</th></tr></thead><tbody>')
for c in ORDER:
    cc = cross[c]
    H.append(f'<tr><td><span class="pill {PILL[c]}">{c}</span></td><td class="n">{cc["장전"]}</td><td class="n">{cc["장중"]}</td><td class="n">{cc["장후"]}</td><td class="n">{sum(cc.values())}</td></tr>')
H.append('</tbody></table></div>')

# 전체 테이블
H.append('<h2>전체 92종목</h2>')
H.append('<p class="mut" style="font-size:.84rem;margin:-6px 0 12px">반응 = 장전/장중 발표는 공시 당일, 장후 발표는 다음 거래일의 등락률·상대거래량(직전 50일 평균 대비). '
         '정합: 방향성 분류는 ±8% 이상 같은 방향 ✓ / 반대 ✗ / 미만 · — 부합·무난은 ±8% 미만이면 ✓. 미관측 —.</p>')
H.append('<div class="tw"><table>')
H.append('<thead><tr><th>종목(코드)</th><th>분류</th><th class="n">근거</th><th class="n">Q2 영업이익(억)</th><th>발표일·시점</th><th>반응</th><th class="c">정합</th></tr></thead><tbody>')
for r in rows_sorted:
    t = r["timing"]
    when = f'{md(r["reaction"]["reveal_date"])} {t["timing_class"]} <span class="mut num">({t["time"]})</span>'
    if t["observable_v2"]:
        ret = t["reaction_ret"]
        cls_ret = "up" if ret >= 0 else "dn"
        rv = t["reaction_relvol"]
        rv_s = f' <span class="mut">·거래량{rv:.1f}배</span>' if rv is not None else ""
        react = f'<span class="{cls_ret} num">{ret:+.1f}%</span>{rv_s}'
    else:
        react = f'<span class="mut">{md(t["reaction_date_v2"])} 대기</span>'
    cv = r["concord_v2"]
    ccls = {"✓": "ok", "✗": "bad"}.get(cv, "na")
    H.append(f'<tr><td>{r["name"]} <span class="mut num">{r["code"]}</span></td>'
             f'<td><span class="pill {PILL[r["classification"]]}">{r["classification"]}</span></td>'
             f'<td class="n">{fmt_basis(r)}</td><td class="n">{fmt_op(r)}</td>'
             f'<td>{when}</td><td>{react}</td><td class="c chk {ccls}">{cv}</td></tr>')
H.append('</tbody></table></div>')

H.append('<footer>분류 기준: 컨센서스 보유 종목은 beat%(실제 vs 컨센 영업이익, ±10%), 미보유 종목은 H1 영업이익 YoY(±30%·흑전/적전). '
         '발표시각 KIND(kind.krx.co.kr) 공시목록 · 반응 재계산 OHLCV 캐시(~8/14) · 8/18 대기 = 8/14 장후 공시분.</footer>')
H.append("</main>")

out = "\n".join(H)
path = os.path.join(SCRATCH, "earnings-classify.html")
with open(path, "w", encoding="utf-8") as f:
    f.write(out)
print("html written:", path, len(out), "bytes")
