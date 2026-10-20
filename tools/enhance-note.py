#!/usr/bin/env python3
"""노트 HTML에 목차·검색·네비게이션을 주입한다.

  - 왼쪽 고정 목차(넓은 화면) / 오른쪽 슬라이드 패널(좁은 화면). 현재 보는 섹션 자동 표시.
  - 노트 안 검색. 접힌 <details> 안까지 뒤지고, 맞으면 그 섹션을 펼친다.
  - 브레드크럼 · 하단 돌아가기 · 우하단 고정 버튼.

노트를 새 버전으로 교체한 뒤 다시 실행하면 된다. 이전 주입분은 마커로 걷어내고
다시 넣으므로 몇 번을 돌려도 결과가 같다(멱등).

  python3 tools/enhance-note.py engineering-in-biology/cell-adhesion/cytoskeleton-quiz-notes.html
"""
import re
import sys
import pathlib

# 블록별 제거 패턴. "top" 만 앞의 개행까지 먹어야 재실행 때 빈 줄이 쌓이지 않는다.
STRIP = [
    r"<!-- uni:head -->.*?<!-- /uni:head -->\n?",
    r"\n?<!-- uni:top -->.*?<!-- /uni:top -->\n?",
    r"<!-- uni:bottom -->.*?<!-- /uni:bottom -->\n?",
    r"<!-- uni:fab -->.*?<!-- /uni:fab -->\n?",
]

# 구버전(마커 없음) 정리용
STRIP_LEGACY = [
    r"<!-- uni-nav -->\n<style>.*?</style>\n",
    r'<nav class="uni-bc">.*?</nav>\n',
    r'<p class="uni-back">.*?</p>\n',
    r'<a class="uni-fab".*?</a>\n?',
]

HEAD = """<!-- uni:head -->
<style>
/* 브레드크럼 */
.uni-bc{font-size:.78rem;color:var(--mute);margin:0 0 12px;display:flex;flex-wrap:wrap;gap:5px;align-items:center;font-weight:700}
.uni-bc a{color:var(--mute);text-decoration:none;border-bottom:1px solid transparent}
.uni-bc a:hover{color:var(--acc);border-bottom-color:var(--acc)}
.uni-bc .s{opacity:.4}

/* 검색바 */
.uni-search{position:sticky;top:0;z-index:40;background:var(--bg);
  padding:8px 0 10px;margin:0 0 14px;border-bottom:1px solid var(--line);
  display:flex;align-items:center;gap:8px}
.uni-search .box{flex:1;display:flex;align-items:center;gap:8px;min-width:0;
  background:var(--card);border:1px solid var(--line);border-radius:999px;padding:7px 12px}
.uni-search .box:focus-within{border-color:var(--acc)}
.uni-search .box svg{flex:none;width:16px;height:16px;color:var(--mute)}
.uni-search input{flex:1;min-width:0;border:0;outline:0;background:transparent;color:var(--fg);
  font-family:inherit;font-weight:600;font-size:16px}
.uni-search input::placeholder{color:var(--mute);font-weight:500}
.uni-search input::-webkit-search-decoration,.uni-search input::-webkit-search-cancel-button{display:none}
.uni-count{flex:none;font-size:.72rem;font-weight:700;color:var(--mute);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.uni-search .btns{display:none;gap:5px}
.uni-search.has .btns{display:flex}
.uni-search button{flex:none;width:28px;height:28px;padding:0;cursor:pointer;
  background:var(--card);border:1px solid var(--line);border-radius:7px;
  color:var(--mute);font-family:inherit;font-weight:800;font-size:.8rem;line-height:1}
.uni-search button:hover:not(:disabled){color:var(--acc);border-color:var(--acc)}
.uni-search button:disabled{opacity:.35;cursor:default}
mark.uni-hit{background:var(--hl);color:inherit;border-radius:2px;padding:0 1px;scroll-margin-top:92px}
mark.uni-hit.on{background:var(--acc);color:var(--bg)}

/* 목차 — 좁은 화면에서는 오른쪽 슬라이드 패널 */
.uni-toc{display:none;position:fixed;top:0;right:0;bottom:0;width:min(300px,82vw);z-index:60;
  background:var(--card);border-left:1px solid var(--line);box-shadow:-10px 0 30px rgba(0,0,0,.22);
  overflow-y:auto;-webkit-overflow-scrolling:touch;
  padding:20px 12px calc(28px + env(safe-area-inset-bottom,0px))}
.uni-toc.open{display:block}
.uni-toc .hd{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 0 12px;padding:0 6px}
.uni-toc .hd b{font-size:.68rem;letter-spacing:.11em;text-transform:uppercase;color:var(--mute);font-weight:800}
.uni-toc .x{width:26px;height:26px;padding:0;cursor:pointer;background:transparent;border:1px solid var(--line);
  border-radius:7px;color:var(--mute);font-family:inherit;font-weight:800;font-size:.85rem;line-height:1}
.uni-toc a{display:flex;gap:8px;align-items:baseline;padding:7px 8px;border-radius:7px;
  text-decoration:none;color:var(--mute);font-size:.8rem;font-weight:700;line-height:1.35}
.uni-toc a .n{flex:none;min-width:19px;font-size:.62rem;font-weight:800;opacity:.8}
.uni-toc a:hover{background:var(--soft);color:var(--fg)}
.uni-toc a.on{background:var(--soft);color:var(--acc)}
.uni-scrim{display:none;position:fixed;inset:0;background:rgba(0,0,0,.42);z-index:55}
.uni-scrim.on{display:block}

/* 돌아가기 / 고정 버튼 */
.uni-back{margin:28px 0 0;padding-top:16px;border-top:1px solid var(--line);font-size:.86rem;font-weight:700}
.uni-back a{color:var(--mute);text-decoration:none}
.uni-back a:hover{color:var(--acc)}
.uni-fabs{position:fixed;right:14px;bottom:14px;z-index:50;display:flex;gap:8px;
  padding-bottom:env(safe-area-inset-bottom,0px)}
.uni-fabs a,.uni-fabs button{display:inline-flex;align-items:center;gap:6px;cursor:pointer;
  padding:9px 14px;border-radius:999px;background:var(--card);border:1px solid var(--line);
  color:var(--fg);text-decoration:none;font-family:inherit;font-weight:800;font-size:.8rem;line-height:1;
  box-shadow:0 2px 10px rgba(0,0,0,.12)}
.uni-fabs a:hover,.uni-fabs button:hover{color:var(--acc);border-color:var(--acc)}

/* 넓은 화면 — 목차를 본문 왼쪽에 상시 고정 */
@media (min-width:1100px){
  .uni-toc{display:block;position:fixed;left:calc(50% - 530px);top:0;right:auto;bottom:auto;
    width:235px;height:100vh;background:transparent;border:0;box-shadow:none;padding:28px 8px 40px}
  .uni-scrim,.uni-toc .x,.uni-toc-btn{display:none!important}
}
@media print{.uni-fabs,.uni-search,.uni-toc,.uni-scrim{display:none!important}}
</style>
<!-- /uni:head -->
"""

