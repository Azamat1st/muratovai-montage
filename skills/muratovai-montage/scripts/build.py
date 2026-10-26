#!/usr/bin/env python3
"""Reel builder: plan.json + clean head + cutout + words + face track → HyperFrames project (picture only).

  python3 build.py <project_dir>            # writes <project_dir>/hf/index.html and stages media/fonts/vendor/img
  npx hyperframes render <project_dir>/hf -o <project_dir>/out/picture.mp4 --fps 30   (see SKILL.md, step 6)

Project layout (created by prep.py):
  plan.json                      the edit plan (beats), see references/plan-format.md
  work/clean.mp4                 tight-cut talking head, 1080x1920 @30, dense keyframes
  work/clean_subject.webm        person cutout of clean.mp4 (VP9 alpha; Apple Vision or hyperframes remove-background)
  work/words.json                {"words":[{word,start,end}]} of clean.mp4
  work/face.json                 face track of clean.mp4 (2 fps; Apple Vision, OpenCV or a centred estimate)
  assets/                        logos, screenshots, photos referenced by the plan (paths relative to the project)
Times in the plan: seconds (float) or "w:<index>[+/-offset]" = start of that word in work/words.json minus 0.05 s.
The style profile (plan meta.style, default: the engine defaults) can override the framing targets (style.json → framing).
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import hashlib, html, json, math, os, re, shutil, statistics as st, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SKILL, load_style  # noqa: E402
import gfx_ui  # noqa: E402

W, H, FPS = 1080, 1920, 30
# default framing targets, measured on reference frames (Apple Vision face box, 1080x1920): face width / eye height / centre x.
# split 418/1337/549 and close-up 754/732/541 are the engine defaults; style.json → framing overrides them per style.
FRAME = {"split": dict(w=418, eye=1337, cx=549), "close": dict(w=754, eye=732, cx=541), "medium": dict(w=600, eye=800, cx=540),
         # 2025 system (reels 23, 24): speaker medium in the bottom half of a 50/50 split, eyes ≈0.63 H; close-up eyes ≈0.35 H
         "split25": dict(w=360, eye=1210, cx=540), "close25": dict(w=700, eye=672, cx=540)}
SEAM25 = 973   # 0.507 H: straight seam of the 2025 split
ARCH = dict(top=1212, side=18, r=195)
POP = 210   # how far above the arch edge the cut-out head may show (px); a 70 px feather hides segmentation blobs above the hair
BG = {"white": "#fdfdfd", "gray": "#f1f1ef", "paper": "#ece5d8", "dark": "#16171b", "black": "#060607", "cream": "#f6f1e7"}


def esc(s):
    return html.escape(str(s), quote=True)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def browser_preflight(P):
    """Fail on browser page errors/missing timeline when Playwright is installed.

    Standalone installs without Playwright fall back to snap.py's picture guard.
    """
    node = shutil.which("node")
    if not node:
        print("browser preflight unavailable (Node missing); snap.py will check rendered frames")
        return False
    report = f"{P}/work/browser_preflight.json"
    if os.path.isfile(report): os.remove(report)
    run = subprocess.run([node, f"{os.path.dirname(__file__)}/browser_preflight.mjs", P, report],
                         capture_output=True, text=True)
    if run.returncode == 2:
        print("browser preflight unavailable (Playwright Chromium missing); snap.py will check rendered frames")
        return False
    if run.returncode:
        raise SystemExit((run.stderr or run.stdout).strip()[-1600:] + "\nFix the named caption/plan beat, rebuild, then snapshot again.")
    if os.path.isfile(report):
        manifest_path = f"{P}/work/caption_qa.json"
        if os.path.isfile(manifest_path):
            with open(report) as file: measured = json.load(file)
            with open(manifest_path) as file: manifest = json.load(file)
            by_id = {cap["id"]: cap for cap in measured.get("captions", [])}
            for caption in manifest.get("captions", []):
                if caption["id"] in by_id:
                    caption.update(by_id[caption["id"]]); caption["dom_layout_checked"] = True
            with open(manifest_path, "w") as file: json.dump(manifest, file, ensure_ascii=False, indent=1)
    print(run.stdout.strip())
    return True


def lum(hexc):
    h = hexc.lstrip("#")
    if len(h) == 3: h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def rgba(hexc, a):
    h = hexc.lstrip("#"); r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4)); return f"rgba({r},{g},{b},{a})"


def mix(hexc, other, k):
    """blend two hex colours: k=0 → hexc, k=1 → other"""
    a = [int(hexc.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]; b = [int(other.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * k):02x}" for x, y in zip(a, b))


class Ctx:
    def __init__(self, P):
        self.P = P; self.plan = json.load(open(f"{P}/plan.json")); self.meta = self.plan.get("meta", {})
        self.words = json.load(open(f"{P}/work/words.json"))["words"]
        self.dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{P}/work/clean.mp4"], capture_output=True, text=True).stdout)
        self.face = [f for f in json.load(open(f"{P}/work/face.json")) if "w" in f] if os.path.exists(f"{P}/work/face.json") else []
        self.style = load_style(self.meta.get("style"), P)
        self.accent = self.meta.get("accent", self.style.get("plan_defaults", {}).get("accent", "#D97757")); self.js = []; self.sfx = []; self.imgs = {}; self.media = []

    def t(self, v, beat=None):
        """time spec → seconds: number | 'w:12' | 'w:12+0.2' | '+0.3' (from beat start) | 'word:Gemini' (first match inside the beat)"""
        if isinstance(v, (int, float)): return float(v)
        v = str(v).strip()
        m = re.match(r"^w:(\d+)([+-][\d.]+)?$", v)
        if m: return max(0.0, self.words[int(m.group(1))]["start"] - 0.05 + float(m.group(2) or 0))
        m = re.match(r"^\+([\d.]+)$", v)
        if m and beat is not None: return beat["_t0"] + float(m.group(1))
        m = re.match(r"^word:(.+?)([+-][\d.]+)?$", v)
        if m: return max(0.0, self.word_at(m.group(1), beat) + float(m.group(2) or 0))
        return float(v)

    def word_at(self, text, beat=None):
        """the first spoken `text` inside the beat (case and punctuation ignored), 50 ms early; matched whole, so "GPT-4" stays one word"""
        target = re.sub(r"[^\w']", "", text.lower()); lo = beat["_t0"] - 0.3 if beat else 0; hi = beat["_t1"] if beat else 1e9
        for w in self.words:
            if lo <= w["start"] < hi and re.sub(r"[^\w']", "", w["word"].lower()) == target: return w["start"] - 0.05
        raise ValueError(f"word '{text}' not found in beat {beat and beat.get('_i')}")

    def img(self, src):
        """stage an asset into hf/img and return its relative url"""
        if src.startswith(("http://", "https://", "data:")): return src
        p = src if os.path.isabs(src) else os.path.join(self.P, src)
        if not os.path.exists(p): p2 = os.path.join(SKILL, "assets", src)
        else: p2 = p
        if not os.path.exists(p2): raise FileNotFoundError(src)
        name = re.sub(r"[^\w.-]", "_", os.path.basename(p2))
        if name in self.imgs and self.imgs[name] != p2: name = f"{len(self.imgs)}_{name}"
        self.imgs[name] = p2; return f"img/{name}"

    def img_size(self, src):
        from PIL import Image
        p = src if os.path.isabs(src) else os.path.join(self.P, src)
        return Image.open(p).size

    def add(self, s): self.js.append(s)

    def fx(self, t, kind, db=None, dur=None):
        self.sfx.append(dict(t=round(t, 3), kind=kind, db=db, **({"dur": round(float(dur), 3)} if dur else {})))


# ---------------------------------------------------------------- framing
def face_at(ctx, t0, t1):
    F = [f for f in ctx.face if t0 - 0.25 <= f["t"] <= t1 + 0.25]
    if not F and ctx.face: F = [min(ctx.face, key=lambda f: abs(f["t"] - (t0 + t1) / 2))]
    if not F: return dict(cx=540, eye=900, w=300, top=800, h=300)
    k = 1080 / F[0]["W"]
    return dict(cx=st.median(f["cx"] for f in F) * k, eye=st.median(f["eye_y"] for f in F) * k, w=st.median(f["w"] for f in F) * k,
                top=st.median(f["y"] for f in F) * k, h=st.median(f["h"] for f in F) * k)


def face_moves(ctx, t0, t1, threshold=38):
    samples = [f for f in ctx.face if t0 <= f["t"] <= t1 and "cx" in f]
    if len(samples) < 2: return False
    x = [f["cx"] * 1080 / f["W"] for f in samples]
    y = [f["eye_y"] * 1080 / f["W"] for f in samples]
    return max(x) - min(x) > threshold or max(y) - min(y) > threshold


def transform(face, mode, smax):
    tg = FRAME[mode]; s = max(0.55, min(smax, tg["w"] / face["w"]))
    if mode != "split": s = max(1.0, s)   # a full-width face (incl. the 2025 half) is never smaller than the source (no side bars); the 2026 arch has margins
    tx = tg["cx"] - s * face["cx"]; ty = tg["eye"] - s * face["eye"]
    if mode == "split":
        tx = min(tx, ARCH["side"]); tx = max(tx, W - ARCH["side"] - s * W); ty = max(ty, H - s * H)
    elif mode == "split25":
        tx = min(tx, 0); tx = max(tx, W - s * W); ty = min(ty, SEAM25); ty = max(ty, H - s * H)
    else:
        tx = min(tx, 0); tx = max(tx, W - s * W); ty = min(ty, 0); ty = max(ty, H - s * H)
    return round(tx, 1), round(ty, 1), round(s, 4)


# ---------------------------------------------------------------- captions
FUNC = {"a", "an", "the", "to", "of", "in", "on", "at", "for", "and", "or", "but", "is", "are", "was", "it", "its", "it's", "my", "your", "with", "by", "from", "as", "that", "this", "so", "if",
        "и", "в", "на", "с", "к", "по", "за", "от", "до", "о", "а", "но", "что", "это", "как", "из", "у", "же", "ли", "не", "для"}


BRIDGE = {"but", "now", "instead", "so", "however", "но", "теперь", "зато", "итак", "lekin", "endi", "ammo"}
CAP_STYLES = ("split", "caps", "face", "mix", "box", "box_seam", "face25", "wide")
CAP_FONT_PX = {"split": 72, "caps": 128, "face": 82, "mix": 88, "box": 60, "box_seam": 60, "face25": 76, "wide": 76}


def wide_lines(words):
    """a "wide" chunk in two lines balanced by characters; one word stays one line"""
    if len(words) < 2: return list(words), []
    k = min(range(1, len(words)), key=lambda i: (max(len(" ".join(words[:i])), len(" ".join(words[i:]))), i))
    return list(words[:k]), list(words[k:])


def caption_style_for(ctx, b, lay, era25):
    """the caption style of a beat: layout default → mix on the CTA → 2025 set → meta.caption_face on face beats → the beat's own"""
    style = {"split": "split", "face": "face", "graphic": "caps", "broll": "caps"}[lay]
    if lay == "face" and (b.get("caption_style") == "mix" or b.get("cta")): style = "mix"
    if era25: style = {"split": "box_seam", "face": "face25", "graphic": "box", "broll": "box"}[lay]
    if lay == "face" and ctx.meta.get("caption_face") in CAP_STYLES and not b.get("cta"): style = ctx.meta["caption_face"]
    return b["caption_style"] if b.get("caption_style") in CAP_STYLES else style


