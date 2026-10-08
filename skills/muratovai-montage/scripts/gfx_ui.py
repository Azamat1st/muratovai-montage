"""Dark app-screen mock-ups (gfx "ui") and the comment → notification CTA (gfx "comment") for build.py.

ui: a column of interface items on a dark screen: search (the text types on and ends on its word), row, profile, stat
(a rolling number), ring (a chart that draws), toggle, button, text, grid. `taps` press an item on its word with a white ring,
`focus` dims the other items, outlines the named one and can zoom the screen onto it. On a face beat the column is a dark
glass card centred at height `y` (0–1 of the frame), drawn above the speaker.
comment: a comment box over the speaker types the CTA keyword so that it ends on the spoken keyword, then turns into an
Instagram notification that "delivers" the reward.
build.py passes its helpers in `h` (esc, rgba, odometer, rise) so this module never imports build.py.
"""
import json

H = 1920
RING_C = 339.29          # circumference of the r=54 ring in its 120-unit viewBox
TYPE_CPS_MIN_DUR = 0.3   # the shortest typing, s
TYPE_MAX_DUR = 1.2       # the longest typing, s
CTA_LEAD = 0.45          # the comment box shows this long before the typing starts, s
NOTIFY_AFTER = 0.55      # the notification replaces the box this long after the keyword, s
NOTIFY_MIN_GAP = 0.3     # ...and never sooner than this, whatever the beat's length: type, send, then the notification, s
NOTIFY_TAIL = 0.3        # the notification stays at least this long before the beat ends, s


def type_on(ctx, sel, text, done, t_min):
    """typeOn so that the last character lands on `done` (never before t_min); returns the start time"""
    n = max(1, len(text)); dur = min(TYPE_MAX_DUR, max(TYPE_CPS_MIN_DUR, 0.06 * n))
    start = max(t_min, done - dur); cps = n / max(0.05, done - start)
    ctx.add(f"typeOn('{sel}',{start:.3f},{cps:.2f});"); ctx.fx(start, "typing", dur=max(0.05, done - start))
    return start


# ---------------------------------------------------------------- ui items
def _search(ctx, b, it, iid, h):
    text = str(it.get("text", ""))
    if it.get("done") is not None or it.get("t") is not None:
        done = ctx.t(it["done"], b) if it.get("done") is not None else ctx.t(it["t"], b) + min(TYPE_MAX_DUR, max(0.3, 0.06 * len(text)))
        type_on(ctx, f"#{iid}x", text, done, b["_t0"])
    return f'<div class="ui-search"><i class="ui-mag"></i><span id="{iid}x" class="ui-q">{h["esc"](text)}</span></div>'


def _avatar(ctx, it, cls, h):
    if it.get("avatar"): return f'<div class="{cls}" style="background-image:url({ctx.img(it["avatar"])})"></div>'
    letter = h["esc"](str(it.get("title") or it.get("name") or "?")[:1].upper())
    return f'<div class="{cls}" style="background:{it.get("color", "#2c2c2e")}">{letter}</div>'


MARKS = {"win": '<path d="M6 12.5l4 4 8-9"/>', "lose": '<path d="M7 7l10 10M17 7L7 17"/>'}   # a green check, a red cross
MARK_SFX = {"win": "chime", "lose": "error"}


def _mark(ctx, b, it, iid):
    """the verdict badge on the right of a row: shown from the start, or popping in at mark_t"""
    kind = it.get("mark")
    if not kind: return ""
    if kind not in MARKS: raise ValueError(f"beat {b['_i']}: row mark {kind!r} — use one of {', '.join(MARKS)}")
    if it.get("mark_t") is not None:
        t = ctx.t(it["mark_t"], b); ctx.fx(t, MARK_SFX[kind])
        ctx.add(f"tl.fromTo('#{iid}mk',{{scale:0,opacity:0}},{{scale:1,opacity:1,duration:0.3,ease:'back.out(2.2)'}},{t:.3f});")
    return f'<i id="{iid}mk" class="ui-mk {kind}"><svg viewBox="0 0 24 24">{MARKS[kind]}</svg></i>'


def _row(ctx, b, it, iid, h):
    e = h["esc"]; sub = f'<span>{e(it["sub"])}</span>' if it.get("sub") else ""
    right = f'<em>{e(it["right"])}</em>' if it.get("right") else ""
    return (f'<div class="ui-row">{_avatar(ctx, it, "ui-av", h)}<div class="ui-rt"><b>{e(it.get("title", ""))}</b>{sub}</div>'
            f'{right}{_mark(ctx, b, it, iid)}</div>')


