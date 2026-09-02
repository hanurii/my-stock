========================================================================================
_runv — **검사하고 «나서» 돌린다** · 대상 `156v-gen-gap.py`
========================================================================================
  ✅ ① 서식(`_fmtcheck`)
  ✅ ② 컴파일
  ✅ ③ 정의 전 사용(모듈 수준)

  ▶ 검사 통과 — 돌린다
========================================================================================
====================================================================================================
156v — 🚨 **154 와 156① 의 «어긋남»을 «네 지점»으로 가른다** · 씨앗 60판
====================================================================================================

Traceback (most recent call last):
  File "C:\Users\hanul\playground\my-stock\research\handoff\scripts\_runv.py", line 166, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "C:\Users\hanul\playground\my-stock\research\handoff\scripts\_runv.py", line 161, in main
    runpy.run_path(str(target), run_name="__main__")
  File "<frozen runpy>", line 287, in run_path
  File "<frozen runpy>", line 98, in _run_module_code
  File "<frozen runpy>", line 88, in _run_code
  File "C:\Users\hanul\playground\my-stock\research\handoff\scripts\156v-gen-gap.py", line 196, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "C:\Users\hanul\playground\my-stock\research\handoff\scripts\156v-gen-gap.py", line 86, in main
    (_a, _b, by2), missing, _ = r91.load_ladder(
                                ^^^^^^^^^^^^^^^^
  File "C:\Users\hanul\playground\my-stock\research\handoff\scripts\91-us-out-of-sample.py", line 156, in load_ladder
    ps = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\hanul\AppData\Local\Programs\Python\Python312\Lib\pathlib.py", line 1028, in read_text
    return f.read()
           ^^^^^^^^
  File "<frozen codecs>", line 322, in decode
MemoryError