def chunks_for(ctx, beat, style):
    """caption chunks: split at sentence ends / pauses / commas, pack by characters, never leave a function word dangling"""
    t0, t1 = beat["_t0"], beat["_t1"]
    W_ = [dict(w, word=w["word"].strip()) for w in ctx.words if t0 - 0.02 <= w["start"] < t1 - 0.02 and w["word"].strip()]
    N, C = {"split": (2, 16), "face": (3, 18), "caps": (2, 14), "mix": (3, 20), "box": (3, 18), "box_seam": (3, 18), "face25": (3, 18), "wide": (4, 22)}[style]
    profile = getattr(ctx, "style", {})
    measured = profile.get("captions", {}).get("words_per_chunk")
    if profile.get("name") != "_defaults" and isinstance(measured, (int, float)) and measured > 0:
        N = max(1, min(4, round(measured)))
    available = caption_box(ctx, beat, style)[2] - caption_box(ctx, beat, style)[0] - (68 if style in ("box", "box_seam") else 20)
    lines = 2 if style in ("wide", "mix") else 1
    C = min(C, max(5, int(available * lines / (CAP_FONT_PX[style] * .65))))
    bare = lambda w: re.sub(r"[^\w']", "", w.lower())
    phrases, cur = [], []
    for i, w in enumerate(W_):
        cur.append(w); nxt = W_[i + 1] if i + 1 < len(W_) else None
        if re.search(r"[.!?;:,]$", w["word"]) or (nxt and nxt["start"] - w["end"] > 0.25): phrases.append(cur); cur = []
    if cur: phrases.append(cur)
    if style == "wide":   # a bridge word opening a sentence stands alone (BUT / NOW / INSTEAD)
        phrases = [part for ph in phrases for part in ([ph[:1], ph[1:]] if len(ph) > 1 and bare(ph[0]["word"]) in BRIDGE else [ph])]
    out = []
    for ph in phrases:
        chs, c = [], []
        for w in ph:
            txt = " ".join(x["word"] for x in c + [w])
            if c and (len(txt) > C or len(c) + 1 > N): chs.append(c); c = []
            c.append(w)
        if c: chs.append(c)
        if N == 1:
            out += chs
            continue
        k = 0
        while k < len(chs) - 1:          # move trailing function words forward
            while len(chs[k]) > 1 and bare(chs[k][-1]["word"]) in FUNC and len(" ".join(x["word"] for x in [chs[k][-1]] + chs[k + 1])) <= C + 6:
                chs[k + 1].insert(0, chs[k].pop())
            k += 1
        merged = []
        for c in chs:                    # a lone function word joins its neighbour
            if len(c) == 1 and bare(c[0]["word"]) in FUNC and merged and len(" ".join(x["word"] for x in merged[-1] + c)) <= C + 6: merged[-1] += c
            elif merged and len(merged[-1]) == 1 and bare(merged[-1][0]["word"]) in FUNC: merged[-1] += c
            else: merged.append(c)
        out += merged
    res = []
    for k, c in enumerate(out):
        a = max(t0, c[0]["start"] - 0.04); b = (out[k + 1][0]["start"] - 0.04) if k + 1 < len(out) else t1
        res.append(dict(words=[x["word"] for x in c], starts=[x["start"] for x in c], ends=[x["end"] for x in c],
                        t0=a, t1=max(b, a + 0.12)))
    if beat.get("cta") and beat.get("_quote"):   # the CTA keyword holds from its word to the last frame, nothing replaces it
        q = bare(beat["_quote"])
        for k, r in enumerate(res):
            if any(bare(w) == q for w in r["words"]):
                r["t1"] = t1; res = res[:k + 1]; break
    return res


CAP_BOX = {"split": (857, 110), "face": (1290, 260), "mix": (1290, 260), "caps": (1225, 200),
           "box": (1262, 90), "box_seam": (928, 90), "face25": (1440, 120), "wide": (790, 340)}


def caption_box(ctx, beat, style):
    """The conservative rendered caption container, including style position."""
    top, height = CAP_BOX[style]; left, width = 60, 960
    measured = getattr(ctx, "style", {}).get("captions", {}).get("bounds_by_layout", {}).get(beat["layout"])
    if isinstance(measured, dict) and all(isinstance(measured.get(k), (int, float)) for k in ("x", "y", "w", "h")):
        # Reference bounds describe glyphs. Add breathing room to keep longer
        # words legible, then clamp to Reels/TikTok safe zones.
        width = int(max(540, min(960, measured["w"] * W * 1.20)))
        left = int(round(measured["x"] * W - width / 2))
        left = min(int(W * .95) - width, max(int(W * .05), left))
        top = int(round(measured["y"] * H - height / 2))
        top = min(int(H * .83) - height, max(int(H * .10), top))
    return left, top, left + width, top + height


def caption_estimated_min_font(ctx, beat, chunk, style):
    """Conservative width estimate before a browser can measure actual glyphs."""
    words = chunk["words"]
    if style == "wide":
        line_a, line_b = wide_lines(words)
        lines = [line_a, line_b]
    elif style == "mix" and len(words) > 1: lines = [words[:-1], words[-1:]]
    else: lines = [words]
    chars = max((len(" ".join(line)) for line in lines), default=0)
    available = caption_box(ctx, beat, style)[2] - caption_box(ctx, beat, style)[0] - (68 if style in ("box", "box_seam") else 20)
    if not chars: return CAP_FONT_PX[style]
    return round(min(CAP_FONT_PX[style], available / (chars * .65)), 1)


def cap_html(ctx, beat, ch, style, dark, idx, emph):
    E = {re.sub(r"[^\w']", "", e.lower()) for e in emph}
    Q = re.sub(r"[^\w']", "", str(beat.get("_quote", "")).lower())
    def word_html(w):
        clean = re.sub(r"[^\w']", "", w.lower()); cls = ' class="emph"' if clean in E else ""
        shown = "“" + re.sub(r"[^\w-]", "", w) + "”" if Q and clean == Q else w
        return f"<span{cls}>{esc(shown)}</span>"
    words = [re.sub(r"[.,;:]+$", "", w) or w for w in ch["words"]]   # short captions carry no full stops or commas; ? and ! stay
    if style == "mix":
        # the bold line is the stressed word: the first emphasised word of the chunk, else the last word
        key = next((k for k, w in enumerate(words) if re.sub(r"[^\w']", "", w.lower()) in E), len(words) - 1)
        if key == 0: inner = f'<span class="sans">{" ".join(word_html(w) for w in words)}</span>'
        else: inner = f'<span class="serif">{" ".join(word_html(w) for w in words[:key])}</span><span class="sans">{" ".join(word_html(w) for w in words[key:])}</span>'
        cls = "cap-face"
    elif style == "caps":
        inner = " ".join(word_html(re.sub(r"[.,!?;:]+$", "", w)) for w in words); cls = "cap-caps"
    elif style == "face":
        inner = " ".join(word_html(w) for w in words); cls = "cap-face"
    elif style in ("box", "box_seam"):   # 2025: white bold sans in a translucent grey box
        inner = " ".join(word_html(w) for w in words); cls = "cap-box" + (" seam" if style == "box_seam" else "")
    elif style == "face25":
        inner = " ".join(word_html(w) for w in words); cls = "cap-face25"
    elif style == "wide":
        inner, cls = wide_html(ctx, beat, ch, words, word_html, f"c{idx}")
    else:
        inner = " ".join(word_html(w) for w in words); cls = "cap-split"
    if dark and cls in ("cap-split", "cap-caps"): cls += " on-dark"
    cid = f"c{idx}"; acc = cap_accent(beat)
    box = caption_box(ctx, beat, style); width = box[2] - box[0]
    estimate = caption_estimated_min_font(ctx, beat, ch, style)
    if estimate < 48:
        raise ValueError(f"beat {beat['_i']}: caption {' '.join(ch['words'])!r} would shrink below 48 px ({estimate:.1f} px estimated); split the phrase or widen the caption area")
    sty = f"left:{box[0]}px;top:{box[1]}px;width:{width}px;height:{box[3] - box[1]}px;"
    if acc and style == "wide": sty += f"--capw:{acc};--capw-glow:{rgba(acc, .6)};"
    inner_width = width - (68 if style in ("box", "box_seam") else 20)
    fit_width = min(inner_width, 940 if cls.startswith("cap-caps") else 900 if style == "wide" else 960)
    ctx.add(f"fit('#{cid} .cap-in', {fit_width}, 48);")
    ctx.add(f"tl.fromTo('#{cid} .cap-in',{{scale:0.94,opacity:0}},{{scale:1,opacity:1,duration:0.07,ease:'power2.out'}},{ch['t0']:.3f});")
    return f'<div id="{cid}" class="clip cap {cls}" style="{sty}" data-start="{ch["t0"]:.3f}" data-duration="{ch["t1"] - ch["t0"]:.3f}" data-track-index="6"><span class="cap-in" style="max-width:{inner_width}px">{inner}</span></div>'


WHITE_SHADOW = "0 4px 18px rgba(0,0,0,.55),0 1px 3px rgba(0,0,0,.35)"
HEX6 = re.compile(r"#[0-9a-fA-F]{6}")


def cap_accent(beat):
    """the beat's own caption colour or None; it goes into CSS and JS as is, so only #RRGGBB passes"""
    v = beat.get("cap_accent")
    if v is None or (isinstance(v, str) and HEX6.fullmatch(v)): return v
    raise ValueError(f"beat {beat['_i']}: cap_accent {v!r} must be #RRGGBB, e.g. #E8203A")


