#!/usr/bin/env python3
"""Turn a note HTML into a tabbed note: one tab per lecture.

  - Lecture tabs. Sections are grouped by their L-badge and shown one group at a
    time. Nothing collapses: inside a tab every section is already open.
    Wide screens get a fixed list on the left, narrow screens a scrollable strip.
  - Search across the whole note, including tabs that are not currently shown;
    jumping to a hit switches to its tab.
  - Breadcrumb back to the folder.

Re-run after replacing the note with a newer version. Previous injections are
stripped by marker first, so the result is the same no matter how often it runs.

  python3 tools/enhance-note.py engineering-in-biology/cell-adhesion/cytoskeleton-quiz-notes.html
"""
import re
import sys
import pathlib

# Removal patterns. Only "top" eats the preceding newline, otherwise a blank
# line accumulates on every re-run.
STRIP = [
    r"<!-- uni:head -->.*?<!-- /uni:head -->\n?",
    r"\n?<!-- uni:top -->.*?<!-- /uni:top -->\n?",
    r"<!-- uni:foot -->.*?<!-- /uni:foot -->\n?",
    # retired blocks from earlier versions
    r"<!-- uni:bottom -->.*?<!-- /uni:bottom -->\n?",
    r"<!-- uni:fab -->.*?<!-- /uni:fab -->\n?",
    r"<!-- uni-nav -->\n<style>.*?</style>\n",
    r'<nav class="uni-bc">.*?</nav>\n',
    r'<p class="uni-back">.*?</p>\n',
    r'<a class="uni-fab".*?</a>\n?',
]

HEAD = """<!-- uni:head -->
<style>
/* Breadcrumb */
.uni-bc{font-size:.78rem;color:var(--mute);margin:0 0 10px;display:flex;flex-wrap:wrap;gap:5px;align-items:center;font-weight:700}
.uni-bc a{color:var(--mute);text-decoration:none;border-bottom:1px solid transparent}
.uni-bc a:hover{color:var(--acc);border-bottom-color:var(--acc)}
.uni-bc .s{opacity:.4}

/* Sticky header: search + lecture tabs */
.uni-top{position:sticky;top:0;z-index:40;background:var(--bg);
  padding:8px 0 9px;margin:0 0 16px;border-bottom:1px solid var(--line)}
.uni-search{display:flex;align-items:center;gap:8px}
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
mark.uni-hit{background:var(--hl);color:inherit;border-radius:2px;padding:0 1px}
mark.uni-hit.on{background:var(--acc);color:var(--bg)}

/* Lecture tabs — narrow screens: a scrollable strip */
.uni-nav{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch;
  margin:9px 0 0;padding:1px}
.uni-nav::-webkit-scrollbar{display:none}
.uni-nav a{flex:none;display:block;padding:7px 13px;border-radius:999px;max-width:16ch;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  background:var(--card);border:1px solid var(--line);color:var(--mute);
  text-decoration:none;font-weight:800;font-size:.8rem;line-height:1.25}
.uni-nav a:hover{color:var(--fg)}
.uni-nav a.on{background:var(--acc);border-color:var(--acc);color:var(--bg)}
.uni-nav a .t{display:none}

/* One tab's worth of sections */
.uni-pane{display:none}
.uni-pane.on{display:block}

/* Nothing collapses any more: the section header is just a header. The quiz
   cards inside "Test yourself" keep their own tap-to-reveal. */
details.sec>summary{cursor:default;pointer-events:none}
details.sec>summary::after{content:""!important;display:none}

/* Wide screens — tabs become a fixed column to the left of the body */
@media (min-width:1100px){
  .uni-nav{position:fixed;left:calc(50% - 530px);top:26px;width:235px;
    max-height:calc(100vh - 52px);overflow-y:auto;display:block;margin:0;padding:0 2px}
  .uni-nav a{display:block;width:100%;max-width:none;white-space:normal;overflow:visible;
    margin:0 0 5px;padding:9px 12px;border-radius:9px}
  .uni-nav a .n{font-size:.72rem}
  .uni-nav a .t{display:block;margin-top:3px;font-size:.71rem;font-weight:700;line-height:1.35;opacity:.75}
  .uni-nav a.on .t{opacity:.95}
}
@media print{.uni-top,.uni-nav{display:none!important}.uni-pane{display:block!important}}
</style>
<!-- /uni:head -->
"""

