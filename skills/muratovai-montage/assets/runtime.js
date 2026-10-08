// muratovai-montage runtime helpers. Deterministic: only layout measurement at build time and timeline tweens.
// The composition's build() creates `window.TL` before calling these.
function fit(sel, maxW, minFontPx) {
  document.querySelectorAll(sel).forEach(function (el) {
    el.style.whiteSpace = 'nowrap';
    var fs = parseFloat(getComputedStyle(el).fontSize), guard = 0;
    // children may carry their own font-size (mix captions): scale the whole block instead
    if (el.scrollWidth > maxW) {
      var k = maxW / el.scrollWidth;
      if (el.children.length && el.querySelector('.serif,.sans')) {
        el.querySelectorAll('.serif,.sans').forEach(function (c) { c.style.fontSize = (parseFloat(getComputedStyle(c).fontSize) * k * 0.98) + 'px'; });
      } else {
        el.style.fontSize = (fs * k * 0.98) + 'px';
      }
    }
    while (el.scrollWidth > maxW && guard++ < 30) { fs = parseFloat(getComputedStyle(el).fontSize) * 0.95; el.style.fontSize = fs + 'px'; }
    if (minFontPx) {
      var nodes = [el].concat(Array.prototype.slice.call(el.querySelectorAll('.serif,.sans,.ln')));
      var smallest = Math.min.apply(null, nodes.map(function (node) { return parseFloat(getComputedStyle(node).fontSize); }));
      if (smallest < minFontPx || el.scrollWidth > maxW) {
        throw new Error('Caption too small or clipped after font layout: ' + sel + ' (' + smallest.toFixed(1) + 'px)');
      }
    }
  });
}
function wrapChars(node) {
  var out = [];
  Array.prototype.slice.call(node.childNodes).forEach(function (c) {
    if (c.nodeType === 3) {
      var frag = document.createDocumentFragment();
      c.textContent.split('').forEach(function (ch) {
        var s = document.createElement('span'); s.className = 'ch'; s.textContent = ch; frag.appendChild(s); out.push(s);
      });
      node.replaceChild(frag, c);
    } else if (c.nodeType === 1 && !c.classList.contains('mk')) {
      out = out.concat(wrapChars(c));
    }
  });
  return out;
}
function typeOn(sel, t, cps) {
  var el = document.querySelector(sel); if (!el) return;
  var chars = wrapChars(el);
  window.TL.fromTo(chars, { opacity: 0 }, { opacity: 1, duration: 0.01, stagger: 1 / (cps || 26), ease: 'none' }, t);
}

// Glyph-noise "decode": each character scrambles through random glyphs (in the accent colour) and resolves left to right.
// Deterministic for seek-based rendering: the glyph shown depends only on (char index, frame step).
function decode(sel, t, dur, glyphs) {
  var el = document.querySelector(sel); if (!el) return;
  var chars = wrapChars(el), finals = chars.map(function (c) { return c.textContent; }), n = chars.length;
  var G = glyphs || '#%&*+=<>/|{}[]01ABCDEFXYZ$@', proxy = { p: 0 };
  function h(i, k) { var x = Math.sin(i * 12.9898 + k * 78.233) * 43758.5453; return x - Math.floor(x); }
  function render(p) {
    var step = Math.floor(p * dur * 30);
    for (var i = 0; i < n; i++) {
      if (finals[i] === ' ') continue;
      if (p >= (i + 1) / n) { chars[i].textContent = finals[i]; chars[i].style.color = ''; }
      else { chars[i].textContent = G.charAt(Math.floor(h(i, step) * G.length)); chars[i].style.color = 'var(--accent)'; }
    }
  }
  render(0);
  window.TL.fromTo(proxy, { p: 0 }, { p: 1, duration: dur, ease: 'none', onUpdate: function () { render(proxy.p); },
    onComplete: function () { render(1); }, onReverseComplete: function () { render(0); } }, t);
}

// gfx "ui" focus: offset of an item's centre from the screen's centre (layout only, no transforms), for a zoom onto it
function focusXY(scrSel, elSel) {
  var s = document.querySelector(scrSel), e = document.querySelector(elSel);
  if (!s || !e) return { dx: 0, dy: 0 };
  return { dx: e.offsetLeft + e.offsetWidth / 2 - s.offsetWidth / 2, dy: e.offsetTop + e.offsetHeight / 2 - s.offsetHeight / 2 };
}
