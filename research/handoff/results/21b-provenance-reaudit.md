# 21b — 출처 재감사 (archive 범위)

## 🚨 자료 기준일 — **2026-08-20** (한국 pdata)

> **이 문서의 한국 숫자는 `price_20260820.json` 까지의 자료로 나왔다.**
> **추정이 아니라 복원값이다** — 산출 코드 `research/handoff/scripts/_asof_recover.py`.
> 이 파일의 **마지막 커밋 시각**에 pdata 에 **이미 있던** 가장 늦은 거래일을 계산했다.
> **결과 문서 39개 전부 `2026-08-20` · 미상 0개.**
>
> ★ 앞끝이 **2026-08-21 16:09 부터 2026-08-24 20:00 까지 줄곧 `2026-08-20`** 이었고
> 모든 커밋이 그 사이에 있다 → **그 안에서 언제 계산했든 답이 같다.**
> **상한이 아니라 확정에 가깝다.**
>
> 🚨 **창 라벨 「~ 2026-08-21」은 «명령줄에 지정한 값»이지 자료 끝이 아니다.**
> `price_20260821.json` 은 **2026-08-24 20:00 에야 들어왔다.**
> 창 끝으로 라벨했다면 **자료가 없던 날짜를 자료 기준일로 적을 뻔했다.**
> **실제 마지막 거래일은 `2026-08-20`.**
>
> ⚠️ **pdata 는 매 영업일 자란다** — 다시 돌리면 마지막 해의 거래일 수와 값이 조금 다르다.
> **재현 실패가 아니다.** 미국(Sharadar)은 **정적 파일**(`stocks-10Y.csv.zip` · 2026-08-24
> 07:14 고정 · 내려받기 코드 없음)이라 **재현이 고정된다. 두 시장의 재현 성질이 다르다.**


- 지시서: 두뇌 세션 26-08-23 «② 21번 재감사 — archive 범위로»
- 대상 `research/provenance-archive/` (커밋 `8722a5ba`) · **`.py` 752개 + `README.md` 1개**
- **스크립트 없음.** 읽기·대조뿐이다. **archive 안의 코드는 한 줄도 실행하지 않았다.**
- 이 파일은 `21-provenance-audit.md`의 **출처 축 라벨을 대체**한다. 건전성 축과 여섯 물음 본문은 그대로다.

> ### 🚨 archive 안에 **네트워크를 부르는 파일이 있다** — 안전 조항 재확인
> `aff259ca/…/probe1.py`(Naver) · `probe1_krx.py`·`probe2_krx.py`·`probe3_anon.py`(KRX) ·
> `probe5_kis.py`(KIS) · `short_probe.py`. **열어서 머리말만 읽었고 실행하지 않았다.**
> 두뇌 세션 지시대로 **archive는 대조용이지 실행용이 아니다.**

---

## ★ 재감사의 가장 큰 소득은 라벨이 아니다

**`.py`만 보존됐고, 그 스크립트들이 읽는 중간 산출 JSON은 보존되지 않았다.**

예: ⑨와 ⑪의 산출 코드는 첫 세 줄이 이렇다.

```python
S = os.environ['SCRATCH']
rows = json.load(open(os.path.join(S, 'taskC', 'joinedC.json'), encoding='utf-8'))
```

`research/provenance-archive/` 안에 **`joined*.json`은 0개**다(파일 종류: `.py` 752 · `.md` 1).

**그 입력들은 아직 임시 폴더에 살아 있다:**

| | 값 |
|---|---|
| 살아 있는 스크래치패드 `.json` | **303개** |
| `joinedC.json` / `joinedC2.json` | **267KB / 318KB** (⑨·⑪이 읽는 그 파일) |
| 스크래치패드 총 용량 | 0.076M · 153M · 0.19M · 241M · **1.1G** · 2.5M |

> **즉 코드는 구조가 차단됐지만 재현은 여전히 막혀 있다.**
> 막는 것이 "코드가 없다"에서 **"입력이 임시 폴더에만 있다"**로 바뀌었을 뿐이다.
> **어떻게 할지는 정하지 않았다** — 1.1GB를 저장소에 넣는 것은 제 판단 밖이다.
> 다만 **⑨·⑪이 필요로 하는 두 파일은 합쳐 585KB**라는 사실만 적는다.

