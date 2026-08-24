# 요약 산출물 스냅샷 (`results/data/`)

> 만든 것: `research/handoff/scripts/_snapshot_data.py`
> 원본 위치: `.cache/bt5y/out/` — **`.gitignore:8` 의 `.cache/` 에 걸려 추적되지 않는다.**
> 그래서 **숫자를 만든 중간 파일이 저장소에 없었고**, 그게 21번 감사의
> 「코드 없음 9행」이 난 구조다. **입력이 사라지면 스크립트가 있어도 재현이 안 된다.**
> 이 폴더가 그 고리를 닫는다: **숫자 → 요약 JSON → 스크립트.**

🚨 **`.cache/sharadar/` 는 여기에 절대 넣지 않는다** — 라이선스상 재배포 금지 ·
해지 후 삭제 의무. 이 스냅샷은 **파생 집계만** 담는다.

## 🚨 **미해결 과제 — 산출 스크립트 «미상» 4파일**

**「정의 미상」으로 분류했으면 정의를 찾는 것이 과제다. 목록이 없으면 아무도 안 찾는다.**

🚨 **채울 때 규칙: 「추정」이 아니라 「파일 내용과 스크립트 출력이 «일치함을 확인»」으로만.**
추정으로 채우면 21번 감사가 잡은 것과 **같은 병**이다.

- [ ] `19-min-daily-count.json`
- [ ] `23d-mechanism.json`
- [ ] `24-universe-union.json`
- [ ] `_DISCARDED_12-exit-grid-oldcanon.json`

## 넣은 것 (개당 5MB 이하)