def _profile(ctx, b, it, iid, h):
    e = h["esc"]
    stats = "".join(f'<div><b>{e(v)}</b><span>{e(lab)}</span></div>' for v, lab in it.get("stats", []))
    bio = "".join(f"<p>{e(x)}</p>" for x in it.get("bio", []))
    link = f'<p class="ui-link">{e(it["link"])}</p>' if it.get("link") else ""
    handle = f'<span class="ui-hd">@{e(it["handle"])}</span>' if it.get("handle") else ""
    return (f'<div class="ui-prof"><div class="ui-ph">{_avatar(ctx, it, "ui-pav", h)}<div class="ui-st">{stats}</div></div>'
            f'<b class="ui-nm">{e(it.get("name", ""))}</b>{handle}{bio}{link}</div>')


def _stat(ctx, b, it, iid, h):
    e = h["esc"]; size = it.get("size", 150); text = str(it.get("value", "")); sid = ""
    if it.get("t") is not None:   # number and label stay hidden until the roll: the odometer's resting digits mean nothing
        t = ctx.t(it["t"], b); sid = f' id="{iid}n"'; ctx.add(f"tl.fromTo('#{iid}n',{{opacity:0}},{{opacity:1,duration:0.12}},{t:.3f});")
        num = h["odometer"](ctx, f"{iid}n", text, t, it.get("dur", 1.2), size, "800 1em Inter, sans-serif")
    else:
        num = f'<span style="font:800 {size}px/1.05 Inter,sans-serif">{e(text)}</span>'
    lab = f'<div class="ui-sl">{e(it["label"])}</div>' if it.get("label") else ""
    return f'<div{sid} class="ui-stat" style="color:{it.get("color", "#fff")}">{num}{lab}</div>'


def _ring(ctx, b, it, iid, h):
    e = h["esc"]; v = max(0.0, min(1.0, float(it.get("value", 0.8)))); size = it.get("size", 360)
    end = RING_C * (1 - v); off = end
    if it.get("t") is not None:
        t = ctx.t(it["t"], b); off = RING_C
        ctx.add(f"tl.fromTo('#{iid}arc',{{attr:{{'stroke-dashoffset':{RING_C}}}}},{{attr:{{'stroke-dashoffset':{end:.2f}}},duration:0.9,ease:'power2.out'}},{t:.3f});")
        ctx.fx(t, "count")
    lab = f'<span>{e(it["label"])}</span>' if it.get("label") else ""
    return (f'<div class="ui-ring" style="width:{size}px;height:{size}px"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="54" class="bgc"/>'
            f'<circle id="{iid}arc" cx="60" cy="60" r="54" class="fgc" style="stroke:{it.get("color", ctx.accent)}" '
            f'stroke-dasharray="{RING_C}" stroke-dashoffset="{off:.2f}"/></svg><div class="ui-rc"><b>{e(it.get("text", f"{round(v * 100)}%"))}</b>{lab}</div></div>')


def _toggle(ctx, b, it, iid, h):
    if it.get("on") is not None:
        t = ctx.t(it["on"], b)
        ctx.add(f"tl.fromTo('#{iid}sw',{{backgroundColor:'#3a3a3c'}},{{backgroundColor:'#34C759',duration:0.18}},{t:.3f});")
        ctx.add(f"tl.fromTo('#{iid}kn',{{x:0}},{{x:62,duration:0.18,ease:'power2.out'}},{t:.3f});"); ctx.fx(t, "toggle")
    return f'<div class="ui-tg"><span>{h["esc"](it.get("label", ""))}</span><i id="{iid}sw" class="ui-sw"><b id="{iid}kn"></b></i></div>'


def _button(ctx, b, it, iid, h):
    return f'<div id="{iid}b" class="ui-btn" style="background:{it.get("color", "#2c2c2e")}">{h["esc"](it.get("label", ""))}</div>'


def _text(ctx, b, it, iid, h):
    return (f'<div class="ui-txt" style="font-size:{it.get("size", 44)}px;color:{it.get("color", "#fff")};'
            f'text-align:{it.get("align", "left")}">{h["esc"](it.get("text", ""))}</div>')


def _grid(ctx, b, it, iid, h):
    views, srcs, cells = it.get("views", []), it.get("srcs", []), []
    for k in range(int(it.get("n", 9))):
        bg = f' style="background-image:url({ctx.img(srcs[k])})"' if k < len(srcs) else ""
        lab = f'<span>&#9654; {h["esc"](views[k])}</span>' if k < len(views) else ""
        cells.append(f"<i{bg}>{lab}</i>")
    return f'<div class="ui-grid">{"".join(cells)}</div>'