---

## 라벨 세 갈래 — 12행

`저장소에 없음` = 저장소 안에는 없다(archive 확인 전 상태) ·
`archive에 있음` = 산출 코드로 보이는 파일을 archive에서 찾았다 ·
`어디에도 없음` = 저장소·archive 어디에서도 찾지 못했다

| # | 메모리 | **출처(신)** | 근거 파일 | 건전성 |
|---|---|---|---|---|
| ① | `correction-regime-volume-edge` | **어디에도 없음** | `2427`·`1658`·`769` archive 0히트. 2026-07-08 세션이 보존 6개에 없다 | **룩어헤드** |
| ② | `actionable-leading-discriminators` | **archive에 있음** | `aff259ca/…/build_events.py` · `aggregate.py` · `finalize.py` · `adversarial_verify.py` · `verify_stats.py` | **룩어헤드(코드 확인)** |
| ③ | `sepa-nextday-breakout-findings` | **저장소에 있음** (코드-값 일치) | `scripts/pivot_backtest_nextday.py:110,125,127` | **룩어헤드** |
| ③ˣ | 〃 색인줄 **57.4%** | **어디에도 없음** (값 불일치) | 저장소·archive 모두 0히트 | 미확인 |
| ④ | `minervini-breakout-validation` | **어디에도 없음** | `2446`·`더블` 히트 2건은 각각 **04번 검증본**·**변동성 파일럿 panel** — 주제가 다르다 | 미확인 |
| ⑤ | `winner-characteristics` | **어디에도 없음** | `pace` archive **0히트**. `cmp_exit.py`는 `_cache-bt5y/`에 보존됐으나 `rs`·`pace` 0회 | 미확인 |
| ⑥ | `scorecard-winner-traits` | **archive에 있음(후보)** | `c9b9862c/retro.py` · `retro2.py` · `scratchpad/cf.py` · `aff259ca/verify_stats.py` (scorecard 장부를 읽는다) | 미확인 |
| ⑦ | `threshold-newcomer-caution` | **archive에 있음** | `aff259ca/…/build_passmatrix.py` · `finalize_newcomer.py` · `newcomer_analysis.py` · `verify_newcomer.py` (+ 저장소 미추적 `scripts/_build_passmatrix.py`) | 미확인 |
| ⑧ | `correction-bottom-leader-factors` | **어디에도 없음** | `21026` 0히트. 그 세션이 보존 6개에 없다 | 미확인 |
| ⑨ | `gate-relaxation-backtest-verdict` | **archive에 있음** | `c9b9862c/c1.py` · `c15.py` · `scratchpad/deep.py` (`gate_near` 카운터) — **입력 `taskC/joinedC.json` 미보존** | 미확인 |
| ⑩ | `ipo-track-validation` | **archive에 있음(후보)** | `990b6503/…/repro_edges.py` 하나뿐. 그 세션은 **실적캘린더 세션**이라 IPO 재현 본체인지 미확인 | 미확인 |
| ⑪ | `volatility-pilot-backtest` | **archive에 있음** | `c9b9862c/c9.py`(국면×손절률) · `extract.py`("events 614건에 as-of 요인") · `panel.py`("2025-11-26 ~ 2026-08-21") — **입력 `taskC/joinedC2.json` 미보존** | 미확인 |
| ⑫ | `liquidity-burden-display` | **어디에도 없음** | `c9b9862c/_liq.py`는 **유동성 문턱 출력기**다(6줄, `MIN_TURNOVER_EOK_DEFAULT` 인쇄). 34건 측정 코드 없음 | 미확인 |

**`archive에 있음` 5행(② ⑥ ⑦ ⑨ ⑪, 그중 2행은 후보) · `저장소에 있음` 1행(③) · `어디에도 없음` 6행(① ③ˣ ④ ⑤ ⑧ ⑫).**

**`문제 없음`은 이번에도 0행이다.**

---

## 여섯 물음을 다시 건 것 — **찾은 것만**

### ② `actionable-leading-discriminators` — **룩어헤드를 코드로 확인**

1. **코드** `research/provenance-archive/aff259ca-…/scratchpad/build_events.py`
   머리말: *"Actionable+leading-sector cohort: events, entries, outcomes, discriminators."*
