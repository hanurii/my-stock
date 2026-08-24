# -*- coding: utf-8 -*-
"""경로를 **줄 단위로 디스크에 흘린다.** 목록을 안 만든다.

왜
--
🚨 2026-08-24 밤, 기계가 실제로 찼다: 경로 방출 peak **2.09GB** 인데 여유 **1.75GB**.
claude 세션 셋이 1.5GB 를 쓰고 있는데 **그건 우리 자신이라 끌 수 없다.**
「여유가 생길 때까지 기다린다」는 **영영 안 올 수 있다.**

**사양(`PATH_DAYS=250`)은 «안» 바꾼다.** 쌓는 자리만 디스크로 옮긴다.
시세 행렬(~1.5GB)은 못 줄이므로 **그 위에 얹히던 몫만 사라진다.**

어떻게
------
- `_PathSink.append()` 가 `<out>.paths.jsonl` 에 **한 줄씩** 쓴다
- `merge_paths()` 가 그 파일을 **한 줄씩 읽어** 최종 JSON 에 이어 붙인다
- **어느 쪽도 전량을 메모리에 올리지 않는다**
"""
from __future__ import annotations

import json
from pathlib import Path

NL = chr(10)


class PathSink:
    """목록처럼 `append` 를 받지만 실제로는 디스크에 흘린다."""

    def __init__(self, out_path):
        self.p = Path(str(out_path) + ".paths.jsonl")
        self.p.parent.mkdir(parents=True, exist_ok=True)
        self.f = self.p.open("w", encoding="utf-8")
        self.n = 0

    def append(self, obj):
        self.f.write(json.dumps(obj, ensure_ascii=False))
        self.f.write(NL)
        self.n += 1

    def close(self):
        if not self.f.closed:
            self.f.close()

    def __len__(self):
        return self.n


def merge_paths(out_path):
    """`{... , "trigger_paths": [ ... ]}` 로 이어 붙인다. **줄 단위 스트리밍.**

    최종 파일의 «형태»는 옛 판과 같다 — 소비자(`39-exit-variants.load_paths`)는
    바뀔 게 없다. **바뀐 것은 만드는 방법뿐이다.**
    """
    out = Path(out_path)
    side = Path(str(out_path) + ".paths.jsonl")
    if not side.exists():
        return 0
    txt = out.read_text(encoding="utf-8").rstrip()
    assert txt.endswith("}"), "출력이 JSON 객체가 아니다"
    head = txt[:-1].rstrip()
    if not head.endswith("{"):
        head += ","
    n = 0
    with out.open("w", encoding="utf-8") as w:
        w.write(head)
        w.write(NL + ' "trigger_paths": [')
        first = True
        with side.open(encoding="utf-8") as r:
            for line in r:
                line = line.strip()
                if not line:
                    continue
                w.write(("" if first else ",") + NL + "  " + line)
                first = False
                n += 1
        w.write(NL + " ]" + NL + "}" + NL)
    side.unlink()
    return n