def wide_html(ctx, beat, ch, words, word_html, cid):
    """two lines of heavy wide caps: the line being spoken is in the accent with a glow; a lone word is a big solo chunk"""
    a, z = wide_lines(words)
    if not z: return f'<span class="ln l0 on">{" ".join(word_html(w) for w in a)}</span>', "cap-wide solo"
    acc = cap_accent(beat) or ctx.accent; t2 =ch.get("starts", [ch["t0"]] * len(words))[len(a)] - 0.04
    ctx.add(f"tl.set('#{cid} .l0',{{color:'#ffffff',textShadow:'{WHITE_SHADOW}'}},{t2:.3f});"
            f"tl.set('#{cid} .l1',{{color:'{acc}',textShadow:'0 0 16px {rgba(acc, .6)},0 0 44px {rgba(acc, .6)}'}},{t2:.3f});")
    return (f'<span class="ln l0 on">{" ".join(word_html(w) for w in a)}</span>'
            f'<span class="ln l1">{" ".join(word_html(w) for w in z)}</span>'), "cap-wide"


# ---------------------------------------------------------------- graphics
def pop(ctx, sel, t, kind="pop", dur=0.34, ease="back.out(2)", db=None, from_scale=0.6):
    ctx.add(f"tl.fromTo('{sel}',{{scale:{from_scale},opacity:0,filter:'blur(10px)'}},{{scale:1,opacity:1,filter:'blur(0px)',duration:{dur},ease:'{ease}'}},{t:.3f});")
    if kind: ctx.fx(t, kind, db)


def rise(ctx, sel, t, dy=60, dur=0.38, kind=None):
    ctx.add(f"tl.fromTo('{sel}',{{y:{dy},opacity:0,filter:'blur(12px)'}},{{y:0,opacity:1,filter:'blur(0px)',duration:{dur},ease:'power3.out'}},{t:.3f});")
    if kind: ctx.fx(t, kind)


def g_logo(ctx, b, g, p):
    size = g.get("size", 300); plain = g.get("plain", False); t = ctx.t(g.get("t", b["_t0"] + 0.02), b)
    img = f'<img src="{ctx.img(g["src"])}" style="width:{size if plain else int(size * 0.64)}px;height:{size if plain else int(size * 0.64)}px;object-fit:contain">'
    tile = img if plain else f'<div class="tile" style="width:{size}px;height:{size}px;border-radius:{int(size * 0.25)}px">{img}</div>'
    lab = f'<div id="{p}l" class="label" style="margin-top:34px">{esc(g["label"])}</div>' if g.get("label") else ""
    pop(ctx, f"#{p}t", t); lab and rise(ctx, f"#{p}l", t + 0.08, 24, 0.3)
    strike = ""
    if g.get("strike"):
        st_ = ctx.t(g["strike"], b); strike = f'<div id="{p}x" style="position:absolute;left:-8%;top:46%;width:116%;height:18px;border-radius:9px;background:#e5484d;transform:rotate(-32deg);transform-origin:50% 50%;box-shadow:0 6px 20px rgba(229,72,77,.45)"></div>'
        ctx.add(f"tl.fromTo('#{p}x',{{scaleX:0}},{{scaleX:1,duration:0.22,ease:'power2.out'}},{st_:.3f});"); ctx.fx(st_, "error")
    return f'<div class="center"><div id="{p}t" style="position:relative">{tile}{strike}</div>{lab}</div>'


def g_logos(ctx, b, g, p):
    items = g["items"]; full = b["layout"] != "split"; big = g.get("size", 380 if full else 260); small = 96 if full else 64
    tiles, labs, row = [], [], []
    for k, it in enumerate(items):
        t = max(b["_t0"] + 0.02 * k, ctx.t(it.get("t", b["_t0"] + 0.02 + k * 0.4), b) - g.get("lead", ctx.meta.get("lead", 0.3))); src = ctx.img(it["src"])
        tiles.append(f'<div id="{p}b{k}" class="tile" style="position:absolute;inset:0;width:{big}px;height:{big}px;border-radius:{int(big * .25)}px;opacity:0"><img src="{src}"></div>')
        labs.append(f'<div id="{p}n{k}" class="label" style="position:absolute;left:0;right:0;top:0;opacity:0;font-size:inherit">{esc(it.get("label", ""))}</div>')
        row.append(f'<img id="{p}s{k}" src="{src}" style="width:{small}px;height:{small}px;object-fit:contain;opacity:0">')
        pop(ctx, f"#{p}b{k}", t, "click")
        ctx.add(f"tl.set('#{p}n{k}',{{opacity:1}},{t:.3f});")
        if k: ctx.add(f"tl.set('#{p}b{k - 1}',{{opacity:0}},{t:.3f});tl.set('#{p}n{k - 1}',{{opacity:0}},{t:.3f});")
        pop(ctx, f"#{p}s{k}", t + 0.1, None, 0.25, "back.out(3)", from_scale=0.2)
    return (f'<div class="center"><div style="position:relative;width:{big}px;height:{big}px">{"".join(tiles)}</div>'
            f'<div style="position:relative;width:900px;height:{80 if full else 60}px;margin-top:{40 if full else 30}px;font-size:{64 if full else 44}px">{"".join(labs)}</div>'
            f'<div style="display:flex;gap:22px;margin-top:26px;height:{small}px;align-items:center">{"".join(row)}</div></div>')


def g_hub(ctx, b, g, p):
    zone_h = 740 if b["layout"] == "split" else (1500 if b.get("caption") == "none" else 1010); cxy = (480, zone_h / 2); R = g.get("radius", min(300, zone_h / 2 - 90))
    nodes = g["nodes"]; n = len(nodes); svg, parts = [], []
    ct = ctx.t(g.get("t", b["_t0"] + 0.02), b)
    csz = g.get("center_size", 210)
    parts.append(f'<div id="{p}c" class="tile" style="position:absolute;left:{cxy[0] - csz / 2}px;top:{cxy[1] - csz / 2}px;width:{csz}px;height:{csz}px;border-radius:{csz * .26}px"><img src="{ctx.img(g["center"])}"></div>')
    pop(ctx, f"#{p}c", ct)
    for k, nd in enumerate(nodes):
        a = -math.pi / 2 + 2 * math.pi * k / n; x, y = cxy[0] + R * math.cos(a), cxy[1] + R * math.sin(a)
        t = max(ct + 0.1, ctx.t(nd.get("t", ct + 0.25 + 0.2 * k), b) - g.get("lead", ctx.meta.get("lead", 0.3)))
        L = math.hypot(x - cxy[0], y - cxy[1])
        svg.append(f'<line id="{p}ln{k}" x1="{cxy[0]:.0f}" y1="{cxy[1]:.0f}" x2="{x:.0f}" y2="{y:.0f}" stroke="#b9b9c0" stroke-width="4" stroke-dasharray="10 12" style="stroke-dashoffset:{L:.0f}"/>')
        ctx.add(f"tl.fromTo('#{p}ln{k}',{{strokeDashoffset:{L:.0f}}},{{strokeDashoffset:0,duration:0.3,ease:'power1.out'}},{t - 0.12:.3f});")
        sz = g.get("node_size", 124)
        lab = f'<div class="label" style="font-size:26px;margin-top:10px;white-space:nowrap">{esc(nd["label"])}</div>' if nd.get("label") else ""
        parts.append(f'<div id="{p}n{k}" class="center" style="position:absolute;left:{x - 90}px;top:{y - sz / 2}px;width:180px"><div class="tile" style="width:{sz}px;height:{sz}px;border-radius:{sz * .28}px"><img src="{ctx.img(nd["src"])}"></div>{lab}</div>')
        pop(ctx, f"#{p}n{k}", t, "tick", 0.3)
    return f'<div style="position:relative;width:960px;height:{zone_h}px"><svg width="960" height="{zone_h}" style="position:absolute;inset:0">{"".join(svg)}</svg>{"".join(parts)}</div>'


def odometer(ctx, p, text, t, dur, size, font):
    """rolling digits (short 6-digit roll, right-to-left stagger); non-digits static. Deterministic: transforms only."""
    out = []; k = 0; digits = [c for c in text if c.isdigit()]
    for c in text:
        if c.isdigit():
            d = int(c); strip = "".join(f"<span>{n % 10}</span>" for n in range(0, 20))
            out.append(f'<span class="dg"><span id="{p}d{k}" class="strip">{strip}</span></span>')
            delay = (len(digits) - 1 - k) * 0.035
            ctx.add(f"tl.fromTo('#{p}d{k}',{{yPercent:{-(d + 4) * 5}}},{{yPercent:{-(d + 10) * 5},duration:{dur:.2f},ease:'power3.out'}},{t + delay:.3f});")
            k += 1
        else:
            out.append(f'<span class="nd">{"&nbsp;" if c == " " else esc(c)}</span>')   # a plain space collapses inside the digit row
    ctx.fx(t, "count"); ctx.fx(t + dur + 0.035 * max(0, len(digits) - 1), "click")   # the roll locks with a click
    return f'<span class="odo" style="font:{font};font-size:{size}px">{"".join(out)}</span>'


