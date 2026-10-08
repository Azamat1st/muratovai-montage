#!/usr/bin/env python3
"""Draft beat plan from the clean words, following the grammar of a style profile. The draft is a starting point, not a result:
every beat with "type": "TODO" must be filled by hand (which logo, which screenshot, which UI) before build.py will run.

  python3 autoplan.py <project> --style <profile folder | montage-<handle> skill folder> [--accent "#D97757"] [--cta WORD] [--lang en|ru] [--era 2026|2025]
      → plan.draft.json (never overwrites plan.json)

Rules encoded (the style profile's numbers, engine defaults where it has none): beats 0.8–3.2 s cut at sentence/clause ends; open on the
style's opening layout (split with a graphic); end on a face close-up with the CTA; a name reveal ("it's called X" / "называется")
→ full-frame title; a number → full-frame counter; a list ordinal (first/second/…/finally) → full-frame list title; face close-ups
on short emotional phrases, at the style's face share; never two face beats in a row; layouts alternate so a run lasts ~2 s.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SKILL, load_style, user_styles  # noqa: E402

CTA_RE = re.compile(r"\b(comment|link in|bio|follow|send (this|it) to|скинь|шапке|коммент|подпиш)", re.I)
NAME_RE = re.compile(r"\b(called|named|называется|называют)\b", re.I)
LIST_RE = re.compile(r"^(the )?(first|second|third|fourth|fifth|finally|number \w+|во-первых|во-вторых|первый|второй|третий|четвёртый|и наконец)\b", re.I)
EMO_RE = re.compile(r"\b(best part|every single|completely free|for free|all in one|insane|crazy|literally|бесплатно|лучшее|каждый)\b", re.I)
NUM_RE = re.compile(r"(?<![\w])\d[\d.,]*(?:\s?(?:%|x|×|k|K|млн|млрд|тыс|million|billion|thousand|\$|₽))?(?![A-Za-zА-Яа-яЁё])")   # "1С" is a product, not a number
STEP_RE = re.compile(r"\b(open|click|type|paste|go to|create|install|download|press|tap|search|copy|run|откр|жм|нажм|вставь|скачай|перейди|напиши|создай)", re.I)
MECH_RE = re.compile(r"\b(sorts?|finds?|scans?|connects?|switch|builds?|generates?|reads?|writes?|turns?|разбир|наход|подключ|генерир|создаёт|собирает)", re.I)


def sentences(W):
    out, cur = [], []
    for i, w in enumerate(W):
        cur.append(i)
        if re.search(r"[.!?]$", w["word"]) or i == len(W) - 1: out.append(cur); cur = []
    return out


def split_long(W, idx, max_len=3.0, min_len=0.8):
    """Split a sentence at clause ends and near the measured shot length."""
    beats, cur = [], []
    for i in idx:
        cur.append(i); d = W[i]["end"] - W[cur[0]]["start"]
        if (re.search(r"[,;:]$", W[i]["word"]) and d >= min_len) or d >= max_len:
            beats.append(cur); cur = []
    if cur:
        if beats and W[cur[-1]]["end"] - W[cur[0]]["start"] < min_len: beats[-1] += cur
        else: beats.append(cur)
    return beats


def style_shot_length(S):
    shots = S.get("shots", {}).get("duration_s", {})
    target = shots.get("median", S.get("pace", {}).get("beat_len_median", 2.2))
    return max(0.8, min(4.0, float(target)))


def apply_style_transitions(beats, S):
    """Spread verified transitions; candidate/unknown share keeps the default."""
    raw = S.get("shots", {}).get("transition_share") or {}
    aliases = {"cut": "cut", "dissolve": "fade", "fade": "fade", "zoom": "zoom", "flash": "flash", "leak": "leak", "blur": "blur"}
    weights = {}
    raw_total = sum(float(v) for v in raw.values() if isinstance(v, (int, float)) and v > 0)
    scale = 1 / max(1.0, raw_total)
    for kind, share in raw.items():
        if kind in aliases and isinstance(share, (int, float)) and share > 0:
            mapped = aliases[kind]; weights[mapped] = weights.get(mapped, 0) + float(share) * scale
    if not weights or len(beats) < 2: return
    weights["auto"] = max(0.0, 1.0 - sum(weights.values()))
    assigned = {k: 0 for k in weights}
    for i, beat in enumerate(beats[1:], 1):
        choice = max(weights, key=lambda k: ((i * weights[k] - assigned[k]), weights[k], k))
        if choice != "auto": beat["trans"] = choice
        assigned[choice] += 1


def first_matching_word(W, indices, pattern):
    return next((i for i in indices if pattern.search(W[i]["word"])), indices[0])


def reveal_name(W, indices):
    """Name reveal begins on the name, not on an introductory article."""
    marker = first_matching_word(W, indices, NAME_RE)
    following = [i for i in indices if i > marker]
    if len(following) > 1 and W[following[0]]["word"] in ("the", "a", "an") and W[following[1]]["word"][:1].isupper():
        following.pop(0)
    return marker, (following[0] if following else marker), " ".join(W[i]["word"] for i in following).strip(" .,")


def main(P, accent, cta, lang, era=None, style=None):
    style = style or os.environ.get("REELS_STYLE")
    if not style:
        have = user_styles()
        if len(have) == 1: style = have[0]; print(f"style profile: {style} (the only one you have)")
        else:
            raise SystemExit("autoplan needs a style profile (--style <folder>). "
                             + (f"You have several: {', '.join(have)}. Ask the user which one." if have else
                                "There is none yet: ask the user for 2–5 reel links of a creator whose editing they like and make one "
                                "(SKILL.md part A). `--style _defaults` edits with the engine's neutral fallback numbers only."))
    S = load_style(style, P); dflt = S.get("plan_defaults", {}); accent = accent or dflt.get("accent", "#D97757"); era = str(era or dflt.get("era", "2026"))
    face_share = S["layouts"]["face"]["median"]; open_layout = S.get("open_layout", "split")
    W = json.load(open(f"{P}/work/words.json"))["words"]; groups = []
    shot_length = style_shot_length(S)
    for s in sentences(W): groups += [(g, " ".join(W[i]["word"] for i in s)) for g in split_long(W, s, max_len=shot_length)]
    beats, prev = [], None; n = len(groups)
    for k, (g, sent) in enumerate(groups):
        text = " ".join(W[i]["word"] for i in g); first = g[0]; b = {"t0": 0 if k == 0 else f"w:{first}", "_text": text}
        is_cta = k >= n - 3 and bool(CTA_RE.search(sent)) or (k >= n - 2 and any(CTA_RE.search(t2) for _, t2 in groups[k:]))
        if k == 0 and open_layout == "face":
            b.update(layout="face", caption_style="mix", emph=[])
        elif k == 0:
            b.update(layout="graphic" if open_layout == "graphic" else "split", bg="white", gfx={"type": "TODO", "hint": "hook visual: the product/brand identity (logo, app widget, terminal, pixel title) — what the first sentence names"})
        elif is_cta:
            b.update(layout="face", caption_style="mix", cta=True, emph=[cta] if cta else [])
        elif NAME_RE.search(text):
            marker, name_word, name = reveal_name(W, g)
            b.update(layout="graphic", bg="white", caption="none", gfx={"type": "title", "font": "pixel", "over": "it's called" if lang == "en" else "называется", "over_t": f"w:{marker}", "text": name or "TODO", "text_t": f"w:{name_word}", "icon": "TODO: product logo/icon", "highlight": []})
        elif LIST_RE.search(text):
            b.update(layout="graphic", bg="white", gfx={"type": "title", "font": "caps", "text": text.split()[0].upper(), "icon": "TODO: item logo or 3D emoji", "sub": "TODO: item name"})
        elif NUM_RE.search(text) and prev != "graphic":
            num = re.search(r"[\d.,]+[%x×kKmMbB]?", text).group(0)
            b.update(layout="graphic", bg="dark", caption="none", gfx={"type": "counter", "text": num, "label": "TODO: unit", "font": "serif", "t": f"w:{first_matching_word(W, g, NUM_RE)}"})
        elif EMO_RE.search(text) and prev != "face" and len(g) <= 7:
            b.update(layout="face", caption_style="mix", emph=[])
        else:
            nxt = {"split": "graphic", "graphic": "split", "face": "split", None: "split"}[prev]
            if prev == "split" and len(beats) >= 2 and beats[-2]["layout"] == "split": nxt = "graphic"
            b.update(layout=nxt, bg="white", gfx={"type": "TODO", "hint": f"visual for: {text}"})
        if b["layout"] == "face" and prev == "face" and b.get("cta") and beats and beats[-1].get("cta"):
            beats[-1]["_text"] += " " + text; continue   # one CTA close-up, not face → split → face
        if b["layout"] == "face" and prev == "face": b.update(layout="split", bg="white", gfx={"type": "TODO", "hint": f"visual for: {text}"}); b.pop("caption_style", None); b.pop("cta", None)
        prev = b["layout"]; beats.append(b)
    if beats[-1]["layout"] != "face": beats[-1].update(layout="face", caption_style="mix", cta=True); beats[-1].pop("gfx", None); beats[-1].pop("bg", None)
    # merge trailing CTA faces into one beat
    while len(beats) > 1 and beats[-2].get("cta") and beats[-1].get("cta"):
        beats[-2]["_text"] += " " + beats[-1]["_text"]; beats.pop()
    # face close-ups ≈ 20–25 % of beats: short, brand-free, number-free lines, never two in a row, not in the first two beats
    def dur(i): 
        t0 = beats[i]["t0"]; a = 0 if t0 == 0 else W[int(str(t0)[2:])]["start"]
        b = W[int(str(beats[i + 1]["t0"])[2:])]["start"] if i + 1 < len(beats) else W[-1]["end"]
        return b - a
    want = max(2 if face_share >= 0.1 else 1, round(len(beats) * face_share * 0.9)); have = sum(1 for b in beats if b["layout"] == "face")
    for i in range(2, len(beats) - 2):
        if have >= want: break
        b = beats[i]; txt = b["_text"]
        if b["layout"] == "face" or beats[i - 1]["layout"] == "face" or beats[i + 1]["layout"] == "face": continue
        if b.get("gfx", {}).get("type") not in ("TODO", None) or NUM_RE.search(txt) or re.search(r"\s[A-Z][a-z]+[A-Z]|\s[A-Z]{2,}|\s[A-Z][a-z]+", txt): continue
        if dur(i) > 2.4 or STEP_RE.search(txt) or MECH_RE.search(txt): continue
        b.update(layout="face", caption_style="mix", emph=[]); b.pop("gfx", None); b.pop("bg", None); have += 1
    if era == "2025":   # reels 23, 24: the face shows only in one hook breather and in the CTA; captions sit in grey boxes (no serif connectors)
        kept = False
        for i, b in enumerate(beats[:-1]):
            if b["layout"] != "face": continue
            if not kept and i <= 4: kept = True; b.pop("caption_style", None); continue
            b.update(layout="graphic", bg="white", gfx={"type": "TODO", "hint": f"visual for: {b['_text']}"}); b.pop("caption_style", None); b.pop("emph", None)
        beats[-1].pop("caption_style", None)
        mid = len(beats) // 2   # the speaker stays in the 50/50 split only in the hook and once mid-reel; everything else is full-frame graphics
        bgs = ["white", "dark", "white", "black"]
        for i, b in enumerate(beats[:-1]):
            if b["layout"] == "split" and i > 1 and i != mid: b["layout"] = "graphic"; b["bg"] = bgs[i % 4]
    apply_style_transitions(beats, S)
    meta = {"title": os.path.basename(P), "lang": lang, "accent": accent, "music": dflt.get("music", "ambient_tech_90"), "cta_word": cta or ""}
    meta.update({k: dflt[k] for k in ("caption_face", "profile", "trans") if dflt.get(k)})
    if "profile" not in meta and S.get("name") != "_defaults": meta["profile"] = "measured"
    if style:   # _defaults is stored by name, a style profile by its absolute path
        meta["style"] = style if os.path.isdir(os.path.join(SKILL, "styles", str(style))) else S["_dir"]
    if era == "2025": meta.update(era="2025", open_punch=True)
    plan = {"meta": meta, "beats": beats}
    json.dump(plan, open(f"{P}/plan.draft.json", "w"), indent=1, ensure_ascii=False)
    print(f"plan.draft.json: {len(beats)} beats; sequence " + " ".join({"split": "S", "graphic": "G", "face": "F"}[b["layout"]] for b in beats))
    todo = sum(1 for b in beats if json.dumps(b).count("TODO"))
    print(f"{todo} beats need a concrete visual (TODO). Fill them, remove the _text keys if you like, save as plan.json, run plan_lint.py.")


if __name__ == "__main__":
    a = sys.argv[1:]; opt = lambda k, d=None: (a[a.index(k) + 1] if k in a else d)
    if not a or a[0] in ("-h", "--help"): raise SystemExit(__doc__)
    main(os.path.abspath(a[0]), opt("--accent"), opt("--cta", ""), opt("--lang", "en"), opt("--era"), opt("--style"))
