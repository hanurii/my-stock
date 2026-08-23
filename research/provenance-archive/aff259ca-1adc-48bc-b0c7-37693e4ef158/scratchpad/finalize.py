# -*- coding: utf-8 -*-
"""Combine events + tables into actionable_leading.json."""
import json, os

SCRATCH = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"
ev = json.load(open(os.path.join(SCRATCH, "events_raw.json"), encoding="utf-8"))
agg = json.load(open(os.path.join(SCRATCH, "agg_tables.json"), encoding="utf-8"))

anchors = {
    "설명": "사용자 실거래 4종목과 백테스트 이벤트 대조 (방향 일치 여부)",
    "rows": [
        {"code": "009150", "name": "삼성전기", "real": "-5.6%", "backtest": "이벤트 6/30, 진입 7/1, 손절 -10.34% (7/2)", "align": True},
        {"code": "086670", "name": "비엠티", "real": "-2.9%", "backtest": "이벤트 6/30, 진입 7/1, 손절 -10.34% (7/7)", "align": True},
        {"code": "219130", "name": "타이거일렉", "real": "+7.6%, +14.8%", "backtest": "이벤트 6/30, 진입 7/1, 익절 +19.66% (7/13 도달)", "align": True},
        {"code": "083450", "name": "GST", "real": "보유중 -4.5%", "backtest": "이벤트 8/11, 진입 8/12, 미결 -3.67% (8/14 종가 평가)", "align": True},
    ],
}

caveats = [
    "섹터 태그는 오늘(2026-08-14) 기준 소급 적용 — 가벼운 사후편향(당시엔 주도섹터인지 몰랐을 수 있음)",
    "진입일 상대거래량은 하루 전체 거래량 기준 — 장중 매수 시점엔 알 수 없는 값(장중 페이스로 근사 필요). 또한 당일 급등 자체가 거래량을 만드는 순환성 있음",
    "미결 6건은 8/14 종가 평가(mark) — 8월 코호트 성적을 부풀림. closed-only 수치를 항상 병기함",
    "표본 작음: 진입 25건, 확정 19건, 확정 승리 2건. 셀 n<8은 전부 참고용",
    "스냅샷 결측일 존재(7/9, 7/16~17, 7/30, 8/8 등 — 커밋 없던 날), 사건 시작일이 하루 이틀 늦게 잡혔을 수 있음",
    "광주신세계는 피벗 3.3% 차이로 이벤트 2건(8/11, 8/12) — 규칙대로지만 사실상 같은 셋업 중복",
    "r63(63일 수익률) 겉보기 역상관(-0.54)은 7월(고r63·하락국면) vs 8월(저r63·상승국면) 합성 효과 — 7월 내부에서는 r63>=40이 오히려 평균 -8.03 vs <40 -10.34로 더 낫다. 미너비니 '사전 대상승' 가설의 반증으로 읽지 말 것",
]

out = {
    "meta": {
        "built": "2026-08-16",
        "definition": "주도섹터 태그(sepa-leading-sectors.json 181종목) AND 야간 스냅샷에서 actionable 또는 entry_ready=true 최초 관측 → 이벤트",
        "snapshots": "2026-06-29 ~ 2026-08-15, 달력일당 마지막 커밋, 32개",
        "entry": "이벤트 다음 거래일부터 high>=직전 스냅샷 피벗 최초 도달일, 체결가=max(시가,피벗)",
        "exit": "+20%/-10% 장중 터치(같은 날 둘 다=패), 왕복비용 0.34%p, 40거래일 창, 미결=8/14 종가 평가+FLAG",
        "pivot_cluster": "같은 종목 재이벤트는 피벗 3% 초과 차이 또는 기존 이벤트 종결 후",
    },
    "summary": ev["summary"],
    "anchors": anchors,
    "discriminator_tables": agg["tables"],
    "rank_correlations": agg["rank_correlations"],
    "overall": agg["overall"],
    "caveats": caveats,
    "events": ev["events"],
}
p = os.path.join(SCRATCH, "actionable_leading.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("wrote", p)
