#!/usr/bin/env python3
"""Packs a style profile (the result of "analyze this creator's montage") into its own agent skill (Claude Code or Codex).

  python3 make_skill.py <profile_dir> [--name montage-<handle>] [--title "@handle"] [--dest <folder>]

Without --dest, the skill is packed under the first path in $REELS_STYLES (a list of skill roots separated by ':',
see common.styles_roots() for the default). The new skill holds the profile's shareable files (style.json,
style-bible.md, STYLE_METRICS.md, analysis/*.md and portable JSON observations, never raw/ or work/) and a SKILL.md that tells the agent to edit with
the muratovai-montage engine and this profile. After it, a request like "edit my video in <handle>'s style" / «смонтируй в
стиле <handle>» triggers the new skill in any session.
The profile folder itself can be passed as --style too: the skill folder is a valid profile.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import datetime, glob, json, os, re, shutil, sys
import common  # noqa: E402  (styles_roots(): the default --dest, see above)

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "creator"


def rules_block(bible):
    """the numbered rules for the planner from style-bible.md (the section whose heading mentions rules), else the first 40 lines"""
    lines = bible.splitlines(); out, on = [], False
    for ln in lines:
        if ln.startswith("#"):
            if on: break
            on = bool(re.search(r"(?i)rule|правил", ln))
            continue
        if on: out.append(ln)
    text = "\n".join(out).strip()
    return text or "\n".join(lines[:40]).strip()


def num(v, k="median"):
    return v.get(k) if isinstance(v, dict) else v


def _reference_windows(reel):
    """Choose a small set of representative windows; the full timeline stays as evidence."""
    duration = float(reel["duration_s"])
    windows = [("hook", 0.0, min(3.0, duration), "opening")]
    frames = reel.get("frames") or []
    graphic = next((f["t_s"] for f in frames if f["t_s"] >= 3 and
                    f.get("layout") in ("graphic_full_no_face", "broll_full_no_face")), None)
    caption = next((f["t_s"] for f in frames if f["t_s"] >= 3 and f.get("caption_words", 0)), None)
    verified = next((s["start_s"] for s in reel.get("shots", [])
                     if s.get("transition_source") == "agent_frame_tag"), None)
    sfx = [e for e in (reel.get("audio") or {}).get("sfx", []) if e.get("t_s", 0) >= 3 and
           isinstance(e.get("peak_above_bed_db"), (int, float))]
    loudest = max(sfx, key=lambda e: e["peak_above_bed_db"])["t_s"] if sfx else None
    for name, t, why in (("graphic", graphic, "graphic layout"), ("caption", caption, "caption geometry"),
                         ("transition", verified, "manually tagged transition"),
                         ("audio", loudest, "background transient candidate")):
        if t is not None:
            windows.append((name, max(0.0, t - 0.75), min(duration, t + 1.75), why))
    if duration > 5:
        windows.append(("outro", max(0.0, duration - 4), duration, "ending and CTA"))
    return windows[:6]


def _window_data(reel, name, start, end):
    in_window = lambda e: start <= e.get("t_s", -1) < end
    intersects = lambda e: e.get("start_s", end) < end and e.get("end_s", start) > start
    sound = reel.get("audio") or {}
    return {"reel": reel["id"], "window": name, "start_s": round(start, 3), "end_s": round(end, 3),
            "measurement_notes": reel.get("measurement_notes", []),
            "shots": [s for s in reel.get("shots", []) if intersects(s)],
            "frames": [f for f in reel.get("frames", []) if in_window(f)],
            "visual_events": [e for e in reel.get("visual_events", []) if in_window(e)],
            "pauses": [p for p in reel.get("pauses", []) if intersects(p)],
            "face_track": [f for f in reel.get("face_track", []) if in_window(f)],
            "audio": {"status": sound.get("status", "unmeasured"),
                      "sfx": [e for e in sound.get("sfx", []) if in_window(e)],
                      "music_accents": [e for e in sound.get("music_accents", []) if in_window(e)],
                      "bed": [b for b in sound.get("bed", []) if intersects(b)]}}


def build_reference_index(profile, out):
    """Write compact selected windows only when a portable timeline exists."""
    source = os.path.join(profile, "analysis", "reference_timeline.json")
    if not os.path.isfile(source): return False
    with open(source, encoding="utf-8") as f: data = json.load(f)
    if data.get("schema_version") != 1 or not isinstance(data.get("reels"), list):
        raise ValueError(f"unsupported reference timeline in {source}")
    folder = os.path.join(out, "analysis", "windows")
    os.makedirs(folder, exist_ok=True)
    lines = ["# Reference windows", "", "Use one or two rows matching the current semantic slot. Open only those small JSON files.",
             "The complete `analysis/reference_timeline.json` remains archival evidence; do not read it wholesale into the planner.",
             "Scene-score boundaries and Demucs transients are candidates until checked in the source.", "",
             "| reel | window | seconds | purpose | file |", "|---|---|---:|---|---|"]
    for reel in data["reels"]:
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "-", reel["id"])
        for name, start, end, why in _reference_windows(reel):
            filename = f"{safe_id}_{name}.json"
            rel = f"analysis/windows/{filename}"
            with open(os.path.join(folder, filename), "w", encoding="utf-8") as f:
                json.dump(_window_data(reel, name, start, end), f, ensure_ascii=False, separators=(",", ":"))
            lines.append(f"| {reel['id']} | {name} | {start:.2f}–{end:.2f} | {why} | `{rel}` |")
    with open(os.path.join(out, "analysis", "reference_index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return True


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): raise SystemExit(__doc__)
    prof = os.path.abspath(os.path.expanduser(a[0]))
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if not os.path.isfile(os.path.join(prof, "style.json")): raise SystemExit(f"no style.json in {prof}: run analyze_reference.py … all first")
    bible_f = os.path.join(prof, "style-bible.md")
    if not os.path.isfile(bible_f):
        raise SystemExit(f"no style-bible.md in {prof}: turn style-bible.draft.md into style-bible.md first (references/style-profiles.md, step 5)")
    with open(os.path.join(prof, "style.json"), encoding="utf-8") as f: style = json.load(f)
    handle = opt("--title") or style.get("name") or os.path.basename(prof)
    name = slug(opt("--name") or f"montage-{handle.lstrip('@')}")
    dest = os.path.abspath(os.path.expanduser(opt("--dest") or common.styles_roots()[0]))
    out = os.path.join(dest, name)
    if os.path.exists(out):
        bak = os.path.join(os.path.dirname(dest), "skills-backup", f"{name}-{datetime.datetime.now():%Y%m%d-%H%M%S}")
        os.makedirs(os.path.dirname(bak), exist_ok=True); shutil.move(out, bak); print(f"previous version moved to {bak}")
    os.makedirs(out)
    for f in ("style.json", "style-bible.md", "STYLE_METRICS.md", "reference-reels.md", "sources.json"):
        if os.path.isfile(os.path.join(prof, f)): shutil.copy(os.path.join(prof, f), out)
    an = sorted(glob.glob(os.path.join(prof, "analysis", "*")))
    if an:
        os.makedirs(os.path.join(out, "analysis"))
        for f in an:
            if os.path.isfile(f) and os.path.basename(f) != "reference_index.md":
                shutil.copy(f, os.path.join(out, "analysis"))
    has_timeline = build_reference_index(prof, out)
    style["name"] = name
    with open(os.path.join(out, "style.json"), "w", encoding="utf-8") as f:
        json.dump(style, f, ensure_ascii=False, indent=1)

    pace, lay, snd = style.get("pace", {}), style.get("layouts", {}), style.get("sound", {})
    facts = []
    if pace.get("wps"): facts.append(f"pace {pace['wps']:.1f} words/s")
    if num(pace.get("first_change")): facts.append(f"first picture change ≈ {num(pace['first_change']):.1f} s")
    if pace.get("beat_len_median"): facts.append(f"beat ≈ {pace['beat_len_median']:.1f} s")
    if num((style.get("shots") or {}).get("duration_s")):
        facts.append(f"visual segment candidate ≈ {num(style['shots']['duration_s']):.1f} s")
    if lay: facts.append("layouts " + " / ".join(f"{k} {num(v):.0%}" for k, v in lay.items() if num(v) is not None))
    if snd.get("music_rel_voice_db") is not None: facts.append(f"music {snd['music_rel_voice_db']:.0f} dB under the voice")
    if num(snd.get("sfx_per_10s")): facts.append(f"{num(snd['sfx_per_10s']):.1f} effects per 10 s")
    n = style.get("reels") or len(an) or "several"
    engine = os.path.join(SKILL_DIR, "scripts").replace(os.path.expanduser("~"), "~")
    here = out.replace(os.path.expanduser("~"), "~")
    desc = (f"Edits a talking-head video (Reels, TikTok, Shorts) in the measured editing style of {handle}, made by muratovai-montage from a "
            f"frame-by-frame analysis of {n} of their reels ({'; '.join(facts[:3]) or 'pace, layouts, captions, sound'}). Use it whenever the user "
            f"asks to edit a video in {handle}'s style, like {handle}, in this style or in my style after this analysis, or in Russian "
            f"«смонтируй в стиле {handle}», «смонтируй как у {handle}», «смонтируй в этом стиле», «в моём стиле», or in Uzbek «{handle} uslubida montaj qil», «mening uslubimda montaj qil». Needs the muratovai-montage skill (the engine).")
    evidence_step = ("Read `analysis/reference_index.md`, then open one or two matching files under `analysis/windows/` "
                     "for the current hook, graphic, caption, transition, sound or CTA. Keep the full timeline on disk as "
                     "evidence; do not load all of it into the planning context.") if has_timeline else (
                     "Use the beat sheets in `analysis/` when present; this legacy profile has no timecoded timeline.")
    with open(bible_f, encoding="utf-8") as f: bible = f.read()
    evidence_description = (", timecoded examples and beat sheets (`analysis/`)" if has_timeline else
                            ", beat sheets (`analysis/`)" if any(f.endswith(".md") for f in an) else "")
    skill_md = f"""---
