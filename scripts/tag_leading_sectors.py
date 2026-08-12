"""SEPA 후보 종목 주도 섹터 태깅(①~⑧ 주도 + ⑨백화점 동행 소비주) — /sepa 마무리 비차단 스텝(수출 태깅 형제).

입력: sepa-{trend,vcp,power-play-all,3c}-candidates.json + sepa-buy-recommendations.json
      + leading-sectors-config.json (큐레이션 코드→섹터 매핑, 사용자 직접 관리)
출력: public/data/sepa-leading-sectors.json (tags + 미분류 목록)
실패 시: 이전 산출 유지(비차단) — exit 0 유지, 경고만 출력.

수출 태깅과 달리 키워드 자동매칭이 없다 — HBM 후공정 vs 반도체 일반 구분·이름 함정
(사명만 로봇)은 업종 텍스트로 판별 불가라 큐레이션 매핑이 정본. assignments·reviewed_none
어디에도 없는 신규 종목은 '미분류'로 보고해 증분 분류를 유도한다.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from tag_export_leaders import collect_codes  # noqa: E402  (동일 후보 파일 집합 재사용)

DATA = ROOT / "public" / "data"


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔에서 이모지 출력 크래시 방지
    # 비차단 계약: 어떤 실패든 경고 한 줄 + 이전 산출 유지 + exit 0.
    try:
        config = json.loads((DATA / "leading-sectors-config.json").read_text(encoding="utf-8"))
        codes, names, asof = collect_codes()
    except Exception as e:
        print(f"⚠️ 설정/후보 파일 오류({e}) — 이전 섹터 태그 유지")
        return
    if not codes:
        print("⚠️ 후보 파일에 종목 없음 — 이전 섹터 태그 유지")
        return
    try:
        sectors = {s["rank"]: s for s in config["sectors"]}
        assign = config.get("assignments", {})
        reviewed_none = config.get("reviewed_none", {})
        tags, unclassified = {}, []
        for code in codes:
            a = assign.get(code)
            if a:
                s = sectors.get(a.get("rank"))
                if not s:  # 설정파일은 사용자 직접 관리 — rank 오타가 페이지를 깨지 않게 건너뜀
                    continue
                tags[code] = {"name": names.get(code) or a.get("name"), "rank": a["rank"],
                              "label": s["label"], "short": s["short"],
                              "confidence": a.get("confidence", "high")}
            elif code not in reviewed_none:
                unclassified.append({"code": code, "name": names.get(code)})
    except Exception as e:
        print(f"⚠️ 태깅 오류({e}) — 이전 섹터 태그 유지 (설정 스키마 확인 필요)")
        return
    out = {"asof": asof, "config_asof": config.get("asof"), "tags": tags, "unclassified": unclassified}
    (DATA / "sepa-leading-sectors.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    by = {}
    for t in tags.values():
        by[t["rank"]] = by.get(t["rank"], 0) + 1
    print(f"💾 저장: sepa-leading-sectors.json — {len(tags)}종목 태깅 / 대상 {len(codes)}종목 / 미분류 {len(unclassified)}")
    for r in sorted(by):
        print(f"   {r}위 {sectors[r]['short']}: {by[r]}")
    if unclassified:
        head = ", ".join(f"{u['name']}({u['code']})" for u in unclassified[:20])
        print(f"   ⚠️ 미분류(증분 분류 필요): {head}" + (" …" if len(unclassified) > 20 else ""))


if __name__ == "__main__":
    main()