RENDER = dict(search=_search, row=_row, profile=_profile, stat=_stat, ring=_ring, toggle=_toggle, button=_button, text=_text, grid=_grid)


# ---------------------------------------------------------------- taps and focus
def _item_index(b, k, n, what):
    if not isinstance(k, int) or not 0 <= k < n: raise ValueError(f"beat {b['_i']}: {what} at={k!r} — no such ui item (0..{n - 1})")
    return k


def _taps(ctx, b, g, iids, kinds):
    """white press rings inside the tapped items; returns {item index: [ring html]}"""
    marks = {k: [] for k in range(len(iids))}
    for tp in g.get("taps") or []:
        k = _item_index(b, tp.get("at"), len(iids), "tap"); t = ctx.t(tp["t"], b); rid = f"{iids[k]}tp{len(marks[k])}"
        marks[k].append(f'<i id="{rid}" class="ui-tap" style="left:{tp.get("x", 0.5) * 100:.0f}%;top:{tp.get("y", 0.5) * 100:.0f}%"></i>')
        ctx.add(f"tl.fromTo('#{rid}',{{scale:0.5,opacity:0}},{{scale:1,opacity:1,duration:0.12,ease:'power2.out'}},{t - 0.12:.3f});")
        ctx.add(f"tl.fromTo('#{rid}',{{scale:1,opacity:1}},{{scale:1.5,opacity:0,duration:0.32,ease:'power1.out',immediateRender:false}},{t + 0.06:.3f});")
        ctx.add(f"tl.fromTo('#{iids[k]}',{{scale:1}},{{scale:0.96,duration:0.07,yoyo:true,repeat:1,ease:'power1.inOut'}},{t:.3f});")
        if kinds[k] == "button": ctx.add(f"tl.to('#{iids[k]}b',{{backgroundColor:'{ctx.accent}',duration:0.15}},{t:.3f});")
        ctx.fx(t, "tap")
    return marks


def _focus(ctx, b, g, p, iids, h):
    """dim the other items, outline the named one, optionally zoom the screen onto it; {"at": null} clears"""
    scr, prev, none = f"#{p}scr", None, "0 0 0 0 rgba(0,0,0,0),0 0 0 0 rgba(0,0,0,0)"
    for f in g.get("focus") or []:
        t = ctx.t(f["t"], b)
        if f.get("at") is None:
            ctx.add(f"tl.to({json.dumps(['#' + i for i in iids])},{{opacity:1,boxShadow:'{none}',duration:0.25}},{t:.3f});")
            ctx.add(f"tl.to('{scr}',{{scale:1,x:0,y:0,duration:0.45,ease:'power2.inOut'}},{t:.3f});"); prev = None; continue
        k = _item_index(b, f["at"], len(iids), "focus"); z = float(f.get("zoom", 1)); others = [f"#{i}" for j, i in enumerate(iids) if j != k]
        if others: ctx.add(f"tl.to({json.dumps(others)},{{opacity:{f.get('dim', 0.25)},boxShadow:'{none}',duration:0.25}},{t:.3f});")
        glow = f"0 0 0 5px {ctx.accent},0 0 60px {h['rgba'](ctx.accent, 0.55)}"
        ctx.add(f"tl.to('#{iids[k]}',{{opacity:1,boxShadow:'{glow}',duration:0.25}},{t:.3f});")
        if z != 1:
            ctx.add(f"(function(){{var o=focusXY('{scr}','#{iids[k]}');window.TL.to('{scr}',{{scale:{z},x:-o.dx*{z},y:-o.dy*{z},duration:0.5,ease:'power2.inOut'}},{t:.3f});}})();")
            ctx.add(f"tl.fromTo('{scr}',{{filter:'blur(6px)'}},{{filter:'blur(0px)',duration:0.35,ease:'power2.out',immediateRender:false}},{t:.3f});")
        ctx.fx(t, "whoosh_soft" if z != 1 else "tick"); prev = k
    return prev