TOP = """<!-- uni:top -->
<nav class="uni-bc">
<a href="../../">홈</a><span class="s">/</span><a href="../">Engineering in Biology</a><span class="s">/</span><a href="./">Cell Adhesion</a>
</nav>
<div class="uni-search">
  <label class="box">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <input type="search" placeholder="노트 안에서 검색 (접힌 내용까지)" autocomplete="off" spellcheck="false" enterkeyhint="search">
    <span class="uni-count"></span>
  </label>
  <span class="btns">
    <button type="button" data-act="prev" title="이전 (Shift+Enter)" aria-label="이전 결과">&#8593;</button>
    <button type="button" data-act="next" title="다음 (Enter)" aria-label="다음 결과">&#8595;</button>
  </span>
</div>
<!-- /uni:top -->
"""

BOTTOM = """<!-- uni:bottom -->
<p class="uni-back"><a href="./">← Cell Adhesion 목록으로</a></p>
<!-- /uni:bottom -->
"""

FAB = """<!-- uni:fab -->
<div class="uni-scrim"></div>
<aside class="uni-toc" aria-label="목차">
  <div class="hd"><b>목차</b><button type="button" class="x" aria-label="목차 닫기">&#10005;</button></div>
  <div class="uni-toc-list"></div>
</aside>
<div class="uni-fabs">
  <button type="button" class="uni-toc-btn" aria-label="목차 열기">&#9776; 목차</button>
  <a href="./" aria-label="Cell Adhesion 목록으로 돌아가기">← 목록</a>
</div>
<script>
(function () {
  var MIN = 2, DEBOUNCE = 120, OFFSET = 72;   // OFFSET: 고정 검색바 높이만큼 띄워서 스크롤
  var root, bar, input, counter, prevBtn, nextBtn;
  var toc, tocList, scrim, tocBtn, links = [], secs = [];
  var hits = [], cur = -1, wasOpen = null, timer = null, ticking = null;

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  /* 부드러운 스크롤이 무시되는 환경이 있다. 움직이지 않으면 즉시 이동으로 떨어뜨린다. */
  function scrollToY(y) {
    if (y < 0) y = 0;
    var start = window.pageYOffset;
    if (Math.abs(y - start) < 2) return;
    try { window.scrollTo({ top: y, behavior: 'smooth' }); }
    catch (e) { window.scrollTo(0, y); return; }
    setTimeout(function () {
      if (Math.abs(window.pageYOffset - start) < 2) window.scrollTo(0, y);
    }, 350);
  }

  /* ---------- 목차 ---------- */

  function buildToc() {
    secs = [].slice.call(root.querySelectorAll('details.sec'));
    for (var i = 0; i < secs.length; i++) {
      var d = secs[i];
      if (!d.id) d.id = 'uni-sec-' + i;
      var sum = d.querySelector('summary');
      if (!sum) continue;
      var nEl = sum.querySelector('.n');
      var n = nEl ? nEl.textContent.trim() : '';
      var label = sum.textContent.trim();
      if (n && label.indexOf(n) === 0) label = label.slice(n.length).trim();

      var a = document.createElement('a');
      a.href = '#' + d.id;
      a.setAttribute('data-target', d.id);
      var ns = document.createElement('span');
      ns.className = 'n';
      ns.textContent = n;
      var ls = document.createElement('span');
      ls.textContent = label;
      a.appendChild(ns);
      a.appendChild(ls);
      tocList.appendChild(a);
      links.push(a);
    }
  }

  function jump(id) {
    var d = document.getElementById(id);
    if (!d) return;
    d.open = true;
    closePanel();
    scrollToY(d.getBoundingClientRect().top + window.pageYOffset - OFFSET);
  }

  function setActive(a) {
    for (var j = 0; j < links.length; j++) links[j].classList.toggle('on', links[j] === a);
  }

  /* 지금 보고 있는 섹션을 목차에 표시 */
  function spy() {
    ticking = null;
    if (!secs.length) return;
    var y = window.pageYOffset + OFFSET + 12, idx = 0;
    for (var i = 0; i < secs.length; i++) {
      if (secs[i].getBoundingClientRect().top + window.pageYOffset <= y) idx = i;
      else break;
    }
    setActive(links[idx]);
  }

  /* 타이머로 솎아낸다. requestAnimationFrame 은 탭이 숨겨지면 아예 돌지 않는다. */
  function onScroll() {
    if (ticking) return;
    ticking = setTimeout(spy, 80);
  }

  function openPanel() { toc.classList.add('open'); scrim.classList.add('on'); }
  function closePanel() { toc.classList.remove('open'); scrim.classList.remove('on'); }

  /* ---------- 검색 ---------- */

  function allDetails() { return root.querySelectorAll('details'); }

  function snapshotOpen() {
    if (wasOpen) return;
    wasOpen = [];
    var d = allDetails();
    for (var i = 0; i < d.length; i++) wasOpen.push(d[i].open);
  }

  function restoreOpen() {
    if (!wasOpen) return;
    var d = allDetails();
    for (var i = 0; i < d.length && i < wasOpen.length; i++) d[i].open = wasOpen[i];
    wasOpen = null;
  }

  function unmark() {
    var ms = root.querySelectorAll('mark.uni-hit');
    for (var i = 0; i < ms.length; i++) {
      var m = ms[i], p = m.parentNode;
      if (!p) continue;
      p.replaceChild(document.createTextNode(m.textContent), m);
      p.normalize();
    }
  }

  /* <style>, <script>, SVG 안은 건드리지 않는다. SVG에 <mark>를 넣으면 도형이 깨진다. */
  function skippable(el) {
    while (el && el !== root) {
      var n = el.nodeName;
      if (n === 'SCRIPT' || n === 'STYLE' || n === 'svg') return true;
      if (el.classList && (el.classList.contains('uni-search') || el.classList.contains('uni-toc'))) return true;
      el = el.parentNode;
    }
    return false;
  }

  function highlight(node, needle, len) {
    var text = node.nodeValue, low = text.toLowerCase();
    var frag = document.createDocumentFragment(), i = 0, p;
    while ((p = low.indexOf(needle, i)) >= 0) {
      if (p > i) frag.appendChild(document.createTextNode(text.slice(i, p)));
      var m = document.createElement('mark');
      m.className = 'uni-hit';
      m.textContent = text.slice(p, p + len);
      frag.appendChild(m);
      i = p + len;
    }
    if (i < text.length) frag.appendChild(document.createTextNode(text.slice(i)));
    node.parentNode.replaceChild(frag, node);
  }

  function go(dir) {
    if (!hits.length) return;
    if (cur >= 0 && hits[cur]) hits[cur].classList.remove('on');
    cur = (cur + dir + hits.length) % hits.length;
    var h = hits[cur];
    h.classList.add('on');
    scrollToY(h.getBoundingClientRect().top + window.pageYOffset - window.innerHeight / 2);
    counter.textContent = (cur + 1) + ' / ' + hits.length;
  }

  function run() {
    var q = input.value.trim();
    unmark();
    hits = []; cur = -1;
    prevBtn.disabled = nextBtn.disabled = true;

    if (q.length < MIN) {
      restoreOpen();
      counter.textContent = q.length ? '2자 이상' : '';
      bar.classList.remove('has');
      return;
    }

    snapshotOpen();
    var d = allDetails();
    for (var i = 0; i < d.length; i++) d[i].open = true;   // 접힌 내용도 검색 대상

    var needle = q.toLowerCase();
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        if (!node.nodeValue) return NodeFilter.FILTER_REJECT;
        if (node.nodeValue.toLowerCase().indexOf(needle) < 0) return NodeFilter.FILTER_REJECT;
        if (skippable(node.parentNode)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var targets = [], n;
    while ((n = walker.nextNode())) targets.push(n);   // 먼저 다 모으고 나서 DOM을 바꾼다
    for (var j = 0; j < targets.length; j++) highlight(targets[j], needle, q.length);

    hits = [].slice.call(root.querySelectorAll('mark.uni-hit'));
    bar.classList.add('has');

    if (hits.length) {
      prevBtn.disabled = nextBtn.disabled = false;
      go(1);
    } else {
      counter.textContent = '결과 없음';
      restoreOpen();
    }
  }

  /* ---------- 시작 ---------- */

  ready(function () {
    root = document.querySelector('.wrap');
    bar = document.querySelector('.uni-search');
    toc = document.querySelector('.uni-toc');
    if (!root || !bar || !toc) return;

    input = bar.querySelector('input');
    counter = bar.querySelector('.uni-count');
    prevBtn = bar.querySelector('[data-act="prev"]');
    nextBtn = bar.querySelector('[data-act="next"]');
    tocList = toc.querySelector('.uni-toc-list');
    scrim = document.querySelector('.uni-scrim');
    tocBtn = document.querySelector('.uni-toc-btn');

    buildToc();
    spy();

    tocList.addEventListener('click', function (e) {
      var a = e.target.closest ? e.target.closest('a[data-target]') : null;
      if (!a) return;
      e.preventDefault();
      setActive(a);
      jump(a.getAttribute('data-target'));
    });
    tocBtn.addEventListener('click', openPanel);
    toc.querySelector('.x').addEventListener('click', closePanel);
    scrim.addEventListener('click', closePanel);
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);

    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(run, DEBOUNCE);
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); go(e.shiftKey ? -1 : 1); }
      else if (e.key === 'Escape') { input.value = ''; run(); input.blur(); }
    });
    prevBtn.addEventListener('click', function () { go(-1); });
    nextBtn.addEventListener('click', function () { go(1); });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { closePanel(); return; }
      if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
      var a = document.activeElement;
      if (a && (a === input || a.tagName === 'INPUT' || a.tagName === 'TEXTAREA' || a.isContentEditable)) return;
      e.preventDefault();
      input.focus();
      input.select();
    });
  });
})();
</script>
<!-- /uni:fab -->
"""


def strip_previous(s):
    for pat in STRIP + STRIP_LEGACY:
        s = re.sub(pat, "", s, flags=re.S)
    return s


def main(path):
    p = pathlib.Path(path)
    s = p.read_text(encoding="utf-8")
    s = strip_previous(s)

    anchor = '<div class="wrap">'
    if anchor not in s:
        print("오류: '%s' 를 찾을 수 없음 — 노트 구조가 바뀌었다" % anchor, file=sys.stderr)
        return 1
    s = s.replace(anchor, HEAD + anchor + "\n" + TOP, 1)

    i = s.rstrip().rfind("</div>")
    if i == -1:
        print("오류: 닫는 </div> 를 찾을 수 없음", file=sys.stderr)
        return 1
    s = s[:i] + BOTTOM + s[i:].rstrip() + "\n" + FAB

    p.write_text(s, encoding="utf-8")
    print("적용 완료: %s" % path)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