| 파일 | 크기 | 만든 스크립트 |
|---|---:|---|
| `01-path-build.json` | 2.1 KB | `research/handoff/scripts/01-path-build.py  (본문 대조 확인)` |
| `01b-cand-path-build.json` | 2.6 KB | `research/handoff/scripts/01b-cand-path-build.py  (본문 대조 확인)` |
| `02-grade-table.json` | 10.7 KB | `research/handoff/scripts/02-grade-table.py  (본문 대조 확인)` |
| `03-turnover-order.json` | 24.8 KB | `research/handoff/scripts/03-turnover-order.py  (본문 대조 확인)` |
| `03a-circular-shift-check.json` | 0.7 KB | `research/handoff/scripts/03a-circular-shift-check.py  (본문 대조 확인)` |
| `04-superperf-score.json` | 14.4 KB | `research/handoff/scripts/04-superperf-score.py  (본문 대조 확인)` |
| `05-first-day-close.json` | 5.0 KB | `research/handoff/scripts/05-first-day-close.py  (본문 대조 확인)` |
| `06-early-exit-10.json` | 32.8 KB | `research/handoff/scripts/06-early-exit-10.py  (본문 대조 확인)` |
| `07-time-limit.json` | 5.1 KB | `research/handoff/scripts/07-time-limit.py  (본문 대조 확인)` |
| `08-plus8-threshold.json` | 6.1 KB | `research/handoff/scripts/08-plus8-threshold.py  (본문 대조 확인)` |
| `08b-m1-universe-check.json` | 3.7 KB | `research/handoff/scripts/08b-m1-universe-check.py  (본문 대조 확인)` |
| `09-loss-streak-pause.json` | 9.8 KB | `research/handoff/scripts/09-loss-streak-pause.py  (본문 대조 확인)` |
| `10-breakout-order.json` | 8.9 KB | `research/handoff/scripts/10-breakout-order.py  (본문 대조 확인)` |
| `11-same-day-correlation.json` | 5.2 KB | `research/handoff/scripts/11-same-day-correlation.py  (본문 대조 확인)` |
| `12-exit-grid-gate.json` | 4.5 KB | `research/handoff/scripts/12-exit-grid-gate.py  (본문 대조 확인)` |
| `12-exit-grid.json` | 345.8 KB | `research/handoff/scripts/{12-exit-grid-gate.py, 12-exit-grid.py}  (본문 대조 · **여러 개 — 확정 필요**)` |
| `12a-slot-sim-gate.json` | 4.3 KB | `research/handoff/scripts/12a-slot-sim-gate.py  (본문 대조 확인)` |
| `12b-exit-grid-thresholds.json` | 53.3 KB | `research/handoff/scripts/12b-exit-grid-thresholds.py  (본문 대조 확인)` |
| `12ii-b-dropyear.json` | 6.7 KB | `research/handoff/scripts/12ii-b-dropyear.py  (본문 대조 확인)` |
| `12ii-self-entry-grid.json` | 40.8 KB | `research/handoff/scripts/12ii-self-entry-grid.py  (본문 대조 확인)` |
| `12iii-decompose-slip.json` | 52.0 KB | `research/handoff/scripts/12iii-decompose-slip.py  (본문 대조 확인)` |
| `13-megacap-momentum.json` | 4.8 KB | `research/handoff/scripts/13-megacap-momentum.py  (본문 대조 확인)` |
| `14-stop-loss-recheck.json` | 64.8 KB | `research/handoff/scripts/14-stop-loss-recheck.py  (본문 대조 확인)` |
| `15-variant2-followup.json` | 4.9 KB | `research/handoff/scripts/15-variant2-followup.py  (본문 대조 확인)` |
| `15b-neighbor-days.json` | 1.1 KB | `research/handoff/scripts/15b-neighbor-days.py  (본문 대조 확인)` |
| `16-selection-edge-raw.json` | 721.5 KB | `research/handoff/scripts/16-selection-edge.py  (본문 대조 확인)` |
| `16-selection-edge.json` | 19.2 KB | `research/handoff/scripts/16-selection-edge.py  (본문 대조 확인)` |
| `16b-beta1-slot5.json` | 1.5 KB | `research/handoff/scripts/16b-beta1-slot5.py  (본문 대조 확인)` |
| `16c-trigger-compare.json` | 3.0 KB | `research/handoff/scripts/16c-trigger-compare.py  (본문 대조 확인)` |
| `17-fee-and-compounding.json` | 18.1 KB | `research/handoff/scripts/17-fee-and-compounding.py  (본문 대조 확인)` |
| `17b-turnover-drag.json` | 0.7 KB | `research/handoff/scripts/17b-turnover-drag.py  (본문 대조 확인)` |
| `17d-slip-grid.json` | 8.1 KB | `research/handoff/scripts/17d-slip-grid.py  (본문 대조 확인)` |
| `17e-selection-noise.json` | 2.1 KB | `research/handoff/scripts/17e-selection-noise.py  (본문 대조 확인)` |
| `18-slot-selection-cause.json` | 2.5 KB | `research/handoff/scripts/18-slot-selection-cause.py  (본문 대조 확인)` |
| `18b-premise-and-calendar.json` | 1.1 KB | `research/handoff/scripts/18b-premise-and-calendar.py  (본문 대조 확인)` |
| `19-min-daily-count.json` | 0.2 KB | `**미상 — 적을 것**` |
| `19-volume-axis-stage0.json` | 0.6 KB | `research/handoff/scripts/19-volume-axis.py  (본문 대조 확인)` |
| `19-volume-features.json` | 964.6 KB | `research/handoff/scripts/19-volume-axis.py  (본문 대조 확인)` |
| `19-volume-stage1.json` | 4.8 KB | `research/handoff/scripts/19b-volume-stage1.py  (본문 대조 확인)` |
| `19c-lookahead-and-484.json` | 2.8 KB | `research/handoff/scripts/19c-lookahead-and-484.py  (본문 대조 확인)` |
| `19d-decile-and-months.json` | 13.6 KB | `research/handoff/scripts/19d-decile-and-months.py  (본문 대조 확인)` |
| `20-slot-full-vs-open.json` | 0.7 KB | `research/handoff/scripts/20-slot-full-vs-open.py  (본문 대조 확인)` |
| `22-gapup-volume.json` | 5.1 KB | `research/handoff/scripts/22-gapup-volume.py` |
| `23-gate-path-identity.json` | 0.2 KB | `research/handoff/scripts/23-stage0-ratchet.py 외 23* 계열` |
| `23-stage0-ratchet.json` | 8.8 KB | `research/handoff/scripts/23-stage0-ratchet.py 외 23* 계열` |
| `23-stage1-ratchet.json` | 17.7 KB | `research/handoff/scripts/23-stage0-ratchet.py 외 23* 계열` |
| `23b-loy-and-slip.json` | 13.3 KB | `research/handoff/scripts/23b-loy-and-slip.py  (본문 대조 확인)` |
| `23c-boot-and-maxstat.json` | 3.6 KB | `research/handoff/scripts/23c-boot-and-maxstat.py  (본문 대조 확인)` |
| `23d-mechanism.json` | 2.2 KB | `**미상 — 적을 것**` |
| `24-universe-union.json` | 26.7 KB | `**미상 — 적을 것**` |
| `24c-subuniverse.json` | 3.3 KB | `research/handoff/scripts/24c-subuniverse.py  (본문 대조 확인)` |
| `25-g3prime.json` | 203.0 KB | `research/handoff/scripts/25-g3prime.py` |
| `25-split-factors.json` | 791.9 KB | `research/handoff/scripts/25-split-check.py` |
| `25-split-impact.json` | 115.9 KB | `research/handoff/scripts/25-split-impact.py` |
| `26-eqw-korea.json` | 69.3 KB | `research/handoff/scripts/26-eqw.py` |
| `26-eqw-kr.json` | 139.1 KB | `research/handoff/scripts/26-eqw.py` |
| `26-eqw-us.json` | 148.1 KB | `research/handoff/scripts/26-eqw.py` |
| `27-kr-extreme-audit-50-100.json` | 22.1 KB | `research/handoff/scripts/27-kr-extreme-audit.py` |
| `27-kr-extreme-audit.json` | 1.9 KB | `research/handoff/scripts/27-kr-extreme-audit.py` |
| `28-headline.json` | 13.0 KB | `research/handoff/scripts/28-headline.py` |
| `29-cols-kr.json` | 633.4 KB | `research/handoff/scripts/29-trigger-match.py  ⚠️철회됨` |
| `29-trigger-match-kr.json` | 1.3 KB | `research/handoff/scripts/29-trigger-match.py  ⚠️철회됨` |
| `31-slot-diagnosis.json` | 1.6 KB | `research/handoff/scripts/31-slot-diagnosis.py` |
| `32-funnel-why-kr.json` | 1.9 KB | `research/handoff/scripts/32-funnel-why.py` |
| `32-funnel-why-us.json` | 1.8 KB | `research/handoff/scripts/32-funnel-why.py` |
| `33-unresolved-and-extremes.json` | 8.5 KB | `research/handoff/scripts/33-unresolved-and-extremes.py` |
| `34-turnover-kr-seasonal.json` | 4.7 KB | `research/handoff/scripts/34-turnover-concentration.py` |
| `34-turnover-kr.json` | 4.2 KB | `research/handoff/scripts/34-turnover-concentration.py` |
| `_DISCARDED_12-exit-grid-oldcanon.json` | 264.2 KB | `**미상 — 적을 것**` |

