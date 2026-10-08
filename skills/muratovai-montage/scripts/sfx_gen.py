#!/usr/bin/env python3
"""Generate an SFX kit with ElevenLabs Sound Effects (paid API; at most 3 parallel requests, else 429).

  python3 sfx_gen.py --out ~/reels-sfx                 # every missing file of VARIANTS → <out>/<kind>/<kind>_<a..>.wav
  python3 sfx_gen.py --out ~/reels-sfx typing tap      # only these kinds
  python3 sfx_gen.py --out ~/reels-sfx --force glitch  # regenerate
  python3 sfx_gen.py --list                            # show the kinds, variants and total seconds (nothing is generated)
Output folder: --out, else $REELS_SFX_DIR. finish.py looks up sounds in plan meta.sfx_dir → $REELS_SFX_DIR → the bundled kit,
so a class you generate overrides the bundled one. Key: ELEVENLABS_API_KEY (environment). Cost: about 40 credits per second
of audio (the whole list ≈ 36 s ≈ 1,500 credits); run --list first and generate only the kinds you need.
Each file: leading silence trimmed, peak-normalised to −3 dBFS, 48 kHz stereo. finish.py rotates the variants of a kind so no two
neighbouring events use the same file. The opening swell and the sub hits are synthesised (sfx_synth.py), not generated.

The prompts describe typical short-form UI and transition sounds (references/sound-design.md):
a small palette of soft airy whooshes on scene changes, short dry clicks on UI events, rare deep sub thumps, one glitch, one slide.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import json, os, re, subprocess, sys, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import env_key  # noqa: E402

OUT = None
VARIANTS = {
    "whoosh": [
        ("soft airy whoosh, a fast pass-by of air, clean modern video transition, no bass boom, no reverb tail", 0.5),
        ("short light airy swish, like a card flicked quickly past the microphone, clean and crisp", 0.4),
        ("smooth soft wind whoosh with a faint high shimmer, short modern motion graphics transition", 0.5),
        ("quick soft swoosh with a gentle low body, subtle cinematic transition, short, no impact", 0.5),
        ("warm smooth whoosh, mid-range air movement, rounded, not bright, short modern transition", 0.5),
        ("soft paper-like swish with low-mid body, quick pass, clean, no high hiss", 0.45),
    ],
    "whoosh_low": [
        ("deep soft whoomp, low air push like a camera punching in, warm low-mid body, short, no high hiss, no impact", 0.5),
        ("low muffled swoosh, heavy fabric swung past the microphone, warm and round, short", 0.5),
        ("soft low whoosh with a gentle bass swell, smooth, subtle, cinematic punch-in, no hiss", 0.6),
    ],
    "whoosh_soft": [
        ("very soft short air swish, subtle and quiet, gentle UI slide transition", 0.35),
        ("tiny soft whoosh, barely there, smooth air movement, short", 0.3),
        ("soft fabric-like swipe of air, short, gentle, clean", 0.35),
    ],
    "pop": [
        ("soft glassy UI pop, bubble-like, clean and short, modern app notification element appearing", 0.3),
        ("soft wet pop, small bubble popping, short, clean, no reverb", 0.25),
        ("bright small pop with a tiny sparkle on top, short, playful modern interface", 0.35),
        ("soft rounded plastic button pop, short and satisfying, dry", 0.25),
    ],
    "click": [
        ("short dry click, soft modern user interface tap, clean, no reverb", 0.2),
        ("crisp single mouse click, dry, close microphone", 0.2),
        ("soft single keyboard key tap, dry and short", 0.2),
        ("tiny soft wooden tick click, short and dry", 0.2),
    ],
    "tick": [
        ("tiny soft digital tick, minimal clock tick in an app, dry, very short", 0.2),
        ("short high soft tick, like a small switch, dry", 0.2),
    ],
    "glitch": [
        ("short digital glitch, data static burst with a stutter, modern tech, clean, not harsh", 0.45),
        ("quick digital static crackle and bit-crushed stutter, short computer glitch", 0.4),
        ("short glitchy digital transition, scrambled data blips, modern", 0.5),
    ],
    "swipe": [
        ("quick short slide, like a paper card sliding across a table, clean, short", 0.35),
        ("fast soft swipe of a finger across a glass touchscreen, short, clean", 0.3),
        ("quick marker stroke on paper, short highlight swipe sound", 0.35),
    ],
    "chime": [
        ("soft pleasant success chime, two rising notes, modern app, subtle, clean", 0.8),
        ("gentle bright confirmation chime, single soft bell with short tail", 0.7),
    ],
    "ding": [
        ("bright clean single ding, modern notification, short tail", 0.6),
        ("soft crystal ding, small and clean, short", 0.6),
    ],
    "error": [
        ("soft digital error buzz, short, two low beeps, not harsh", 0.45),
    ],
    "punch": [
        ("cartoon punch hit, fast whoosh into a crisp meaty smack, short, punchy, no reverb", 0.5),
        ("8-bit video game punch impact, retro arcade hit sound with a short crunch, clean", 0.5),
    ],
    "shatter": [
        ("glass logo shattering into pieces, sharp crack then bright shards scattering, short, cinematic, no long tail", 1.0),
        ("digital crystal shatter, a crack and a burst of glassy fragments with a light pixel crunch, short", 0.9),
    ],
    "impact": [
        ("deep cinematic sub thump, short punchy low hit, no long tail, no rumble", 0.6),
    ],
    # classes the bundled kit covers only with synthesised stand-ins (typing, count, riser_soft) or aliases (the rest)
    "tap": [
        ("single soft tap on a smartphone touch screen, short dry UI click with a tiny bit of body, modern and clean, no reverb, no music", 0.5),
        ("soft rounded finger tap on glass, short, dry, clean, no music", 0.5),
    ],
    "toggle": [
        ("UI switch toggle flipping on, crisp short mechanical click with a tiny upward tail, dry, no music", 0.5),
    ],
    "send": [
        ("message sent sound, short rising whoosh ending in a soft pop, clean modern app, no music", 0.7),
    ],
    "shutter": [
        ("smartphone camera shutter click, single, crisp and clean, dry, no music", 0.5),
    ],
    "blip": [
        ("tiny soft digital blip, a short rising two-tone UI chirp, clean, dry, no music", 0.5),
    ],
    "reveal": [
        ("short bright shimmer sparkle rising, tiny glassy bell-like particles for a text or result reveal, clean and positive, short tail, no music", 1.0),
    ],
    "typing": [
        ("fast even typing on a quiet laptop keyboard, soft rapid key clicks, continuous with no pauses, dry close microphone, no voices, no music", 2.5),
        ("light quick typing on a low-profile keyboard, steady soft clicks, dry, no voices, no music", 2.0),
    ],
    "count": [
        ("fast soft digital counter ticking, numbers rolling up quickly like a small odometer, even rapid ticks, dry, no music", 1.0),
    ],
    "riser_soft": [
        ("tension riser for a reveal, airy filtered noise and a synth tone rising steadily in pitch and volume and getting brighter, ends abruptly at its loudest point, no hit at the end, no cymbal, no music", 1.5),
    ],
    "open_riser": [
        ("dark cinematic riser that builds for three seconds and stops dead at its loudest point, then a short low sub tail, no drums, no melody, no music", 4.0),
    ],
}


def one(job):
    kind, k, (text, dur), force = job
    d = os.path.join(OUT, kind); os.makedirs(d, exist_ok=True)
    wav = os.path.join(d, f"{kind}_{'abcdefgh'[k]}.wav"); mp3 = wav[:-4] + ".mp3"
    if os.path.exists(wav) and not force: return os.path.relpath(wav, OUT), "exists"
    body = json.dumps({"text": text, "duration_seconds": max(0.5, dur), "prompt_influence": 0.6}).encode()   # the API refuses < 0.5 s; the tail is trimmed below
    req = urllib.request.Request("https://api.elevenlabs.io/v1/sound-generation", data=body, headers={"xi-api-key": env_key("ELEVENLABS_API_KEY"), "Content-Type": "application/json"})
    try: open(mp3, "wb").write(urllib.request.urlopen(req, timeout=120).read())
    except urllib.error.HTTPError as e: return os.path.relpath(wav, OUT), f"HTTP {e.code}: {e.read()[:300]!r}"
    peak = subprocess.run(["ffmpeg", "-v", "info", "-i", mp3, "-af", "silenceremove=start_threshold=-45dB:start_silence=0.005,volumedetect", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    mx = float(re.search(r"max_volume: (-?[\d.]+)", peak).group(1))
    hp = "" if kind == "impact" else "highpass=f=90,"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-af", f"silenceremove=start_threshold=-45dB:start_silence=0.005,{hp}volume={-3 - mx:.2f}dB,"
                    f"areverse,silenceremove=start_threshold=-55dB:start_silence=0.01,areverse,atrim=0:{max(dur, 0.2) + 0.15:.2f},"
                    f"afade=t=out:st={max(dur - 0.05, 0.1):.2f}:d=0.15", "-ar", "48000", "-ac", "2", wav], check=True)
    os.remove(mp3); return os.path.relpath(wav, OUT), "ok"


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): raise SystemExit(__doc__)
    if "--list" in a:
        for kd, vs in VARIANTS.items(): print(f"{kd:12} {len(vs)} variants, {sum(max(0.5, d) for _, d in vs):.1f} s")
        print(f"total {sum(max(0.5, d) for vs in VARIANTS.values() for _, d in vs):.1f} s of audio"); sys.exit(0)
    OUT = a[a.index("--out") + 1] if "--out" in a else os.environ.get("REELS_SFX_DIR")
    if not OUT: raise SystemExit("give an output folder: --out <dir> (or set REELS_SFX_DIR); finish.py picks the kit up from there")
    OUT = os.path.abspath(os.path.expanduser(OUT)); env_key("ELEVENLABS_API_KEY")
    skip = {a[a.index("--out") + 1]} if "--out" in a else set()
    force = "--force" in a; kinds = [x for x in a if not x.startswith("--") and x not in skip] or list(VARIANTS)
    bad = [k for k in kinds if k not in VARIANTS]
    if bad: raise SystemExit(f"unknown kinds {bad}; known: {', '.join(VARIANTS)}")
    jobs = [(kd, k, v, force) for kd in kinds for k, v in enumerate(VARIANTS[kd])]
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(one, jobs): print(*r, flush=True)