def g_counter(ctx, b, g, p):
    t = ctx.t(g.get("t", b["_t0"] + 0.05), b); dur = g.get("dur", 0.7); size = g.get("size", 230)
    font = "italic 900 1em var(--caps-font), serif" if g.get("font") == "serif" else "800 1em 'Inter', sans-serif"
    dark = b.get("_dark"); color = g.get("color", "#fff" if dark else "var(--ink)")
    if g.get("font") == "serif" or not g.get("roll", True):
        num = f'<span id="{p}num" style="display:inline-block;white-space:nowrap;font:{font};font-size:{size}px;line-height:1.1;padding:0 0.08em">{esc(g["text"])}</span>'
        ctx.add(f"fit('#{p}num',960);")   # "$20 000" must never wrap onto two lines
        ctx.add(f"tl.fromTo('#{p}num',{{scale:0.7,opacity:0,filter:'blur(14px)'}},{{scale:1,opacity:1,filter:'blur(0px)',duration:0.42,ease:'back.out(1.6)'}},{t:.3f});"); ctx.fx(t, "hero")
    else:
        num = odometer(ctx, p, str(g["text"]), t, dur, size, font)
    if g.get("label") and g.get("label_style") == "serif":
        lab = f'<div id="{p}l" style="font:italic 500 {g.get("label_size", 64)}px/1.05 \'Playfair Display\',serif;color:var(--accent);margin-top:16px">{esc(g["label"])}</div>'
    else:
        lab = f'<div id="{p}l" class="mono" style="font-size:30px;letter-spacing:0.28em;color:{"#9a9ba3" if dark else "#6b6c72"};margin-top:22px;text-transform:uppercase">{esc(g["label"])}</div>' if g.get("label") else ""
    over = f'<div class="over">{esc(g["over"])}</div>' if g.get("over") else ""
    lab and rise(ctx, f"#{p}l", ctx.t(g["label_t"], b) if g.get("label_t") else t + 0.2, 20, 0.3)
    body = f'<div class="center" style="color:{color};position:relative;z-index:1">{over}<div>{num}</div>{lab}</div>'
    if g.get("bg_src"):
        # the blurred source sits in the frame's media layer (full 1080×1920), not inside the zone, so nothing is left uncovered
        rel = ctx.img(g["bg_src"]); t0b, t1b = b["_t0"], b["_t1"]
        ctx.media.append(f'<div id="{p}bgs" style="position:absolute;inset:-90px;opacity:0;background:url({rel}) center/cover;filter:blur(24px) brightness(0.3) saturate(1.15)"></div>'
                         f'<div id="{p}bgo" style="position:absolute;inset:0;opacity:0;background:radial-gradient(80% 45% at 50% 45%,rgba(0,0,0,.15),rgba(0,0,0,.55))"></div>')
        ctx.add(f"tl.set(['#{p}bgs','#{p}bgo'],{{opacity:1}},{t0b:.3f});tl.set(['#{p}bgs','#{p}bgo'],{{opacity:0}},{t1b:.3f});")
        ctx.add(f"tl.fromTo('#{p}bgs',{{scale:1.15,y:0}},{{scale:1.08,y:-40,duration:{t1b - t0b:.2f},ease:'none'}},{t0b:.3f});")
        return body.replace(f'color:{color};', 'color:#fff;', 1) if "color" not in g else body
    return body


def measured_title_layout(ctx, beat, nominal_size):
    """Place a headline from tagged reference bounds inside the output safe area."""
    bounds = getattr(ctx, "style", {}).get("graphics", {}).get("title_bounds_by_layout", {}).get(beat["layout"])
    if not isinstance(bounds, dict) or not all(isinstance(bounds.get(k), (int, float)) for k in ("x", "y", "w", "h")):
        return "", 960, nominal_size
    width = int(max(540, min(960, bounds["w"] * W * 1.15)))
    height = max(90, min(400, bounds["h"] * H))
    cx = max(54 + width / 2, min(1026 - width / 2, bounds["x"] * W))
    cy = max(192 + height / 2, min(int(H * .83) - height / 2, bounds["y"] * H))
    zone_y = 96 if beat["layout"] == "split" else (210 if beat.get("caption") == "none" else 170)
    size = int(max(nominal_size * .85, min(nominal_size * 1.15, height / 1.05)))
    css = f"position:absolute;left:{cx - 60:.0f}px;top:{cy - zone_y:.0f}px;transform:translate(-50%,-50%);width:{width}px;"
    return css, width, size


def title_motion(ctx, graphic):
    if graphic.get("motion"): return graphic["motion"]
    shares = getattr(ctx, "style", {}).get("graphics", {}).get("motion_share") or {}
    if not shares: return None
    motion, share = max(shares.items(), key=lambda item: item[1])
    return motion if isinstance(share, (int, float)) and share >= .45 and motion in ("pop", "slide", "type", "scale", "fade") else None


def g_title(ctx, b, g, p):
    t = ctx.t(g.get("t", b["_t0"] + 0.02), b); dark = b.get("_dark"); ink = "#fff" if dark else "var(--ink)"
    font = g.get("font", "caps"); nominal_size = g.get("size", {"caps": 150, "pixel": 118, "block": 84, "heavy": 130, "sans": 160, "serif": 120, "wide": 120}[font])
    root_style, title_width, measured_size = measured_title_layout(ctx, b, nominal_size)
    size = nominal_size if g.get("size") is not None else measured_size
    motion = title_motion(ctx, g)
    color = g.get("color", {"caps": "var(--accent)", "pixel": ink, "block": ink, "heavy": ink, "sans": ink, "serif": "var(--accent)", "wide": "var(--accent)"}[font])
    css = {"caps": f"italic 900 {size}px/0.92 var(--caps-font),serif;text-transform:uppercase;letter-spacing:-0.015em",
           "pixel": f"700 {size}px/1.02 'Pixelify Sans',monospace;letter-spacing:0.01em",
           "heavy": f"italic 900 {size}px/1 'Playfair Display',serif;letter-spacing:-0.02em",
           "block": f"400 {size}px/1.2 'Press Start 2P',monospace;letter-spacing:0.02em;text-transform:uppercase",
           "sans": f"900 {size}px/0.9 'Inter',sans-serif;letter-spacing:-0.045em",
           "serif": f"italic 500 {size}px/1 'Playfair Display',serif;letter-spacing:-0.01em",
           "wide": f"900 {size}px/1 'Unbounded',sans-serif;letter-spacing:0.06em;text-transform:uppercase"}[font]
    text = g["text"]; hl = g.get("highlight") or []
    body = esc(text)
    for k, h in enumerate(hl):
        if h in text:
            body = body.replace(esc(h), f'<span class="mark"><i id="{p}m{k}" class="mk"></i>{esc(h)}</span>', 1)
            ctx.add(f"tl.fromTo('#{p}m{k}',{{scaleX:0}},{{scaleX:1,duration:0.28,ease:'power2.out'}},{t + 0.3 + 0.15 * k:.3f});"); ctx.fx(t + 0.3 + 0.15 * k, "swipe")
    parts = []
    it_, ot_ = ctx.t(g.get("icon_t", t), b), ctx.t(g.get("over_t", t), b)   # icon on the cut, "IT'S CALLED" on its word, the name on its word (text_t)
    if g.get("text_t"): t = ctx.t(g["text_t"], b)
    if g.get("icon"):
        isz = g.get("icon_size", 260); parts.append(f'<img id="{p}i" src="{ctx.img(g["icon"])}" style="width:{isz}px;height:{isz}px;object-fit:contain;margin-bottom:34px">'); pop(ctx, f"#{p}i", it_, "pop")
    if g.get("over") and g.get("over_style") == "caps":
        # the "IT'S CALLED" title: heavy italic serif caps, accent → pale tint gradient, zooms in from blur
        top, bot = g.get("over_color", ctx.accent), mix(g.get("over_color", ctx.accent), "#ffffff", 0.72)
        parts.append(f'<div id="{p}o" style="font:italic 900 {g.get("over_size", 92)}px/1 var(--caps-font),serif;text-transform:uppercase;letter-spacing:-0.01em;'
                     f'background:linear-gradient(180deg,{top} 0%,{bot} 100%);-webkit-background-clip:text;background-clip:text;color:transparent;padding:0 0.1em;margin-bottom:30px">{esc(g["over"])}</div>')
        ctx.add(f"tl.fromTo('#{p}o',{{scale:1.35,opacity:0,filter:'blur(16px)'}},{{scale:1,opacity:1,filter:'blur(0px)',duration:0.32,ease:'power3.out'}},{ot_:.3f});"); ctx.fx(ot_, "whoosh_soft")
    elif g.get("over"):
        parts.append(f'<div id="{p}o" class="over" style="font-size:{g.get("over_size", 64)}px;color:{g.get("over_color", "var(--ink-2)" if not dark else "rgba(255,255,255,.65)")}">{esc(g["over"])}</div>'); rise(ctx, f"#{p}o", ot_, 24, 0.3)
    grad = f"background:linear-gradient(180deg,{color} 0%,{rgba(ctx.accent, .55) if 'accent' in color else '#9a9aa2'} 100%);-webkit-background-clip:text;background-clip:text;color:transparent;" if g.get("gradient") else f"color:{color};"
    parts.append(f'<div id="{p}x" style="font:{css};{grad}text-align:center;max-width:{title_width}px">{body}</div>')
    if g.get("decode"):
        dt = t + (0.28 if g.get("over") or g.get("icon") else 0.05)   # the name resolves after "IT'S CALLED" / the icon land
        dd = g.get("decode_dur", round(min(0.7, max(0.3, (b["_t1"] - dt) * 0.5)), 2))   # resolved well before the cut
        ctx.add(f"tl.fromTo('#{p}x',{{opacity:0}},{{opacity:1,duration:0.01}},{dt:.3f});decode('#{p}x',{dt:.3f},{dd});"); ctx.fx(dt, "glitch")
        if g.get("over_style") == "caps": ctx.fx(dt + dd, "hero")   # "IT'S CALLED X": the name landing is a hero moment
    elif motion == "type" or (motion is None and font in ("pixel", "block") and g.get("type_on", True)):
        ctx.add(f"typeOn('#{p}x',{t + 0.05:.3f},{g.get('cps', 26)});"); ctx.fx(t + 0.05, "typing")
    elif motion == "slide":
        rise(ctx, f"#{p}x", t, 56, 0.38, "whoosh_soft")
    elif motion == "fade":
        ctx.add(f"tl.fromTo('#{p}x',{{opacity:0}},{{opacity:1,duration:0.28,ease:'power1.out'}},{t:.3f});")
    else:
        delay = 0 if g.get("text_t") else (0.12 if g.get("icon") or g.get("over") else 0)
        pop(ctx, f"#{p}x", t + delay, None if g.get("icon") else "pop", 0.3, "back.out(1.6)", from_scale=0.85)
    if g.get("sub"):
        st_ = ctx.t(g.get("sub_t", t + 0.25), b); sfont = {"pixel": "font-family:'Pixelify Sans',monospace;font-weight:700;", "block": "font-family:'Press Start 2P',monospace;font-weight:400;letter-spacing:0.02em;"}.get(g.get("sub_font"), "")
        scol = g.get("sub_color", ink)
        parts.append(f'<div id="{p}s" class="label" style="margin-top:26px;font-size:{g.get("sub_size", 52)}px;color:{scol};{sfont}">{esc(g["sub"])}</div>')
        if g.get("sub_type"): ctx.add(f"typeOn('#{p}s',{st_:.3f},{g.get('cps', 18)});"); ctx.fx(st_, "typing")
        else: rise(ctx, f"#{p}s", st_, 20, 0.3)
    ctx.add(f"fit('#{p}x',{title_width});")
    root_attr = f' style="{root_style}"' if root_style else ""
    return f'<div class="center"{root_attr}>{"".join(parts)}</div>'


