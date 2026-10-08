#!/usr/bin/env python3
"""Check a plan.json against the measured editing grammar of its style profile before building.

  python3 plan_lint.py <project> [--projects <folder with your earlier reel projects>]
      → metrics vs targets, list of problems; exit 1 on errors

Targets come from the style profile named in plan meta.style (default: the engine defaults in styles/_defaults):
layout mix, first visual change, opening and closing layout, the longest face run. The novelty check compares the plan with
your two most recent earlier plans; it looks for them under --projects or $REELS_PROJECTS and is skipped when neither is set.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import hashlib, json, os, re, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import Ctx  # noqa: E402
from common import SKILL, era_view  # noqa: E402

def is_cta(b):
    """the closing call to action: keyword captions (cta) or the comment box that types the keyword (gfx comment)"""
    return bool(b.get("cta")) or (b.get("gfx") or {}).get("type") == "comment"


EVENT_KEYS = {"logos": "items", "hub": "nodes", "switcher": "seq", "terminal": "lines", "html": "js"}
SKIP_DIRS = {"hf", "work", "assets", "out", "node_modules", ".git", "snapshots"}


def sig(b):
    """what a viewer remembers of a beat: layout, the kind of graphic and its look (custom html by its markup)"""
    g = b.get("gfx") or {}
    look = hashlib.md5(g.get("html", "").encode()).hexdigest()[:8] if g.get("type") == "html" else f"{g.get('font')}|{bool(g.get('decode'))}|{g.get('over_style')}|{g.get('label_style')}"
    return (b["layout"], g.get("type"), look)


def previous_plans(P, root, n=2, max_depth=4):
    """the n most recent plan.json files under root (excluding this project), searched at most max_depth folders deep"""
    if not root or not os.path.isdir(root): return []
    here, out, base = os.path.realpath(P), [], os.path.realpath(root).rstrip(os.sep).count(os.sep)
    for cur, dirs, files in os.walk(root):
        depth = os.path.realpath(cur).count(os.sep) - base
        dirs[:] = [] if depth >= max_depth else [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if "plan.json" in files and os.path.realpath(cur) != here: out.append(os.path.join(cur, "plan.json"))
    return sorted(out, key=os.path.getmtime, reverse=True)[:n]


def novelty(P, plan, root, errs, warns):
    """Every reel should feel new while staying in one style: the grid, captions, accent discipline and sound system stay;
    the opening, the key-number treatment, the backgrounds, the music and the custom moves change from reel to reel."""
    meta, beats = plan.get("meta", {}), plan["beats"]
    opening = lambda m: next((k for k in ("open_zoom", "open_punch", "flash_start") if m.get(k)), None)
    mine = [sig(b) for b in beats if b["layout"] != "face"]
    for k, f in enumerate(previous_plans(P, root)):
        try: q = json.load(open(f))
        except Exception: continue
        name = os.path.relpath(os.path.dirname(f), root); qm, qb = q.get("meta", {}), q.get("beats", [])
        if qb and sig(beats[0]) == sig(qb[0]):
            errs.append(f"the opening repeats {name} one to one ({sig(beats[0])[1]}, {sig(beats[0])[2]}). Pick another opening from references/move-bank.md")
        if k: continue   # the rest compares with the latest reel only
        if opening(meta) and opening(meta) == opening(qm): warns.append(f"same opening move as {name}: {opening(meta)} (rotate open_zoom / open_punch / flash_start / a custom first beat)")
        if meta.get("music") and meta.get("music") == qm.get("music"): warns.append(f"same music as {name}: {meta.get('music')} (rotate the music bed between reels)")
        theirs = {sig(b) for b in qb if b["layout"] != "face"}
        rep = [s for s in mine if s in theirs and s[1] not in (None, "none")]
        if mine and len(rep) / len(mine) >= 0.4:
            warns.append(f"{len(rep)} of {len(mine)} graphic beats repeat the looks of {name} ({', '.join(sorted({s[1] for s in rep}))}): take new moves from references/move-bank.md")


def check_visual_legibility(beat, errs, warns):
    """Catch the tiny, captionless UI cards seen in an actual delivered reel."""
    g = beat.get("gfx") or {}
    if g.get("type") != "ui": return
    items = g.get("items") or []
    text_items = [it for it in items if it.get("kind") in ("search", "row", "profile", "toggle", "button", "text")]
    grid_labels = any(it.get("kind") == "grid" and it.get("views") for it in items)
    small_unit_labels = any(it.get("kind") in ("stat", "ring") and it.get("label") for it in items)
    if beat.get("caption") == "none" and (text_items or grid_labels or small_unit_labels or g.get("title")):
        errs.append(f"beat {beat['_i']}: captionless UI relies on phone-small CSS labels (28–46 px); add readable speech captions or one large focal visual")
    for it in items:
        if it.get("kind") == "text":
            size = it.get("size", 44)
            if not isinstance(size, (int, float)) or size < 44:
                errs.append(f"beat {beat['_i']}: UI text is {size!r} px (minimum 44 px at 1080 width); enlarge it or move secondary copy to captions")
    if len(items) > 5:
        warns.append(f"beat {beat['_i']}: {len(items)} UI items compete on a phone screen; split the beat or focus one item at a time")


def check_html_disclosure(beat, errs):
    """Keep illustrative UI/opinion labels readable and clear of app controls.

    This intentionally checks only explicit disclosures in custom HTML. Other
    UI text can be decorative; a disclosure is essential to interpreting a
    simulated screen and must remain readable in the delivered vertical reel.
    """
    graphic = beat.get("gfx") or {}
    if graphic.get("type") != "html": return
    markup = graphic.get("html", "")
    for element in re.finditer(r'<(?:div|span)\b(?P<attrs>[^>]*)>(?P<copy>[^<]*(?:Tasviriy misol|Muallif bahosi)[^<]*)',
                               markup, re.IGNORECASE):
        style_match = re.search(r'\bstyle="([^"]+)"', element.group("attrs"))
        style = style_match.group(1) if style_match else ""
        font_match = re.search(r'\bfont(?:-size)?\s*:\s*[^;]*?(\d+(?:\.\d+)?)px', style)
        size = float(font_match.group(1)) if font_match else 0
        if size < 44:
            errs.append(f"beat {beat['_i']}: illustrative disclosure is {size:g} px (minimum 44 px at 1080 width)")
        bottom_match = re.search(r'\bbottom\s*:\s*(\d+(?:\.\d+)?)px', style)
        if bottom_match and float(bottom_match.group(1)) < 300:
            errs.append(f"beat {beat['_i']}: illustrative disclosure sits in the bottom app-control zone")
        top_match = re.search(r'\btop\s*:\s*(\d+(?:\.\d+)?)px', style)
        if top_match:
            padding_match = re.search(r'\bpadding\s*:\s*(\d+(?:\.\d+)?)px', style)
            height_match = re.search(r'\bheight\s*:\s*(\d+(?:\.\d+)?)px', style)
            padding = float(padding_match.group(1)) if padding_match else 0
            estimated_height = max(size * 1.2 + 2 * padding,
                                   float(height_match.group(1)) if height_match else 0)
            if float(top_match.group(1)) + estimated_height > 1620:
                errs.append(f"beat {beat['_i']}: illustrative disclosure sits in the bottom app-control zone")


def check_vocab_spelling(P, words, warns):
    """Surface Scribe's proper-name mistakes before they become rendered captions."""
    path = os.path.join(P, "work", "source.json")
    if not os.path.isfile(path): return
    source = json.load(open(path))
    names = source.get("vocab_names") or []
    normalized = lambda text: re.sub(r"[^\w]+", "", text.casefold())
    transcript = normalized(" ".join(w["word"] for w in words))
    for name in names:
        if normalized(name) not in transcript:
            warns.append(f"provided name {name!r} is absent from work/words.json; check transcript and captions against the script before rendering")