def g_ui(ctx, b, g, p, h):
    items = list(g.get("items") or [])
    bad = [it.get("kind") for it in items if it.get("kind") not in RENDER]
    if bad: raise ValueError(f"beat {b['_i']}: ui item kind {bad[0]!r} — use one of {', '.join(RENDER)}")
    iids = [f"{p}u{k}" for k in range(len(items))]
    marks = _taps(ctx, b, g, iids, [it["kind"] for it in items]); body = []
    for k, it in enumerate(items):
        inner = RENDER[it["kind"]](ctx, b, it, iids[k], h)
        if it.get("show") is not None: h["rise"](ctx, f"#{iids[k]}", ctx.t(it["show"], b), 30, 0.3, "pop")
        body.append(f'<div id="{iids[k]}" class="ui-it">{inner}{"".join(marks[k])}</div>')
    _focus(ctx, b, g, p, iids, h)
    title = f'<div class="ui-bar">{h["esc"](g["title"])}</div>' if g.get("title") else ""
    scr = f'<div id="{p}scr" class="ui-scr{" ui-full" if b["layout"] != "face" else ""}">{title}{"".join(body)}</div>'
    return f'<div class="ui-card" style="top:{g.get("y", 0.54) * H:.0f}px">{scr}</div>' if b["layout"] == "face" else scr


# ---------------------------------------------------------------- comment → notification CTA
def _keyword_time(ctx, b, g, word):
    if g.get("done") is not None: return ctx.t(g["done"], b)
    try: return max(0.0, ctx.word_at(word, b))
    except ValueError:
        print(f"warn: beat {b['_i']}: the CTA keyword {word!r} is not spoken in this beat — it types at 60 % of the beat")
        return b["_t0"] + 0.6 * (b["_t1"] - b["_t0"])


def _notify_time(ctx, b, g, done):
    t = ctx.t(g["notify"], b) if g.get("notify") is not None else min(done + NOTIFY_AFTER, b["_t1"] - NOTIFY_TAIL)
    t = max(done + NOTIFY_MIN_GAP, t)
    if round(b["_t1"] - t, 3) < NOTIFY_TAIL:
        print(f"warn: beat {b['_i']}: the notification lands {max(0.0, b['_t1'] - t):.2f} s before the beat ends — end the beat later or type the keyword earlier (done)")
    return t


def g_comment(ctx, b, g, p, h):
    if b["layout"] != "face":   # it is placed in frame coordinates over the speaker; other layouts put it in a smaller zone
        raise ValueError(f"beat {b['_i']}: gfx comment goes on a face beat (it sits over the speaker), not on a {b['layout']} beat")
    e = h["esc"]; word = str(g.get("word") or ctx.meta.get("cta_word") or "LINK")
    done = max(b["_t0"] + 0.65, _keyword_time(ctx, b, g, word))
    start = type_on(ctx, f"#{p}ty", word, done, b["_t0"] + 0.35)
    notify = _notify_time(ctx, b, g, done)
    h["rise"](ctx, f"#{p}cm", max(b["_t0"] + 0.02, start - CTA_LEAD), 40, 0.3, "pop")
    ctx.add(f"tl.fromTo('#{p}ph',{{opacity:1}},{{opacity:0,duration:0.05}},{start - 0.05:.3f});")
    ctx.add(f"tl.fromTo('#{p}sd',{{scale:1}},{{scale:1.25,duration:0.1,yoyo:true,repeat:1}},{done + 0.12:.3f});"); ctx.fx(done + 0.12, "send")
    ctx.add(f"tl.to('#{p}cm',{{opacity:0,y:-24,duration:0.22,ease:'power2.in'}},{notify - 0.12:.3f});")
    ctx.add(f"tl.fromTo('#{p}nt',{{opacity:0,y:-70,scale:0.94}},{{opacity:1,y:0,scale:1,duration:0.38,ease:'back.out(1.6)'}},{notify:.3f});")
    ctx.fx(notify, "ding"); y = g.get("y", 0.49) * H
    sender = g.get("sender") or ctx.meta.get("handle", ""); msg = g.get("message", "Here's your link")
    return (f'<div id="{p}cm" class="cmt" style="top:{y:.0f}px"><i class="av"></i><div class="in"><span id="{p}ph" class="ph">'
            f'{e(g.get("placeholder", "Add a comment…"))}</span><span id="{p}ty" class="ty">{e(word)}</span></div><i id="{p}sd" class="snd">&#8593;</i></div>'
            f'<div id="{p}nt" class="ntf" style="top:{y:.0f}px;opacity:0"><i class="ig"></i><div class="nb"><div class="hd"><b>{e(g.get("app", "Instagram"))}</b>'
            f'<span>now</span></div><div class="tt">{e(sender)}</div><div class="ms">{e(msg)}</div></div></div>')