def g_widget(ctx, b, g, p):
    t = ctx.t(g.get("t", b["_t0"] + 0.02), b); p0, p1 = g.get("progress", [0.1, 0.96]); dur = max(0.4, b["_t1"] - t - 0.1)
    icon = f'<div id="{p}i" style="width:230px;height:230px;border-radius:58px;background:var(--accent);box-shadow:0 0 0 12px {rgba(ctx.accent, .25)},var(--shadow);display:flex;align-items:center;justify-content:center"><img src="{ctx.img(g["icon"])}" style="width:62%;height:62%;object-fit:contain"></div>'
    pop(ctx, f"#{p}i", t, "pop")
    name = f'<div class="label" style="margin-top:30px;font-size:46px">{esc(g.get("name", ""))}</div>'
    bar = (f'<div id="{p}w" style="width:600px;margin-top:34px"><div class="mono" style="display:flex;justify-content:space-between;font-size:20px;letter-spacing:.18em;color:#8b8c93;margin-bottom:12px">'
           f'<span>{esc(g.get("status", "PROCESSING"))}</span><span>{int(p1 * 100)}%</span></div><div class="prog"><i id="{p}b"></i></div></div>')
    rise(ctx, f"#{p}w", t + 0.1, 16, 0.3)
    ctx.add(f"tl.fromTo('#{p}b',{{scaleX:{p0}}},{{scaleX:{p1},duration:{dur:.2f},ease:'power1.inOut'}},{t + 0.1:.3f});")
    if p1 >= 0.99: ctx.fx(t + 0.1 + dur, "ding")
    return f'<div class="center">{icon}{name}{bar}</div>'


def g_terminal(ctx, b, g, p):
    t = ctx.t(g.get("t", b["_t0"] + 0.02), b); lines = []
    rise(ctx, f"#{p}w", t, 40, 0.3, "whoosh_soft" if b["layout"] != "split" else None)
    for k, ln in enumerate(g["lines"]):
        lt = ctx.t(ln.get("t", t + 0.25 + k * 0.45), b); txt = ln["text"]; color = ln.get("color", "#dfe1e6")
        if ln.get("prompt", k == 0): txt_html = f'<span style="color:var(--accent)">&gt; </span><span id="{p}y{k}" class="typed" style="width:0ch">{esc(txt)}</span>'
        else: txt_html = f'<span id="{p}y{k}" style="color:{color}">{esc(txt)}</span>'
        lines.append(f'<span id="{p}l{k}" class="ln" style="opacity:0">{txt_html}</span>')
        ctx.add(f"tl.set('#{p}l{k}',{{opacity:1}},{lt:.3f});")
        if ln.get("prompt", k == 0):
            n = len(txt); d = min(1.2, 0.03 * n + 0.1)
            ctx.add(f"tl.fromTo('#{p}y{k}',{{width:'0ch'}},{{width:'{n}ch',duration:{d:.2f},ease:'steps({n})'}},{lt:.3f});"); ctx.fx(lt, "typing")
    w = g.get("width", 940); fs = g.get("font_size", 30 if b["layout"] == "split" else 40)
    longest = max(len(ln["text"]) + (2 if ln.get("prompt", k == 0) else 0) for k, ln in enumerate(g["lines"]))
    fs_fit = int((w - 72) / (0.61 * max(1, longest)))   # JetBrains Mono advance ≈ 0.6 em: every line must fit whole (text is never cut off)
    if fs_fit < fs: fs = max(20, fs_fit)
    if fs_fit < 20: print(f"warn: terminal line of {longest} chars does not fit even at 20 px — shorten it or split it into two lines")
    for k, ln in enumerate(g["lines"]):
        if any(m in ln["text"] for m in ("✓", "✔")): ctx.fx(ctx.t(ln.get("t", t + 0.25 + k * 0.45), b) + 0.05, "ding")
    glow = f"box-shadow:0 30px 90px rgba(0,0,0,.45),0 0 120px {rgba(ctx.accent, .35)};" if b.get("_dark") else ""
    return (f'<div id="{p}w" class="term" style="width:{w}px;{glow}"><div class="bar"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i><b>{esc(g.get("title", "Terminal"))}</b></div>'
            f'<div class="body" style="font-size:{fs}px">{"".join(lines)}</div></div>')


def g_shot(ctx, b, g, p):
    """screenshot card with optional browser chrome, highlight box and zoom-to-box (image + box share one transformed stage)"""
    t = ctx.t(g.get("t", b["_t0"] + 0.02), b); src = g["src"]; iw, ih = ctx.img_size(src)
    zone_h = 740 if b["layout"] == "split" else (1500 if b.get("caption") == "none" else 1010)
    cw = g.get("width", 940); crop = g.get("crop")  # [x,y,w,h] in image px
    cx0, cy0, cwid, chei = crop if crop else (0, 0, iw, ih)
    chrome_h = 64 if g.get("chrome") else 0
    ch = min(zone_h - 20 - chrome_h, int(cw * chei / cwid)); k = cw / cwid
    dark = g.get("dark", b.get("_dark"))
    chrome = (f'<div class="chrome"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i><div class="url">{esc(g.get("url", ""))}</div></div>' if g.get("chrome") else "")
    img = f'<img src="{ctx.img(src)}" style="position:absolute;left:{-cx0 * k:.1f}px;top:{-cy0 * k:.1f}px;width:{iw * k:.1f}px;height:{ih * k:.1f}px">'
    box = ""
    if g.get("box"):
        bx, by, bw, bh = g["box"]; bt = ctx.t(g.get("box_t", t + 0.5), b)
        X, Y, BW, BH = (bx - cx0) * k, (by - cy0) * k, bw * k, bh * k
        box = f'<div id="{p}bx" class="box" style="left:{X - 8:.1f}px;top:{Y - 8:.1f}px;width:{BW + 16:.1f}px;height:{BH + 16:.1f}px;opacity:0"></div>'
        pop(ctx, f"#{p}bx", bt, "swipe", 0.28, "back.out(2.2)", from_scale=1.12)
        if g.get("zoom"):
            z = g.get("zoom_scale", min(2.4, (cw - 80) / BW, (ch - 80) / BH)); zt = ctx.t(g.get("zoom_t", bt + 0.35), b)
            tx = cw / 2 - z * (X + BW / 2); ty = ch / 2 - z * (Y + BH / 2)
            tx = min(0, max(cw - z * cw, tx)); ty = min(0, max(ch - z * ch, ty))   # never pull the image off the card edge
            ctx.add(f"tl.to('#{p}stg',{{scale:{z:.3f},x:{tx:.1f},y:{ty:.1f},duration:0.6,ease:'power2.inOut'}},{zt:.3f});")
    rise(ctx, f"#{p}cd", t, 70, 0.38, "whoosh_soft" if g.get("sfx_in", False) else None)
    if not g.get("zoom") and g.get("drift", True):
        ctx.add(f"tl.fromTo('#{p}stg',{{scale:1,y:0}},{{scale:1.06,y:{-min(60, ch * 0.04):.0f},duration:{max(0.5, b['_t1'] - t):.2f},ease:'none',transformOrigin:'50% 30%'}},{t:.3f});")
    return (f'<div id="{p}cd" class="card{" dark" if dark else ""}" style="width:{cw}px;height:{ch + chrome_h}px">{chrome}'
            f'<div style="position:relative;width:{cw}px;height:{ch}px;overflow:hidden"><div id="{p}stg" style="position:absolute;left:0;top:0;width:{cw}px;height:{ch}px;transform-origin:0 0">{img}{box}</div></div></div>')


def g_broll(ctx, b, g, p):
    """full-frame: blurred copy as background + sharp rounded card (image or video)."""
    src = g["src"]; is_vid = src.lower().endswith((".mp4", ".mov", ".webm")); t = b["_t0"]; dur = b["_t1"] - b["_t0"]
    if is_vid:
        rel = ctx.img(src); ms = g.get("media_start", 0)
        vid = lambda vid_id, style: f'<div style="{style}"><video id="{vid_id}" src="{rel}" data-start="{t:.3f}" data-duration="{dur:.3f}" data-media-start="{ms}" muted playsinline style="width:100%;height:100%;object-fit:cover"></video></div>'
        ctx.media.append(vid(f"{p}vb", "position:absolute;inset:-80px;filter:blur(40px) brightness(0.55)") + vid(f"{p}vf", "position:absolute;left:70px;top:430px;width:940px;height:900px;border-radius:40px;overflow:hidden;box-shadow:0 40px 100px rgba(0,0,0,.5)"))
        return ""
    rel = ctx.img(src)
    rise(ctx, f"#{p}cd", t + 0.02, 50, 0.35)
    ctx.add(f"tl.fromTo('#{p}bg',{{scale:1.18}},{{scale:1.1,duration:{dur:.2f},ease:'none'}},{t:.3f});")
    return (f'<div id="{p}bg" style="position:absolute;inset:-60px;background:url({rel}) center/cover;filter:blur(38px) brightness(0.5)"></div>'
            f'<div id="{p}cd" class="card" style="position:absolute;left:70px;top:{g.get("top", 360)}px;width:940px;height:{g.get("height", 820)}px;background:url({rel}) center/cover"></div>')


def g_person(ctx, b, g, p):
    t = ctx.t(g.get("t", b["_t0"] + 0.02), b)
    rise(ctx, f"#{p}ph", t, 60, 0.4, "pop")
    over = f'<div class="over" style="font-size:46px">{esc(g.get("over", ""))}</div>' if g.get("over") else ""
    return (f'<div class="center">{over}<div id="{p}ph" class="card" style="width:{g.get("w", 640)}px;height:{g.get("h", 760)}px;background:url({ctx.img(g["src"])}) center/cover"></div>'
            f'<div class="label" style="margin-top:34px;font-size:58px">{esc(g.get("name", ""))}</div><div class="label" style="font-weight:500;font-size:34px;opacity:.7;margin-top:8px">{esc(g.get("role", ""))}</div></div>')


def g_note(ctx, b, g, p):
    t = ctx.t(g.get("t", b["_t0"] + 0.02), b); nt = ctx.t(g.get("note_t", t + 0.5), b)
    pop(ctx, f"#{p}lg", t, "pop")
    ctx.add(f"tl.fromTo('#{p}nt',{{y:-60,opacity:0,rotation:-4}},{{y:0,opacity:1,rotation:-1.5,duration:0.4,ease:'back.out(1.8)'}},{nt:.3f});"); ctx.fx(nt, "click")
    lines = "".join(f"<div>{esc(x)}</div>" for x in g.get("lines", []))
    return (f'<div class="center"><div id="{p}lg" class="tile" style="width:200px;height:200px;border-radius:50px"><img src="{ctx.img(g["logo"])}"></div>'
            f'{"<div class=label style=margin-top:18px;font-size:28px;color:#8b8c93;letter-spacing:.2em>" + esc(g["tag"]) + "</div>" if g.get("tag") else ""}'
            f'<div id="{p}nt" class="note" style="width:560px;margin-top:34px"><b>{esc(g.get("title", "Note"))}</b>{lines}</div></div>')