2. **계산이다**(하드코딩 아님).
3. **표본** — 코드가 `entry_i` 기준 코호트를 만든다. 메모리의 40/25/19와 대조는 못 했다(출력 JSON 미보존).
4. **룩어헤드 — 있다. 필드 이름 그대로 옮겨 적는다:**

```python
    # entry-day features
    relvol = None
    if entry_i >= 10:
        w = v[max(0, entry_i - 50):entry_i]
        m = mean(w) if w else None
        if m and m > 0:
            relvol = v[entry_i] / m
    gap = (o[entry_i] / c[entry_i - 1] - 1) * 100 if entry_i >= 1 else None
```
   필드명 **`relvol_entry`** · 분자 **`v[entry_i]`(진입일 자신의 종일 거래량)** · 분모 직전 50일 평균.
   **`scripts/canslim_lib/pivot_backtest.py`의 `rel_volume(series, ni)`와 같은 구조**이고,
   이 세션이 금지한 **`rel_vol_entry_LOOKAHEAD_DO_NOT_FILTER`와도 같은 구조**다.
   같은 함수가 만드는 이웃 필드 **`mfe10`·`mae10`·`r10`도 `entry_i` 이후 10일을 본다**(주석: *"raw path, no stop"*).
5. **다중검정** — 보정 코드 없음. 메모리 본문은 "p는 낙관적"이라고 적는다.
6. **재현 미실행** — 입력 pdata 경로가 원 세션 기준이고, 지시대로 실행하지 않았다.

### ⑦ `threshold-newcomer-caution`
1. `aff259ca/…/build_passmatrix.py`(+`av_load.py`·`av_matrix_check.py`·`av_stats_check.py`·
   `finalize_newcomer.py`·`newcomer_analysis.py`·`verify_newcomer.py`·`flicker_analysis.py`·`flicker_check2.py`).
   저장소에도 **미추적** `scripts/_build_passmatrix.py`(494행)가 있다.
2~6. **읽기만 했다.** `0.78`은 archive에 0히트 — **값이 코드에 없고 출력에만 있었다.**
   `av_load.py` 머리말이 *"Adversarial verify — independent raw-pdata loader (my own implementation)"*라
   **적대검증이 별도 구현으로 돌았다는 사실**은 코드로 확인된다.

### ⑨ `gate-relaxation-backtest-verdict`
1. `c9b9862c/c1.py`가 `gate_near` 분포를 세고 `deep.py`·`c15.py`가 이어받는다.
2. **계산이다.** 3. 입력 `taskC/joinedC.json`을 읽는데 **archive에 없다.**
4. 미확인. 5. 보정 코드 없음. 6. **재현 불가**(입력 미보존).

### ⑪ `volatility-pilot-backtest`
1. `c9b9862c/extract.py`(*"events 614건에 as-of 요인들을 붙인다. **scan_date 까지 절단한 시계열만 사용**"*) ·
   `panel.py`(*"pdata **2025-11-26 ~ 2026-08-21** 패널 적재"*) · `c9.py`(국면×손절률).
   **메모리의 기간·건수와 코드 머리말이 문자 그대로 일치한다.**
2. 계산. 3. **일치**(614건 · 2025-11-26~2026-08-21).
4. `extract.py` 머리말이 **"scan_date 까지 절단"**이라 적는다 — **as-of 의도는 코드에 있다.** 실제 절단 여부는 미검증.
5. 보정 코드 없음. 6. **재현 불가**(입력 `joinedC2.json` 미보존).
   ⚠️ **`+2.68`은 archive에 0히트** — 그 값을 만드는 줄을 찾지 못했다.

### ⑥ `scorecard-winner-traits` (후보)
`c9b9862c/retro.py`·`retro2.py`·`scratchpad/cf.py`, `aff259ca/verify_stats.py`가 정산표 장부를 읽는다.
**"VCP 47% vs 무셋업 10%"를 내는 줄은 확인하지 못했다.** 후보까지다.

### ⑩ `ipo-track-validation` (후보)
`990b6503/…/repro_edges.py` 하나. **그 세션은 실적캘린더 세션**(`mut/scripts/screen_earnings_calendar.py`·
`repro_ir_expected.py`·`repro_rule2_clamp.py`)이라 **IPO 재현 검증 본체로 보기 어렵다.** 후보까지다.

