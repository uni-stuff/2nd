#!/usr/bin/env python3
"""노트 HTML에 상단 브레드크럼 / 하단 돌아가기 / 고정 버튼을 넣는다.

노트를 새 버전으로 교체한 뒤 다시 실행하면 된다. 이미 들어가 있으면 아무것도 하지 않는다.

  python3 tools/add-nav.py engineering-in-biology/cell-adhesion/cytoskeleton-quiz-notes.html
"""
import sys, pathlib

MARK = "<!-- uni-nav -->"

STYLE = """<!-- uni-nav -->
<style>
.uni-bc{font-size:.78rem;color:var(--mute);margin:0 0 14px;display:flex;flex-wrap:wrap;gap:5px;align-items:center;font-weight:700}
.uni-bc a{color:var(--mute);text-decoration:none;border-bottom:1px solid transparent}
.uni-bc a:hover{color:var(--acc);border-bottom-color:var(--acc)}
.uni-bc .s{opacity:.4}
.uni-back{margin:28px 0 0;padding-top:16px;border-top:1px solid var(--line);font-size:.86rem;font-weight:700}
.uni-back a{color:var(--mute);text-decoration:none}
.uni-back a:hover{color:var(--acc)}
.uni-fab{position:fixed;right:14px;bottom:14px;z-index:50;display:inline-flex;align-items:center;gap:6px;
  padding:9px 14px;border-radius:999px;background:var(--card);border:1px solid var(--line);
  color:var(--fg);text-decoration:none;font-weight:800;font-size:.8rem;
  box-shadow:0 2px 10px rgba(0,0,0,.12);
  padding-bottom:calc(9px + env(safe-area-inset-bottom,0px))}
.uni-fab:hover{color:var(--acc);border-color:var(--acc)}
@media print{.uni-fab{display:none}}
</style>
"""

BC = """<nav class="uni-bc">
<a href="../../">홈</a><span class="s">/</span><a href="../">Engineering in Biology</a><span class="s">/</span><a href="./">Cell Adhesion</a>
</nav>
"""

BACK = """<p class="uni-back"><a href="./">← Cell Adhesion 목록으로</a></p>
"""

FAB = """<a class="uni-fab" href="./" aria-label="Cell Adhesion 목록으로 돌아가기">← 목록</a>
"""


def main(path):
    p = pathlib.Path(path)
    s = p.read_text(encoding="utf-8")
    if MARK in s:
        print(f"이미 적용됨: {path}")
        return 0

    anchor = '<div class="wrap">'
    if anchor not in s:
        print(f"오류: '{anchor}' 를 찾을 수 없음 — 노트 구조가 바뀌었다", file=sys.stderr)
        return 1

    # <style> 는 wrap 앞에, 브레드크럼은 wrap 바로 뒤에
    s = s.replace(anchor, STYLE + anchor + "\n" + BC, 1)

    # 마지막 </div> (wrap 닫기) 앞에 돌아가기 링크, 그 뒤에 고정 버튼
    i = s.rstrip().rfind("</div>")
    if i == -1:
        print("오류: 닫는 </div> 를 찾을 수 없음", file=sys.stderr)
        return 1
    s = s[:i] + BACK + s[i:].rstrip() + "\n" + FAB

    p.write_text(s, encoding="utf-8")
    print(f"적용 완료: {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
