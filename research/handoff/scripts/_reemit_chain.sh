#!/bin/bash
# 시가 포함 경로 재방출 → 연장분 재생성. 순서가 중요하다(연장은 경로에서 만든다).
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
bash research/handoff/scripts/_us_paths_run.sh
D=$(ls .cache/bt5y/sub/uspath_20*.json 2>/dev/null | wc -l)
if [ "$D" -ne 6 ]; then echo "[chain] 경로 ${D}/6 — 연장 건너뜀"; exit 1; fi
echo "[chain] 시가 확인:"
python -c "
import json
d=json.load(open('.cache/bt5y/sub/uspath_2021.json',encoding='utf-8'))['trigger_paths'][0]
print('   키:',sorted(d.keys()))
print('   o 있음:', 'o' in d, '| 길이 일치:', len(d.get('o',[]))==len(d['c']))
print('   첫 5개 o:', d.get('o',[])[:5])"
echo "[chain] 연장 재생성"
python -u research/handoff/scripts/40-extend-cap-paths.py 2>&1 | tail -8
echo CHAIN_DONE