def g_meter(ctx, b, g, p):
    t = ctx.t(g.get("t", b["_t0"] + 0.02), b); to = g.get("to", 0.97); dur = g.get("dur", max(0.6, b["_t1"] - t - 0.2)); n = 28
    full = b["layout"] != "split"; off = "rgba(255,255,255,.14)" if b.get("_dark") else "rgba(15,15,17,.08)"
    segs = "".join(f'<i id="{p}g{k}" style="display:block;flex:1;height:{58 if full else 44}px;border-radius:6px;background:{off}"></i>' for k in range(n))
    for k in range(int(n * to)):
        col = "#e5484d" if k > n * 0.7 else "var(--accent)"
        ctx.add(f"tl.set('#{p}g{k}',{{backgroundColor:'{col}'}},{t + 0.15 + dur * k / (n * to):.3f});")
    icon = f'<img id="{p}ic" src="{ctx.img(g["icon"])}" style="width:230px;height:230px;object-fit:contain;margin-bottom:40px">' if g.get("icon") else ""
    icon and pop(ctx, f"#{p}ic", t, "pop")
    ctx.fx(t + 0.15, "count")
    if to >= 0.8: ctx.fx(t + 0.15 + dur * 0.85, "error")   # the bar hits red
    return (f'<div class="center">{icon}<div class="label" style="font-size:{46 if full else 36}px;color:#e5484d;margin-bottom:{30 if full else 22}px">⚠ {esc(g.get("label", "Low usage limit"))}</div>'
            f'<div style="display:flex;gap:{8 if full else 6}px;width:{900 if full else 780}px">{segs}</div></div>')


def g_switcher(ctx, b, g, p):
    cards = g["cards"]; seq = g.get("seq", []); t = ctx.t(g.get("t", b["_t0"] + 0.02), b)
    row = "".join(f'<div id="{p}k{k}" class="sw-card"><img src="{ctx.img(c["src"])}"><span>{esc(c.get("label", ""))}</span></div>' for k, c in enumerate(cards))
    rise(ctx, f"#{p}r", t, 40, 0.35)
    stat = [f'<div id="{p}st0" class="mono" style="position:absolute;left:0;right:0;text-align:center;font-size:28px;letter-spacing:.12em;color:#8b8c93">{esc(g.get("status", "Switching model..."))}</div>']
    shown = 0
    for k, s in enumerate(seq):
        st_ = ctx.t(s["t"], b); idx = s["index"]
        for j in range(len(cards)): ctx.add(f"tl.set('#{p}k{j}',{{className:'sw-card{' on' if j == idx else ''}'}},{st_:.3f});")
        ctx.add(f"tl.fromTo('#{p}k{idx}',{{scale:0.9}},{{scale:1.08,duration:0.25,ease:'back.out(2)'}},{st_:.3f});"); ctx.fx(st_, "click")
        if s.get("status"):
            stat.append(f'<div id="{p}st{k + 1}" class="mono" style="position:absolute;left:0;right:0;text-align:center;font-size:28px;letter-spacing:.12em;color:#22a06b;opacity:0">{esc(s["status"])}</div>')
            ctx.add(f"tl.set('#{p}st{shown}',{{opacity:0}},{st_:.3f});tl.set('#{p}st{k + 1}',{{opacity:1}},{st_:.3f});"); shown = k + 1
            if any(m in s["status"] for m in ("✓", "✔")): ctx.fx(st_ + 0.05, "chime")
    return f'<div class="center"><div style="position:relative;width:900px;height:40px;margin-bottom:40px">{"".join(stat)}</div><div id="{p}r" style="display:flex;gap:26px;align-items:center">{row}</div></div>'


def g_chart(ctx, b, g, p):
    t = ctx.t(g.get("t", b["_t0"] + 0.02), b); vals = g["bars"]; mx = max(vals)
    bars = "".join(f'<i id="{p}b{k}" style="height:{int(400 * v / mx)}px;opacity:{0.55 + 0.45 * v / mx:.2f}"></i>' for k, v in enumerate(vals))
    ctx.add(f"tl.fromTo('#{p}bars i',{{scaleY:0}},{{scaleY:1,duration:0.5,stagger:0.04,ease:'power3.out'}},{t:.3f});"); ctx.fx(t, "reveal")
    lab = ""
    if g.get("label"):
        lt = ctx.t(g.get("label_t", t + 0.6), b)
        lab = f'<div id="{p}lb" style="font:900 120px/1 Inter,sans-serif;letter-spacing:-0.04em;color:var(--accent);margin-bottom:40px">{esc(g["label"])}</div>'; pop(ctx, f"#{p}lb", lt, "pop")
    return f'<div class="center">{lab}<div id="{p}bars" class="bars">{bars}</div></div>'


def g_emoji(ctx, b, g, p):
    t = ctx.t(g.get("t", b["_t0"] + 0.02), b)
    ctx.add(f"tl.fromTo('#{p}e',{{y:120,scale:0.6,opacity:0,rotation:-12}},{{y:0,scale:1,opacity:1,rotation:0,duration:0.5,ease:'back.out(1.7)'}},{t:.3f});"); ctx.fx(t, "pop")
    return f'<div class="center"><img id="{p}e" src="{ctx.img(g["src"])}" style="width:{g.get("size", 560)}px;height:{g.get("size", 560)}px;object-fit:contain"></div>'


def g_tweet(ctx, b, g, p):
    t = ctx.t(g.get("t", b["_t0"] + 0.02), b); text = esc(g["text"])
    for k, h in enumerate(g.get("highlight", [])):
        if esc(h) in text:
            text = text.replace(esc(h), f'<span class="mark"><i id="{p}m{k}" class="mk" style="opacity:.35"></i>{esc(h)}</span>', 1)
            ctx.add(f"tl.fromTo('#{p}m{k}',{{scaleX:0}},{{scaleX:1,duration:0.3,ease:'power2.out'}},{t + 0.45:.3f});")
    rise(ctx, f"#{p}cd", t, 60, 0.36, "pop")
    ava = f'<img src="{ctx.img(g["avatar"])}" style="width:92px;height:92px;border-radius:50%;object-fit:cover">' if g.get("avatar") else ""
    return (f'<div id="{p}cd" class="card" style="width:920px;padding:40px 44px"><div style="display:flex;gap:22px;align-items:center">{ava}'
            f'<div><div style="font:800 36px Inter">{esc(g.get("name", ""))} <span style="color:#1d9bf0">✔</span></div><div style="font:500 30px Inter;color:#6b6c72">@{esc(g.get("handle", ""))}</div></div></div>'
            f'<div style="font:500 38px/1.38 Inter;color:#0f0f11;margin-top:26px;white-space:pre-wrap">{text}</div>'
            f'{chr(60) + "div style=" + chr(34) + "font:500 28px Inter;color:#6b6c72;margin-top:24px" + chr(34) + chr(62) + esc(g["meta"]) + "</div>" if g.get("meta") else ""}</div>')


def g_html(ctx, b, g, p):
    """bespoke graphic for anything the kit lacks (before/after, slot list, custom mini-UI).
    g.html: markup; g.js: list of GSAP lines using the shared timeline `tl`; g.sfx: [{t, kind, db}].
    Tokens inside html/js: {p} → unique id prefix of this beat, {t:SPEC} → seconds (SPEC = 12.3 | w:N | +0.4 | word:X),
    {img:assets/x.png} → staged image url, {accent} → accent colour."""
    def sub(s):
        s = s.replace("{p}", p).replace("{accent}", ctx.accent)
        s = re.sub(r"\{img:([^}]+)\}", lambda m: ctx.img(m.group(1).strip()), s)
        return re.sub(r"\{t:([^}]+)\}", lambda m: f"{ctx.t(m.group(1).strip(), b):.3f}", s)
    for line in g.get("js") or []: ctx.add(sub(line))
    for e in g.get("sfx") or []: ctx.fx(ctx.t(e["t"], b), e.get("kind", "pop"), e.get("db"), e.get("dur"))
    return sub(g["html"])


def g_none(ctx, b, g, p):
    return ""


GFX = dict(logo=g_logo, logos=g_logos, hub=g_hub, counter=g_counter, title=g_title, widget=g_widget, terminal=g_terminal, shot=g_shot,
           broll=g_broll, person=g_person, note=g_note, meter=g_meter, switcher=g_switcher, chart=g_chart, emoji=g_emoji, tweet=g_tweet, html=g_html, none=g_none,
           ui=lambda ctx, b, g, p: gfx_ui.g_ui(ctx, b, g, p, HELP), comment=lambda ctx, b, g, p: gfx_ui.g_comment(ctx, b, g, p, HELP))
HELP = dict(esc=esc, rgba=rgba, odometer=odometer, rise=rise)
FACE_FULL = ("ui", "comment")   # on a face beat these are placed in frame coordinates, above the speaker