name: {name}
description: {json.dumps(desc, ensure_ascii=False)}
---

# Montage in the style of {handle}

Created on {datetime.date.today():%Y-%m-%d} by `muratovai-montage` from {n} reels of {handle}. This folder is a **style profile**: the numbers
(`style.json`), the style bible (`style-bible.md`), measurements (`STYLE_METRICS.md`){evidence_description}. The engine is
the `muratovai-montage` skill.

## How to edit a take in this style
1. Read the muratovai-montage skill (part **B. Edit a take**) and this folder's `style-bible.md` before planning. {evidence_step}
2. Run every step of part B; pass this profile to the planner: `python3 {engine}/autoplan.py $P --style {here} …`.
   `autoplan.py` writes it into `plan.json → meta.style`, and `plan_lint.py`, `build.py`, `finish.py`, `qa.py` use its numbers.
3. Plan the beats with the rules below and the moves in `analysis/`; keep the engine's quality gates (lint, contact sheet, qa).

## The style in numbers
{chr(10).join('- ' + f for f in facts) or '- see STYLE_METRICS.md'}

## Rules for the planner (from style-bible.md)
{rules_block(bible)}
"""
    with open(os.path.join(out, "SKILL.md"), "w", encoding="utf-8") as f: f.write(skill_md)
    print(f"skill '{name}' → {out}\nAsk for it by name or say «смонтируй в стиле {handle}»; the profile path for --style is {here}")


if __name__ == "__main__":
    main()
