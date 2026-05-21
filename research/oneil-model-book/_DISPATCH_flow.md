# DISPATCH — 수급(I) 가드 데이터 수집 (창 하나당 1줄 · ~12분)

각 줄을 **새 PowerShell 창**(또는 새 Claude Code 세션)에 그대로 붙여넣고 엔터.
중간 실패 시 같은 줄 재실행하면 이어서 됨(멱등). 다른 파일 안 건드림.
끝나면 마지막 절차(REDUCE) 2줄 → 그다음은 메인세션(저)에게 'B 수집 끝' 알려주세요.

## c2024-12 (창 1~19)

창 1:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 0 --workers-total 19 --pages 30
창 2:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 1 --workers-total 19 --pages 30
창 3:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 2 --workers-total 19 --pages 30
창 4:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 3 --workers-total 19 --pages 30
창 5:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 4 --workers-total 19 --pages 30
창 6:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 5 --workers-total 19 --pages 30
창 7:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 6 --workers-total 19 --pages 30
창 8:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 7 --workers-total 19 --pages 30
창 9:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 8 --workers-total 19 --pages 30
창10:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 9 --workers-total 19 --pages 30
창11:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 10 --workers-total 19 --pages 30
창12:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 11 --workers-total 19 --pages 30
창13:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 12 --workers-total 19 --pages 30
창14:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 13 --workers-total 19 --pages 30
창15:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 14 --workers-total 19 --pages 30
창16:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 15 --workers-total 19 --pages 30
창17:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 16 --workers-total 19 --pages 30
창18:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 17 --workers-total 19 --pages 30
창19:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --codes-file _flow_candidates_c2024-12.txt --worker 18 --workers-total 19 --pages 30

## c2020-03 (창 20~31)

창20:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 0 --workers-total 12 --pages 30
창21:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 1 --workers-total 12 --pages 30
창22:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 2 --workers-total 12 --pages 30
창23:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 3 --workers-total 12 --pages 30
창24:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 4 --workers-total 12 --pages 30
창25:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 5 --workers-total 12 --pages 30
창26:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 6 --workers-total 12 --pages 30
창27:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 7 --workers-total 12 --pages 30
창28:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 8 --workers-total 12 --pages 30
창29:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 9 --workers-total 12 --pages 30
창30:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 10 --workers-total 12 --pages 30
창31:  cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --codes-file _flow_candidates_c2020-03.txt --worker 11 --workers-total 12 --pages 30

## 마지막: REDUCE (위 31창 전부 끝난 뒤, 아무 창에서 2줄)

cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2024-12 --reduce
cd C:\Users\hanul\playground\my-stock; $env:PYTHONIOENCODING='utf-8'; python scripts/oneil_model_book/collect_flow_universe.py --cycle c2020-03 --reduce

끝나면 메인 세션에 "B 수급 수집·reduce 완료" 라고만 알려주세요.
→ 제가 I가드 켜고 자본곡선 재실행(D3) + 최종 결론·문서반영 진행합니다.

## 참고
- 후보만 수집(전 유니버스 아님): c2024 1217종·c2020 737종.
- 네이버는 최근구간 위주 → 오래된 구간 결손 정상(추정 안 함).
- 더 잘게 원하면 workers-total 키우고 worker 0..그수-1 전부 돌리면 됨.