## 🚨 안 넣은 것 — **무언의 절단이 아니다. 크기와 함께 적는다**

| 파일 | 크기 | 만든 스크립트 |
|---|---:|---|
| `cand_paths_2021.json` | **104.2 MB** | `**미상 — 적을 것**` |
| `cand_paths_2022.json` | **50.5 MB** | `**미상 — 적을 것**` |
| `cand_paths_2023.json` | **76.7 MB** | `**미상 — 적을 것**` |
| `cand_paths_2024.json` | **60.0 MB** | `**미상 — 적을 것**` |
| `cand_paths_2025.json` | **73.0 MB** | `**미상 — 적을 것**` |
| `cand_paths_2026.json` | **14.1 MB** | `**미상 — 적을 것**` |
| `paths_2021.json` | **42.7 MB** | `**미상 — 적을 것**` |
| `paths_2022.json` | **19.6 MB** | `**미상 — 적을 것**` |
| `paths_2023.json` | **28.9 MB** | `**미상 — 적을 것**` |
| `paths_2024.json` | **25.6 MB** | `**미상 — 적을 것**` |
| `paths_2025.json` | **28.2 MB** | `**미상 — 적을 것**` |
| `paths_2026.json` | **7.3 MB** | `**미상 — 적을 것**` |

## 여기에 없는 것 (설계상)

- **이벤트 목록 원본** (`.cache/bt5y/sub/*.json`, `bt_*.json`) — 개당 0.3~5MB이고
  2.5단계 관문만 팔은 150~200MB로 예상된다. **결과 문서의 숫자는 전부 요약 JSON에서
  나오므로 재현에 필요한 것은 위 표로 충분하다.**
- **가격 원본** (`.cache/pdata/`, `.cache/sharadar/`) — 전자는 용량, 후자는 라이선스.

총 69개 넣음 · 12개 제외.