TOP = """<!-- uni:top -->
<nav class="uni-bc">
<a href="../../">Home</a><span class="s">/</span><a href="../">Engineering in Biology</a><span class="s">/</span><a href="./">Cell Adhesion</a>
</nav>
<div class="uni-top">
  <div class="uni-search">
    <label class="box">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input type="search" placeholder="Search this note, every tab included" autocomplete="off" spellcheck="false" enterkeyhint="search">
      <span class="uni-count"></span>
    </label>
    <span class="btns">
      <button type="button" data-act="prev" title="Previous (Shift+Enter)" aria-label="Previous match">&#8593;</button>
      <button type="button" data-act="next" title="Next (Enter)" aria-label="Next match">&#8595;</button>
    </span>
  </div>
  <nav class="uni-nav" aria-label="Lectures"></nav>
</div>
<!-- /uni:top -->
"""

FOOT = """<!-- uni:foot -->
<script>
(function () {
  var MIN = 2, DEBOUNCE = 120;
  var root, head, bar, input, counter, prevBtn, nextBtn, nav;
  var groups = [], links = [], active = -1;
  var hits = [], cur = -1, wasOpen = null, timer = null;

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  /* Some environments ignore smooth scrolling. If nothing moved, jump instantly. */
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

  function headroom() { return (head ? head.offsetHeight : 0) + 12; }

  /* ---------- Tabs ---------- */

  function titleOf(sec) {
    var sum = sec.querySelector('summary');
    if (!sum) return '';
    var badge = sum.querySelector('.n');
    var t = sum.textContent.trim();
    if (badge) {
      var b = badge.textContent.trim();
      if (b && t.indexOf(b) === 0) t = t.slice(b.length).trim();
    }
    return t;
  }

  /* Consecutive sections sharing an L-badge become one tab. */
  function buildTabs() {
    var secs = [].slice.call(root.querySelectorAll('details.sec'));
    if (!secs.length) return;

    for (var i = 0; i < secs.length; i++) {
      var sum = secs[i].querySelector('summary');
      var nEl = sum ? sum.querySelector('.n') : null;
      var badge = nEl ? nEl.textContent.trim() : '';
      var g = groups[groups.length - 1];
      if (!g || g.badge !== badge) {
        g = { badge: badge, items: [], titles: [] };
        groups.push(g);
      }
      g.items.push(secs[i]);
      g.titles.push(titleOf(secs[i]));
    }

    for (var k = 0; k < groups.length; k++) {
      var gr = groups[k];
      var pane = document.createElement('div');
      pane.className = 'uni-pane';
      gr.items[0].parentNode.insertBefore(pane, gr.items[0]);
      for (var j = 0; j < gr.items.length; j++) {
        pane.appendChild(gr.items[j]);
        gr.items[j].open = true;          // never collapsed inside a tab
      }
      gr.pane = pane;
      gr.key = /^L\\d+$/.test(gr.badge) ? gr.badge : 'tab' + k;

      var a = document.createElement('a');
      a.href = '#' + gr.key;
      a.setAttribute('data-i', k);
      /* A lecture badge is label enough; anything else borrows its first title. */
      var chip = /^L\\d+$/.test(gr.badge)
        ? gr.badge
        : (gr.badge + ' ' + gr.titles[0].replace(/\\s*\\(.*\\)\\s*$/, '')).trim();
      var ns = document.createElement('span');
      ns.className = 'n';
      ns.textContent = chip;
      var ts = document.createElement('span');
      ts.className = 't';
      ts.textContent = gr.titles.join(' · ');
      a.appendChild(ns);
      a.appendChild(ts);
      a.title = gr.titles.join(' · ');
      nav.appendChild(a);
      links.push(a);
    }
  }

  function activate(i, keepScroll) {
    if (i < 0 || i >= groups.length || i === active) {
      if (i === active && !keepScroll) scrollToY(0);
      return;
    }
    active = i;
    for (var k = 0; k < groups.length; k++) {
      groups[k].pane.classList.toggle('on', k === i);
      links[k].classList.toggle('on', k === i);
      if (k === i) links[k].setAttribute('aria-current', 'true');
      else links[k].removeAttribute('aria-current');
    }
    try { links[i].scrollIntoView({ block: 'nearest', inline: 'center' }); } catch (e) {}
    if (history.replaceState) history.replaceState(null, '', '#' + groups[i].key);
    if (!keepScroll) scrollToY(0);
  }

  function indexOfKey(key) {
    for (var i = 0; i < groups.length; i++) if (groups[i].key === key) return i;
    return -1;
  }

  function paneIndexOf(node) {
    while (node && node !== root) {
      if (node.classList && node.classList.contains('uni-pane')) {
        for (var i = 0; i < groups.length; i++) if (groups[i].pane === node) return i;
        return -1;
      }
      node = node.parentNode;
    }
    return -1;
  }

  /* ---------- Search ---------- */

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

  /* Leave <style>, <script> and SVG alone: a <mark> inside SVG breaks the drawing. */
  function skippable(el) {
    while (el && el !== root) {
      var n = el.nodeName;
      if (n === 'SCRIPT' || n === 'STYLE' || n === 'svg') return true;
      if (el.classList && el.classList.contains('uni-top')) return true;
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
    var pi = paneIndexOf(h);
    if (pi >= 0 && pi !== active) activate(pi, true);   // hit lives in another tab
    counter.textContent = (cur + 1) + ' / ' + hits.length;
    scrollToY(h.getBoundingClientRect().top + window.pageYOffset - window.innerHeight / 2);
  }

  function run() {
    var q = input.value.trim();
    unmark();
    hits = []; cur = -1;
    prevBtn.disabled = nextBtn.disabled = true;

    if (q.length < MIN) {
      restoreOpen();
      counter.textContent = q.length ? 'Type 2+ characters' : '';
      bar.classList.remove('has');
      return;
    }

    snapshotOpen();
    var d = allDetails();
    for (var i = 0; i < d.length; i++) d[i].open = true;   // reveal quiz answers too

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
    while ((n = walker.nextNode())) targets.push(n);   // collect every node first, then mutate
    for (var j = 0; j < targets.length; j++) highlight(targets[j], needle, q.length);

    hits = [].slice.call(root.querySelectorAll('mark.uni-hit'));
    bar.classList.add('has');

    if (hits.length) {
      prevBtn.disabled = nextBtn.disabled = false;
      go(1);
    } else {
      counter.textContent = 'No matches';
      restoreOpen();
    }
  }

  /* ---------- Boot ---------- */

  ready(function () {
    root = document.querySelector('.wrap');
    head = document.querySelector('.uni-top');
    bar = document.querySelector('.uni-search');
    nav = document.querySelector('.uni-nav');
    if (!root || !head || !bar || !nav) return;

    input = bar.querySelector('input');
    counter = bar.querySelector('.uni-count');
    prevBtn = bar.querySelector('[data-act="prev"]');
    nextBtn = bar.querySelector('[data-act="next"]');

    buildTabs();
    if (!groups.length) return;

    var start = indexOfKey((location.hash || '').replace(/^#/, ''));
    activate(start >= 0 ? start : 0, true);

    nav.addEventListener('click', function (e) {
      var a = e.target.closest ? e.target.closest('a[data-i]') : null;
      if (!a) return;
      e.preventDefault();
      activate(parseInt(a.getAttribute('data-i'), 10), false);
    });

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
      var a = document.activeElement;
      var typing = a && (a === input || a.tagName === 'INPUT' || a.tagName === 'TEXTAREA' || a.isContentEditable);
      if (e.key === '/' && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault(); input.focus(); input.select(); return;
      }
      /* Arrow keys step between lectures when you are not typing. */
      if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === 'ArrowRight') { e.preventDefault(); activate(Math.min(active + 1, groups.length - 1), false); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); activate(Math.max(active - 1, 0), false); }
    });

    window.addEventListener('hashchange', function () {
      var i = indexOfKey((location.hash || '').replace(/^#/, ''));
      if (i >= 0) activate(i, false);
    });
  });
})();
</script>
<!-- /uni:foot -->
"""


def strip_previous(s):
    for pat in STRIP:
        s = re.sub(pat, "", s, flags=re.S)
    return s


def main(path):
    p = pathlib.Path(path)
    s = p.read_text(encoding="utf-8")
    s = strip_previous(s)

    anchor = '<div class="wrap">'
    if anchor not in s:
        print("error: %s not found - the note structure changed" % anchor, file=sys.stderr)
        return 1
    s = s.replace(anchor, HEAD + anchor + "\n" + TOP, 1)

    i = s.rstrip().rfind("</div>")
    if i == -1:
        print("error: closing </div> not found", file=sys.stderr)
        return 1
    s = s[:i] + s[i:].rstrip() + "\n" + FOOT

    p.write_text(s, encoding="utf-8")
    print("applied: %s" % path)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