---

## 찾지 못한 여섯 — **사실만**

| # | 찾은 히트 | 그것이 아닌 이유 |
|---|---|---|
| ① | 0 | 2026-07-08 조정장 세션이 보존 6개(`0ab26997`·`6169d0c4`·`990b6503`·`aff259ca`·`c9b9862c`·`f3bf3bbc`)에 없다 |
| ③ˣ 57.4% | 0 | 저장소·archive 모두 |
| ④ | 2 | `6169d0c4/v04_verify.py` = **04번(초수익 점수) 검증본** · `c9b9862c/orderK/panel.py` = 변동성 파일럿 |
| ⑤ | 0 | `pace` 문자열 자체가 archive 전체에 없다 |
| ⑧ | 0 | `21026` 0히트 |
| ⑫ | 1 | `_liq.py`는 6줄짜리 문턱 출력기 |

---

## 한계 — 숫자로

1. **archive 코드를 한 줄도 실행하지 않았다.** 지시대로 대조용으로만 썼다.
   따라서 **`archive에 있음` 5행 중 어느 것도 `코드-값 일치`가 아니다.**
2. **중간 산출 JSON이 archive에 없다**(위 ★). ⑨·⑪은 **코드가 있어도 재현이 막혀 있다.**
3. **`archive에 있음(후보)` 2행(⑥ ⑩)은 "그 숫자를 내는 줄"을 확인하지 못했다.**
4. **주장의 숫자가 코드에 없는 것이 정상이다** — 스크립트가 계산해 인쇄하고 사람이 옮겨 적었기 때문이다.
   그래서 **숫자 grep으로 `어디에도 없음`을 확정하는 것은 약한 근거**다. ①④⑤⑧은
   **주제어**(`pace`·`21026`·`2446`)로도 0히트라 함께 적었지만, **"없다"의 증명은 아니다.**
5. **752개 전부의 머리말을 읽지는 않았다** — 독스트링이 있는 **226개**만 자동 추출해 훑었고,
   나머지 **526개는 이름과 grep 결과로만 걸렀다.**
6. **건전성 축은 ②만 갱신했다**(추론 → 코드 확인). 나머지 11행은 21번 그대로다.
7. **판정하지 않았다.** 이 파일은 숫자와 사실만 담는다.

---

# 재검색 — **숫자가 아니라 산출물 파일명으로** (두뇌 세션 지시 ②)

## 🚨 먼저 — **탐색 범위가 또 틀렸습니다**

21번에서 저는 파일 존재 확인을 **`ls scripts/` (최상위)**로 했습니다.

| | 값 |
|---|---:|
| `scripts/**/*.py` | **216개** |
| 그중 `ls scripts/*.py`로 보이는 것 | **87개** |
| **못 본 하위 폴더** | `oneil_model_book`(**84개**) · `canslim_lib` · `autobuy` · `monitor` |

`exit-rules-path-and-profit-protect`가 이름 붙인 산출물로 검색하니 **전부 저장소에 있었습니다**:
`scripts/oneil_model_book/analyze_path_mae.py` · `analyze_profit_protect.py` ·
`research/oneil-model-book/_path_mae.txt` · `_path_mae_c2020.txt` · `_profit_protect.txt` ·
`_profit_protect_c2020.txt` · `korea_exit_rules.md`.

**→ 파일명 키가 숫자 키보다 확실히 낫습니다.** 두뇌 세션·검증 세션 지적이 맞습니다.

## 라벨 정정

**`어디에도 없음` → `찾은 범위에서 못 찾음`**으로 바꿉니다. **라벨은 세계가 아니라 탐색을 반영해야 합니다.**

이번 탐색 범위를 명시합니다:
- `research/provenance-archive/` **`.py` 752개** 중 **독스트링 226개는 머리말 확인**, **526개는 이름·grep만**
- 저장소 **`scripts/**/*.py` 216개 전수(재귀)** · `research/` · `src/` · `public/data/`
- **archive 코드는 한 줄도 실행하지 않음**

## 여섯 행 재검색 결과 — 각 메모리가 이름 붙인 산출물로