def check_visual_intent(beat, errs):
    intent = beat.get("qa_intent")
    if intent is None: return
    if not isinstance(intent, dict) or not any(intent.get(k) is True for k in ("static_ok", "dark_ok")):
        errs.append(f"beat {beat['_i']}: qa_intent must name an explicit static_ok or dark_ok exception")
    elif not isinstance(intent.get("reason"), str) or len(intent["reason"].strip()) < 12:
        errs.append(f"beat {beat['_i']}: qa_intent requires a specific editorial reason (at least 12 characters)")


def main(P, root=None):
    ctx = Ctx(P); beats = ctx.plan["beats"]; D = ctx.dur; errs, warns = [], []
    S = era_view(ctx.style, ctx.meta.get("era", "2026")); name = S.get("name", "style")
    check_vocab_spelling(P, ctx.words, warns)
    TG = {k: (v["lo"], v["hi"], v["median"]) for k, v in S["layouts"].items()}
    for i, b in enumerate(beats): b["_i"] = i; b["_t0"] = ctx.t(b["t0"]) if i else 0.0
    for i, b in enumerate(beats): b["_t1"] = beats[i + 1]["_t0"] if i + 1 < len(beats) else D
    share = {"split": 0.0, "graphic": 0.0, "face": 0.0}
    for b in beats:
        d = b["_t1"] - b["_t0"]; share["graphic" if b["layout"] in ("graphic", "broll") else b["layout"]] += d / D
        if d < 0.45: errs.append(f"beat {b['_i']} lasts {d:.2f}s (< 0.45 s: a flash, merge it)")
        if d > 4.0 and not (b is beats[-1] and is_cta(b)): warns.append(f"beat {b['_i']} lasts {d:.2f}s (> 4 s: split it or add in-beat events)")
        g = b.get("gfx") or {}
        check_visual_legibility(b, errs, warns)
        check_html_disclosure(b, errs)
        check_visual_intent(b, errs)
        if g.get("type") == "TODO" or "TODO" in json.dumps(g): errs.append(f"beat {b['_i']}: TODO left in the graphic — fill it (references/shot-library.md)")
        if b["layout"] in ("split", "graphic") and not g and b.get("caption") == "none": errs.append(f"beat {b['_i']}: empty screen (no graphic, no caption)")
        if b["layout"] == "split" and not g: warns.append(f"beat {b['_i']}: split without a graphic — the top 60% of the frame is empty")
        ev = len(g.get(EVENT_KEYS.get(g.get("type"), "_"), [])) if g else 0
        if g.get("type") == "shot": ev += (1 if g.get("box") else 0) + (1 if g.get("zoom") else 0) + (1 if g.get("drift", True) and not g.get("zoom") else 0)
        if g.get("type") in ("counter", "chart", "meter", "widget", "note"): ev += 2   # they animate through the beat
        if g.get("type") == "ui": ev += len(g.get("taps") or []) + len(g.get("focus") or []) + sum(1 for it in g.get("items", []) if any(it.get(k) is not None for k in ("t", "done", "on", "show")))
        if g.get("type") == "comment": ev += 3   # box, typing, notification
        if d > 2.6 and b["layout"] != "face" and ev < 2: warns.append(f"beat {b['_i']} ({d:.1f}s, {g.get('type', 'none')}): long static graphic — add items/box/zoom or split the beat")
        for key in ("src", "icon", "center", "logo", "bg_src", "avatar"):
            v = g.get(key)
            if isinstance(v, str) and not v.startswith(("http", "data:", "TODO")) and not any(os.path.exists(x) for x in (os.path.join(P, v), os.path.join(SKILL, "assets", v))):
                errs.append(f"beat {b['_i']}: missing asset {v}")
        for it in g.get("items", []) + g.get("nodes", []) + g.get("cards", []):
            for key in ("src", "avatar"):   # ui items carry optional avatars and no src
                if it.get(key) and not any(os.path.exists(x) for x in (os.path.join(P, it[key]), os.path.join(SKILL, "assets", it[key]))):
                    errs.append(f"beat {b['_i']}: missing asset {it[key]}")
    runs, cur = [], None
    for b in beats:
        lay = "graphic" if b["layout"] in ("graphic", "broll") else b["layout"]
        if cur and cur[0] == lay: cur[1] += b["_t1"] - b["_t0"]
        else: cur = [lay, b["_t1"] - b["_t0"]]; runs.append(cur)
    ol, cl = S.get("open_layout", "split"), S.get("close_layout", "face")
    if ol and (beats[0]["layout"] != ol or (ol == "split" and not beats[0].get("gfx"))):
        errs.append(f"the reel must open on a {ol} beat" + (" with a graphic" if ol == "split" else "") + f" (style '{name}' always does)")
    if cl and beats[-1]["layout"] != cl: errs.append(f"the reel must end on a {cl} beat (the CTA; style '{name}' always does)")
    if not is_cta(beats[-1]): warns.append("last beat has no CTA: \"cta\": true (keyword colour + mix captions) or gfx \"comment\" (keyword typed into a comment box)")
    for k, (lo, hi, med) in TG.items():
        if k in share and not lo <= share[k] <= hi: warns.append(f"layout share {k} = {share[k]:.2f}, style range {lo}-{hi} (median {med})")
    for a, b2 in zip(beats, beats[1:]):
        if a["layout"] == b2["layout"] == "face": warns.append(f"beats {a['_i']}-{b2['_i']}: two face close-ups in a row (put a graphic between them or merge)")
        if a["layout"] == b2["layout"] == "split" and (a.get("gfx") or {}).get("type") == (b2.get("gfx") or {}).get("type") and a.get("bg") == b2.get("bg"):
            warns.append(f"beats {a['_i']}-{b2['_i']}: same layout, same graphic kind, same background — the cut will read as a jump; change the graphic or the background")
    fc = S["pace"]["first_change"]
    if len(beats) > 1 and beats[1]["_t0"] > fc["hi"]: warns.append(f"first visual change at {beats[1]['_t0']:.2f}s (style {fc['lo']}–{fc['hi']} s, median {fc['median']} s)")
    face_runs = [r for r in runs if r[0] == "face"]
    if any(r[1] > S.get("face_max_run", 4.5) for r in face_runs[:-1]): warns.append(f"a face close-up runs > {S.get('face_max_run', 4.5)} s before the CTA — cut to a graphic")
    lens = [b["_t1"] - b["_t0"] for b in beats]
    nocap = sum(b["_t1"] - b["_t0"] for b in beats if b.get("caption") == "none") / D
    if nocap > 0.3 and S.get("captions", {}).get("always_on", True): warns.append(f"{nocap:.0%} of the reel has no caption (style: captions almost always on)")
    print(f"style '{name}' | {len(beats)} beats over {D:.1f}s | beat median {st.median(lens):.2f}s (min {min(lens):.2f}, max {max(lens):.2f}) | "
          f"layout runs {len(runs)}, run median {st.median(r[1] for r in runs):.2f}s (style {S['pace'].get('layout_run_median', 2.0)})")
    print("layout share: " + ", ".join(f"{k} {v:.2f} (style {TG[k][2]})" for k, v in share.items() if k in TG) + f" | no-caption {nocap:.0%}")
    print("sequence: " + " ".join({"split": "S", "graphic": "G", "broll": "B", "face": "F"}[b["layout"]] for b in beats))
    for b in beats:   # flat custom graphics read as slides, not montage: give them depth
        g = b.get('gfx') or {}
        if g.get('type') == 'html' and not any(k in g.get('html', '') for k in ('box-shadow', 'drop-shadow', 'blur(')):
            warns.append(f"beat {b['_i']}: flat custom graphic (no shadow, no blur). Add depth: blurred backdrop, heavy card shadow, glow, push-in (references/move-bank.md)")
    root = root or os.environ.get("REELS_PROJECTS")
    if root: novelty(P, ctx.plan, os.path.abspath(os.path.expanduser(root)), errs, warns)
    for e in errs: print("ERROR", e)
    for w in warns: print("warn ", w)
    return 1 if errs else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): raise SystemExit(__doc__)
    sys.exit(main(os.path.abspath(a[0]), a[a.index("--projects") + 1] if "--projects" in a else None))