# ---------------------------------------------------------------- assemble
def build(P):
    ctx = Ctx(P); beats = ctx.plan["beats"]; D = ctx.dur
    for k, v in (ctx.style.get("framing") or {}).items():   # the style profile's measured framing
        if isinstance(v, dict) and {"w", "eye", "cx"} <= set(v): FRAME[k] = dict(w=float(v["w"]), eye=float(v["eye"]), cx=float(v["cx"]))
    for i, b in enumerate(beats):
        b["_i"] = i; b["_t0"] = ctx.t(b["t0"]) if i else 0.0
    for i, b in enumerate(beats):
        b["_t1"] = beats[i + 1]["_t0"] if i + 1 < len(beats) else D
        if b["_t1"] - b["_t0"] < 0.2: raise SystemExit(f"beat {i} too short: {b['_t0']:.2f}-{b['_t1']:.2f}")
        bgc = BG.get(b.get("bg", "white"), b.get("bg", "white")) if b["layout"] != "face" else "#000000"
        if b.get("bg") == "accent": bgc = ctx.accent
        b["_bg"] = bgc; b["_dark"] = lum(bgc) < 0.45
    smax_face = ctx.meta.get("face_scale_max", 2.2); smax_split = ctx.meta.get("split_scale_max", 1.8); era25 = str(ctx.meta.get("era", "2026")) == "2025"
    beats_html, over_html, caps_html, caption_qa = [], [], [], []; ci = 0; prev_layout = None
    if ctx.meta.get("open_punch"):   # 2025 opening (reels 23, 24): the whole frame punches in from 1.12x with a zoom blur over 0.25 s
        ctx.add("tl.fromTo(['#gfx','#plate','#cut','#over'],{scale:1.12,filter:'blur(8px)'},{scale:1,filter:'blur(0px)',duration:0.25,ease:'power2.out'},0);")
    if ctx.meta.get("flash_start"):
        ctx.media.append('<div id="leakflash" style="position:absolute;inset:0;z-index:41;background:#fff;opacity:0"></div>')
        ctx.add("tl.fromTo('#leakflash',{opacity:0.95},{opacity:0,duration:0.12,ease:'power1.out'},0);")
    TRM = ctx.meta.get("trans", "auto")   # auto | fade | cut: how scenes change (auto = soft moves + whooshes; cut = hard cuts)
    FULL = "inset(0px 0px 0px 0px round 0px 0px 0px 0px)"
    ARCHC = f"inset({ARCH['top']}px {ARCH['side']}px 0px {ARCH['side']}px round {ARCH['r']}px {ARCH['r']}px 0px 0px)"
    SEAMC = f"inset({SEAM25}px 0px 0px 0px round 0px 0px 0px 0px)"
    def trans_of(k):
        if k == 0: return "cut"
        t = beats[k].get("trans") or TRM
        if t == "auto":
            a, c = beats[k - 1]["layout"], beats[k]["layout"]
            return "punch" if {a, c} <= {"split", "face"} and a != c else ("zoom" if a == c else "fade")
        return t
    for k, b in enumerate(beats): b["_tr"] = trans_of(k)
    TR = 0.2; prev = None   # prev = head state at the end of the previous beat
    for b in beats:
        i, t0, t1, lay = b["_i"], b["_t0"], b["_t1"], b["layout"]; p = f"b{i}-"; tr = b["_tr"]
        pbg = beats[i - 1]["_bg"] if i else b["_bg"]
        if tr in ("cut", "flash", "blur", "punch") or i == 0: ctx.add(f"tl.set('#bg',{{backgroundColor:'{b['_bg']}'}},{t0:.3f});")   # a punch covers the frame at once: no grey band
        else: ctx.add(f"tl.fromTo('#bg',{{backgroundColor:'{pbg}'}},{{backgroundColor:'{b['_bg']}',duration:{TR},ease:'power1.inOut'}},{t0:.3f});")
        moving = lay in ("split", "face") and face_moves(ctx, t0, t1)
        fc = face_at(ctx, t0, min(t1, t0 + 0.25)) if moving else face_at(ctx, t0, t1)
        push = None; mask = None; mode = None
        if lay == "split" and era25:
            mode = "split25"; tx, ty, s = transform(fc, mode, smax_split); cur = dict(plate=1, cut=0, clip=SEAMC, x=tx, y=ty, s=s)
        elif lay == "split":
            mode = "split"; tx, ty, s = transform(fc, mode, smax_split); cur = dict(plate=1, cut=1, clip=ARCHC, x=tx, y=ty, s=s)
            hair = ty + s * (fc["top"] - 0.6 * fc["h"]); m0 = int(min(ARCH["top"] - 80, max(ARCH["top"] - POP - 60, hair - 70))); m1 = m0 + 55
            mask = f"linear-gradient(to bottom,transparent {m0}px,#000 {m1}px)"
        elif lay == "face":
            mode = "medium" if b.get("zoom") == "medium" else ("close25" if era25 else "close")
            tx, ty, s = transform(fc, mode, smax_face); s2 = min(smax_face * 1.04, s * 1.035)
            tx2, ty2 = round(FRAME[mode]["cx"] - s2 * fc["cx"], 1), round(FRAME[mode]["eye"] - s2 * fc["eye"], 1)
            tx2 = min(tx2, 0); tx2 = max(tx2, W - s2 * W); ty2 = min(ty2, 0); ty2 = max(ty2, H - s2 * H)
            cur = dict(plate=1, cut=0, clip=FULL, x=tx, y=ty, s=s)
            if not moving: push = (tx2, ty2, s2)
        else:
            cur = dict(plate=0, cut=0, clip=(prev or {}).get("clip", ARCHC), x=(prev or {}).get("x", 0), y=(prev or {}).get("y", 0), s=(prev or {}).get("s", 1))
        if mask: ctx.add(f"tl.set('#cut',{{webkitMaskImage:'{mask}',maskImage:'{mask}'}},{t0:.3f});")
        zoom_open = i == 0 and lay == "split" and not era25 and ctx.meta.get("open_zoom")
        st = lambda d: f"x:{d['x']},y:{d['y']},scale:{d['s']}"
        head_t = t0   # when the face push-in may start
        if zoom_open:
            # opening move (reels 08, 09): the speaker starts as a full-frame close-up and snaps into the arch in ~6 frames with motion blur
            cx0, cy0, cs0 = transform(fc, "close", smax_face)
            ctx.add(f"tl.set('#plate',{{opacity:1}},0);tl.set('#cut',{{opacity:1}},0);")
            ctx.add(f"tl.fromTo(['#plate-inner','#cut-inner'],{{x:{cx0},y:{cy0},scale:{cs0}}},{{{st(cur)},duration:0.2,ease:'power3.out'}},0);")
            ctx.add(f"tl.fromTo('#plate',{{clipPath:'{FULL}'}},{{clipPath:'{cur['clip']}',duration:0.2,ease:'power3.out'}},0);")
            ctx.add("tl.fromTo(['#plate','#cut'],{filter:'blur(7px)'},{filter:'blur(0px)',duration:0.22,ease:'power2.out'},0);")
            head_t = max(head_t, 0.2)
        elif prev is None or tr in ("cut", "flash", "blur", "leak"):
            ctx.add(f"tl.set('#plate',{{opacity:{cur['plate']},clipPath:'{cur['clip']}'}},{t0:.3f});tl.set('#cut',{{opacity:{cur['cut']}}},{t0:.3f});")
            if cur["plate"]: ctx.add(f"tl.set(['#plate-inner','#cut-inner'],{{{st(cur)}}},{t0:.3f});")
        elif prev["plate"] and cur["plate"]:
            # punch-in / pull-out: the camera moves from the old framing to the new one, the arch opens or closes, a short motion blur hides the jump
            TP = 0.2; head_t = t0 + TP
            ctx.add(f"tl.fromTo(['#plate-inner','#cut-inner'],{{{st(prev)}}},{{{st(cur)},duration:{TP},ease:'power3.out'}},{t0:.3f});")
            if prev["clip"] != cur["clip"]: ctx.add(f"tl.fromTo('#plate',{{clipPath:'{prev['clip']}'}},{{clipPath:'{cur['clip']}',duration:0.12,ease:'power2.out'}},{t0:.3f});")
            ctx.add(f"tl.set('#plate',{{opacity:1}},{t0:.3f});tl.fromTo('#plate',{{filter:'blur(6px)'}},{{filter:'blur(0px)',duration:0.24,ease:'power2.out',immediateRender:false}},{t0:.3f});")   # without immediateRender:false the speaker is blurred from frame 0
            if prev["cut"] and not cur["cut"]: ctx.add(f"tl.fromTo('#cut',{{opacity:1}},{{opacity:0,duration:0.1}},{t0:.3f});")
            elif cur["cut"] and not prev["cut"]: ctx.add(f"tl.fromTo('#cut',{{opacity:0}},{{opacity:1,duration:0.12}},{t0 + 0.1:.3f});")
            else: ctx.add(f"tl.set('#cut',{{opacity:{cur['cut']}}},{t0:.3f});")
        elif cur["plate"]:
            # the speaker fades in over a graphic
            ctx.add(f"tl.set('#plate',{{clipPath:'{cur['clip']}'}},{t0:.3f});tl.set(['#plate-inner','#cut-inner'],{{{st(cur)}}},{t0:.3f});")
            ctx.add(f"tl.fromTo('#plate',{{opacity:0}},{{opacity:1,duration:{TR},ease:'power1.out'}},{t0:.3f});")
            ctx.add(f"tl.fromTo('#cut',{{opacity:0}},{{opacity:{cur['cut']},duration:{TR},ease:'power1.out'}},{t0:.3f});")
        elif prev["plate"]:
            # the speaker fades out under the incoming graphic
            ctx.add(f"tl.fromTo('#plate',{{opacity:1}},{{opacity:0,duration:{TR},ease:'power1.in'}},{t0:.3f});tl.fromTo('#cut',{{opacity:{prev['cut']}}},{{opacity:0,duration:{TR},ease:'power1.in'}},{t0:.3f});")
        else:
            ctx.add(f"tl.set(['#plate','#cut'],{{opacity:0}},{t0:.3f});")
        if moving and mode and cur["plate"]:
            # The old renderer framed the median face once per beat. Follow a
            # walking speaker at the face track's 2 fps with linear camera
            # moves, including the cutout layer in the split layout.
            track_times = [f["t"] for f in ctx.face if head_t + 0.05 < f["t"] < t1 - 0.05]
            track_times.append(t1)
            start_t = head_t; end_state = (cur["x"], cur["y"], cur["s"])
            for target_t in track_times:
                target_face = face_at(ctx, target_t, target_t)
                end_state = transform(target_face, mode, smax_split if lay == "split" else smax_face)
                duration = target_t - start_t
                if duration > 0.01:
                    ctx.add(f"tl.to(['#plate-inner','#cut-inner'],{{x:{end_state[0]},y:{end_state[1]},scale:{end_state[2]},duration:{duration:.3f},ease:'none'}},{start_t:.3f});")
                start_t = target_t
            prev = dict(cur, x=end_state[0], y=end_state[1], s=end_state[2])
        elif push:
            ctx.add(f"tl.fromTo('#plate-inner',{{{st(cur)}}},{{x:{push[0]},y:{push[1]},scale:{push[2]:.4f},duration:{max(0.1, t1 - head_t):.3f},ease:'none'}},{head_t:.3f});")
            prev = dict(cur, x=push[0], y=push[1], s=push[2])
        else: prev = cur
        # scene-change sound: a whoosh on every change of layout, a soft one when only the graphic changes (hard "cut" transitions stay silent)
        if i and tr != "cut":   # the sound follows the move: a punch-in/out is a low whoomp, a fade a whoosh, a zoom between graphics a soft swish
            gt = (b.get("gfx") or {}).get("type")
            snd = {"punch": "whoosh_low", "zoom": "whoosh_soft"}.get(tr) or ("swipe" if gt in ("shot", "tweet", "broll") else "whoosh" if beats[i - 1]["layout"] != lay else "whoosh_soft")
            sound_style = ctx.style.get("sound", {})
            measured_offset = sound_style.get("sfx_cut_offset_s", {})
            offset = ctx.meta.get("sfx_cut_offset_s")
            if offset is None and sound_style.get("sfx_timing_verified") and isinstance(measured_offset, dict):
                offset = measured_offset.get("median")
            if offset is None: offset = -0.04
            ctx.fx(max(0, t0 + max(-0.3, min(0.3, float(offset)))), snd)
        elif era25 and i and i % 3 == 0: ctx.fx(t0, "whoosh_soft")
        if tr == "flash":
            fl = f"flash{i}"; ctx.media.append(f'<div id="leak{fl}" style="position:absolute;inset:0;z-index:41;background:#fff;opacity:0"></div>')
            ctx.add(f"tl.fromTo('#leak{fl}',{{opacity:0.9}},{{opacity:0,duration:0.14,ease:'power1.out',immediateRender:false}},{t0:.3f});")   # without immediateRender:false the white sheet sits over every earlier frame
        if tr == "blur":
            ctx.add(f"tl.fromTo(['#gfx','#plate','#cut','#over'],{{filter:'blur(14px)',scale:1.06}},{{filter:'blur(0px)',scale:1,duration:0.24,ease:'power2.out',immediateRender:false}},{t0:.3f});")
        if tr == "leak" or (lay == "face" and ctx.meta.get("leaks") and beats[i - 1]["layout"] != "face" and i):
            lk = f"leak{i}"; ctx.media.append(f'<div id="{lk}" style="position:absolute;inset:0;z-index:40;opacity:0;mix-blend-mode:screen;background:radial-gradient(120% 70% at 85% 20%,rgba(255,150,60,.95),rgba(255,60,120,.55) 45%,rgba(0,0,0,0) 75%)"></div>')
            ctx.add(f"tl.fromTo('#{lk}',{{opacity:0}},{{opacity:0.9,duration:0.16,ease:'power2.out'}},{t0 - 0.16:.3f});tl.to('#{lk}',{{opacity:0,duration:0.42,ease:'power2.in'}},{t0:.3f});")
            if tr == "cut": ctx.fx(t0 - 0.12, "whoosh_soft")
        prev_layout = lay
        g = b.get("gfx") or {"type": "none"}
        full = g["type"] in ("broll",) or (lay == "face" and g["type"] in FACE_FULL)
        zone = "zone-split" if lay == "split" else ("zone-full" if full else ("zone-graphic-nocap" if b.get("caption") == "none" else "zone-graphic"))
        inner = GFX[g["type"]](ctx, b, g, p) if lay != "face" else (GFX[g["type"]](ctx, b, g, p) if g["type"] != "none" else "")
        up = {"widget": 1.35, "note": 1.3, "switcher": 1.12}.get(g["type"])   # these are sized for the split's top zone
        if lay == "graphic" and up and g.get("scale", True) is not False:
            inner = f'<div style="transform:scale({g["scale"] if isinstance(g.get("scale"), (int, float)) and g["scale"] is not True else up});transform-origin:50% 50%">{inner}</div>'
        if inner or lay != "face":
            nxt = beats[i + 1]["_tr"] if i + 1 < len(beats) else "cut"
            ov = TR if nxt in ("fade", "zoom", "punch") else 0.0   # the outgoing graphic stays TR s longer and fades under the incoming one
            (over_html if lay == "face" else beats_html).append(f'<section id="{p}sec" class="clip beat{" on-dark" if b["_dark"] else ""}" data-start="{t0:.3f}" data-duration="{min(t1 + ov, D) - t0:.3f}" data-track-index="2">'
                              f'<div class="zone {zone}">{inner}</div></section>')
            if i and tr in ("fade", "punch"): ctx.add(f"tl.fromTo('#{p}sec > .zone',{{opacity:0,filter:'blur(8px)'}},{{opacity:1,filter:'blur(0px)',duration:{TR},ease:'power1.out'}},{t0:.3f});")
            if i and tr == "zoom": ctx.add(f"tl.fromTo('#{p}sec > .zone',{{opacity:0,scale:0.9,filter:'blur(10px)'}},{{opacity:1,scale:1,filter:'blur(0px)',duration:{TR + 0.04},ease:'power2.out'}},{t0:.3f});")
            if ov: ctx.add(f"tl.to('#{p}sec > .zone',{{opacity:0,{'scale:1.08,' if nxt == 'zoom' else ''}duration:{TR},ease:'power1.in'}},{t1:.3f});")
        # captions
        cs = b.get("caption", "auto")
        if cs != "none":
            style = caption_style_for(ctx, b, lay, era25)
            emph = list(b.get("emph", []))
            if b.get("cta") and ctx.meta.get("cta_word"): emph.append(ctx.meta["cta_word"]); b["_quote"] = ctx.meta["cta_word"]
            for ch in chunks_for(ctx, b, style):
                caps_html.append(cap_html(ctx, b, ch, style, b["_dark"] and lay != "face", ci, emph))
                caption_qa.append(dict(id=f"c{ci}", beat=i, t0=round(ch["t0"], 3), t1=round(ch["t1"], 3), style=style,
                                       text=" ".join(ch["words"]), starts=[round(t, 3) for t in ch["starts"]],
                                       word_ends=[round(t, 3) for t in ch["ends"]],
                                       box_px=list(caption_box(ctx, b, style)), bounds_kind="container_estimate",
                                       glyph_bounds_verified=False, estimated_min_font_px=caption_estimated_min_font(ctx, b, ch, style)))
                ci += 1
    # stage files
    hf = f"{P}/hf"; os.makedirs(f"{hf}/img", exist_ok=True); os.makedirs(f"{hf}/media", exist_ok=True)
    shutil.copytree(f"{SKILL}/assets/fonts", f"{hf}/fonts", dirs_exist_ok=True); os.makedirs(f"{hf}/vendor", exist_ok=True)
    shutil.copy(f"{SKILL}/assets/vendor/gsap.min.js", f"{hf}/vendor/gsap.min.js")
    for name, src in ctx.imgs.items(): shutil.copy(src, f"{hf}/img/{name}")
    for f in ("clean.mp4", "clean_subject.webm"):
        dst = f"{hf}/media/{f}"
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(f"{P}/work/{f}"): shutil.copy(f"{P}/work/{f}", dst)
    css = open(f"{SKILL}/assets/base.css").read(); fonts_css = open(f"{SKILL}/assets/fonts/fonts.css").read()
    acc_face = ctx.meta.get("accent_face", ctx.accent if lum(ctx.accent) > 0.35 else "#ffd84d")
    caps_font = ctx.meta.get("caps_font") or ("'Noto Serif Display'" if ctx.meta.get("lang") == "ru" else "'Playfair Display'")   # Playfair's italic Т carries a ball that reads as an apostrophe in Russian
    root_vars = f":root{{--accent:{ctx.accent};--accent-soft:{rgba(ctx.accent, .18)};--accent-face:{acc_face};--caps-font:{caps_font};--accent-glow:{rgba(ctx.accent, .6)}}}"
    runtime = open(f"{SKILL}/assets/runtime.js").read()
    doc = f"""<!doctype html><html lang="{ctx.meta.get('lang', 'en')}"><head><meta charset="utf-8"><meta name="viewport" content="width={W}, height={H}">
<title>{esc(ctx.meta.get('title', 'reel'))}</title><script src="vendor/gsap.min.js"></script>
<style>{fonts_css}
{css}
{root_vars}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-width="{W}" data-height="{H}" data-duration="{D:.3f}">
<div id="bg" class="layer"></div>
{"".join(x for x in ctx.media if not x.startswith('<div id="leak'))}
<div class="layer" id="gfx">{"".join(beats_html)}</div>
<div id="plate" class="layer"><div id="plate-inner"><video id="head" src="media/clean.mp4" data-start="0" data-duration="{D:.3f}" data-media-start="0" data-track-index="0" muted playsinline></video></div></div>
<div id="cut" class="layer" style="opacity:0;-webkit-mask-image:linear-gradient(to bottom,transparent {ARCH['top'] - POP}px,#000 {ARCH['top'] - POP + 70}px);mask-image:linear-gradient(to bottom,transparent {ARCH['top'] - POP}px,#000 {ARCH['top'] - POP + 70}px)"><div id="cut-inner"><video id="headcut" src="media/clean_subject.webm" data-start="0" data-duration="{D:.3f}" data-media-start="0" data-track-index="1" muted playsinline></video></div></div>
<div class="layer" id="over">{"".join(over_html)}</div>
<div class="layer" id="caps">{"".join(caps_html)}</div>
<div class="layer" id="fx">{"".join(x for x in ctx.media if x.startswith('<div id="leak'))}</div>
</div>
<script>{runtime}
window.__timelines = window.__timelines || {{}};
function build(){{
const tl = window.TL = gsap.timeline({{paused:true}});
{chr(10).join(ctx.js)}
window.__timelines["main"] = tl;
}}
document.fonts.ready.then(build);
</script></body></html>"""
    open(f"{hf}/index.html", "w").write(doc)
    json.dump(dict(duration=D, sfx=sorted(ctx.sfx, key=lambda x: x["t"]),
                   beats=[dict(i=b["_i"], t0=round(b["_t0"], 3), t1=round(b["_t1"], 3),
                               layout=b["layout"], gfx=(b.get("gfx") or {}).get("type", "none"),
                               **({"visual_intent": b["qa_intent"]} if b.get("qa_intent") else {})) for b in beats]),
              open(f"{P}/work/timeline.json", "w"), indent=1)
    json.dump(dict(width=W, height=H, video_width=W, video_height=H,
                   plan_sha256=sha256(f"{P}/plan.json"), hf_index_sha256=sha256(f"{hf}/index.html"),
                   words_sha256=sha256(f"{P}/work/words.json"), captions=caption_qa),
              open(f"{P}/work/caption_qa.json", "w"), ensure_ascii=False, indent=1)
    browser_preflight(P)
    print(f"built {hf}/index.html: {len(beats)} beats, {ci} captions, {len(ctx.sfx)} sfx events, {len(ctx.imgs)} images, duration {D:.2f}s")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): raise SystemExit(__doc__)
    build(os.path.abspath(sys.argv[1]))