| # | 메모리가 이름 붙인 산출물 | 찾았나 | 그것이 주장의 산출 코드인가 |
|---|---|---|---|
| ① | `pivot_backtest_nextday_multi.py` · `pivot_backtest.py:108` · `replay.py` · `.cache/min_daily` | **전부 있음** | **아니다** — `_multi.py`에 거래량 코드 없음(21번 확인). **2,427건 국면×거래량 표를 내는 파일은 못 찾음** |
| ③ˣ | (색인줄이 산출물을 이름 붙이지 않음) | — | **키가 없다** |
| ④ | `monster_lib.py` | **없음**(저장소·archive 전부 0) | — |
| ④ | `track_buy_recommendations.py` | **있음** `scripts/` | **아니다** — 머리말이 *"매수 추천 **살아있는 검증** — 매일 추천 리스트를 원장에 기록하고 **전방** 성과를 갱신"*. **전방 원장 추적기지 2,446진입 백테스트가 아니다** |
| ④ | `public/data/sepa-buy-rec-ledger.json` · `_rsrank.json` | 원장 **있음** · `_rsrank.json` **없음** | 원장은 산출 데이터 |
| ⑤ | `cmp_exit.py` | **있음** `.cache/bt5y/`(+archive `_cache-bt5y/`) | **아니다** — `rs`·`pace` 0회 |
| ⑤ | (그 외 산출물 이름 없음) | — | ⚠️ 정정: `pace`는 **archive에 0회**지만 **저장소에는 있다** — `scripts/autobuy/signals.py`·`replay.py`·`verify_volume.py`·`runner.py`·`canslim_lib/kis_api.py`. **다만 이는 봇의 실시간 페이스 게이트이고 "903레코드 승자 판별" 분석이 아니다** |
| ⑧ | **메모리 본문에 파일명이 하나도 없다** | — | **키를 만들 수 없다.** `조정 바닥`·`bottom_dates`·`9바닥` 재귀 검색도 0히트 |
| ⑫ | `screen_buy_recommendations.py` · `strategy_params.py` · `tests/test_buy_recommendations.py` | **전부 있음** | **아니다** — 1.02는 여전히 **독스트링 문장**. archive `gapfill.py:47`은 *"손절일 **갭하락** 실태"*로 **거래대금이 아니다** |

## 갱신된 라벨 — 12행

| # | 출처(재검색 후) |
|---|---|
| ① | **찾은 범위에서 못 찾음** (지목 파일은 있으나 거래량 코드 부재) |
| ② | **archive에 있음** (`build_events.py`, 룩어헤드 코드 확인) |
| ③ | **저장소에 있음** |
| ③ˣ 57.4% | **찾은 범위에서 못 찾음** (산출물 키 없음) |
| ④ | **찾은 범위에서 못 찾음** (`monster_lib.py` 부재 · `track_*`는 전방 추적기) |
| ⑤ | **찾은 범위에서 못 찾음** (`cmp_exit.py`는 있으나 다른 코드) |
| ⑥ | **archive에 있음(후보)** |
| ⑦ | **archive에 있음** |
| ⑧ | **찾은 범위에서 못 찾음 — 키 자체가 없다** |
| ⑨ | **archive에 있음** (입력 미보존) |
| ⑩ | **archive에 있음(후보)** |
| ⑪ | **archive에 있음** (입력 미보존) |
| ⑫ | **하드코딩·비계산** (측정 코드는 찾은 범위에서 못 찾음) |

**`문제 없음`은 세 번째 감사에서도 0행입니다.**

## 이번 재검색이 못 하는 것

1. **`scripts/oneil_model_book/` 84개의 머리말을 전부 읽지는 않았습니다** — 주제어 매칭만 했고
   `bottom`·`바닥`·`pace`·`megacap`·`relvol`은 **0히트**였습니다.
2. **⑧은 키가 없어 재검색 자체가 불가능했습니다.** 이건 탐색의 한계가 아니라 **메모리의 결함**입니다 —
   그 메모리는 방법("FDR 전종목 `_hist`, 5샤드병렬")만 적고 **파일명을 하나도 남기지 않았습니다.**
3. **여전히 아무것도 실행하지 않았습니다.** `archive에 있음` 5행 중 `코드-값 일치`는 0행입니다.
4. **제 탐색 범위가 두 번 연속 틀렸습니다**(스크래치패드 → 하위 폴더). **세 번째가 없다고 말할 근거가 없습니다.**
