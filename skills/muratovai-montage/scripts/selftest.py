#!/usr/bin/env python3
"""Engine self-test: builds, renders and mixes a 5-second synthetic reel with no API keys, so a fresh install proves that
ffmpeg (x264 + VP9 alpha), Python (numpy, Pillow), Node, the pinned HyperFrames CLI with its Chrome, the builder and the sound
engine all work on this machine.

  python3 selftest.py [--out <dir>] [--no-render]

What it fakes: the speaker (a drawn silhouette), the voice (tone bursts as "words") and whisper (the words are known). Everything
else is the real pipeline: prep init/cut/voice, a plan with a split, a counter, a custom html beat with a typing prompt and a CTA
face, plan_lint, build, hyperframes lint, snap, render, finish. Takes 1–3 minutes (the first run downloads HyperFrames' Chrome).
Result: <out>/out/selftest_light.mp4 and <out>/work/snap_sheet.jpg (default <out>: ~/reels/_selftest).
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import json, os, shutil, subprocess, sys, tempfile, time, wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    raise SystemExit("selftest needs numpy and Pillow: run install.py from the kit (or python3 -m pip install numpy Pillow)")
from common import gpu_env, hf  # noqa: E402

WORDS = "This is a quick engine test for the reels montage kit and it works fine today".split()
T0 = time.time()


def step(msg): print(f"[{time.time() - T0:5.1f}s] {msg}", flush=True)


def run(argv, **kw):
    r = subprocess.run([str(a) for a in argv], capture_output=True, text=True, **kw)
    if r.returncode: raise SystemExit(f"FAILED: {' '.join(str(a) for a in argv[:4])} …\n{(r.stdout or '')[-1200:]}\n{(r.stderr or '')[-1200:]}")
    return r


def synth_take(d):
    """a drawn talking head (silhouette on a dark gradient) + tone-burst 'speech' with one long pause; returns raw.mp4, words, mask.png"""
    W, H = 1080, 1920
    bg = Image.new("RGB", (W, H)); px = ImageDraw.Draw(bg)
    for y in range(H): px.line([(0, y), (W, y)], fill=(22 + y * 30 // H, 26 + y * 34 // H, 40 + y * 60 // H))
    mask = Image.new("L", (W, H), 0); m = ImageDraw.Draw(mask)
    m.ellipse([360, 560, 720, 980], fill=255)                              # head
    m.rounded_rectangle([200, 1000, 880, 1920], radius=220, fill=255)       # shoulders
    m.rectangle([470, 940, 610, 1060], fill=255)                            # neck
    mask = mask.filter(ImageFilter.GaussianBlur(3))
    person = Image.new("RGB", (W, H), (205, 160, 130)); pd = ImageDraw.Draw(person)
    pd.rectangle([0, 1000, W, H], fill=(40, 70, 120))                       # shirt
    pd.ellipse([430, 700, 480, 730], fill=(40, 30, 30)); pd.ellipse([600, 700, 650, 730], fill=(40, 30, 30))   # eyes
    img = Image.composite(person, bg, mask); img.save(f"{d}/frame.png"); mask.save(f"{d}/mask.png")
    sr = 48000; words, t, a = [], 0.35, []
    audio = np.zeros(int(sr * 7.4), dtype=np.float32)
    for k, w in enumerate(WORDS):
        dur = 0.18 + 0.03 * (len(w) % 4); f0 = 140 + 25 * (k % 5)
        n = int(dur * sr); tt = np.arange(n) / sr
        env = np.minimum(1, np.minimum(tt / 0.02, (dur - tt) / 0.03)).clip(0, 1)
        tone = (0.5 * np.sin(2 * np.pi * f0 * tt) + 0.3 * np.sin(2 * np.pi * 2 * f0 * tt) + 0.15 * np.sin(2 * np.pi * 3.1 * f0 * tt)) * env * 0.35
        i0 = int(t * sr); audio[i0:i0 + n] += tone.astype(np.float32)
        words.append(dict(word=w + ("." if k == len(WORDS) - 1 else ""), start=round(t, 3), end=round(t + dur, 3)))
        t += dur + (0.9 if k == 6 else 0.07)                                 # one long pause after word 6: cut must remove it
    wav = f"{d}/voice.wav"
    with wave.open(wav, "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes((audio.clip(-1, 1) * 32767).astype(np.int16).tobytes())
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "30", "-i", f"{d}/frame.png", "-i", wav, "-t", "7.4",
         "-vf", "scale=1080:1920,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-shortest", f"{d}/raw.mp4"])
    return f"{d}/raw.mp4", words


def plan(accent="#29B6F6"):
    html = ("<div class='center' style='flex-direction:column;gap:30px'>"
            "<div id='{p}box' class='card' style='width:880px;padding:40px 44px;background:#1d1f24;color:#eef0f3;border-radius:28px;"
            "box-shadow:0 60px 120px rgba(0,0,0,.6),0 18px 40px rgba(0,0,0,.35);font:500 46px/1.3 Inter'>"
            "<span id='{p}a' style='opacity:0'>Edit my video </span><span id='{p}b' style='opacity:0'>in this style</span>"
            "<span id='{p}c' style='display:inline-block;width:4px;height:48px;background:{accent};vertical-align:middle;margin-left:6px'></span></div></div>")
    js = ["tl.fromTo('#{p}box',{y:60,opacity:0,rotationX:18,filter:'blur(12px)'},{y:0,opacity:1,rotationX:0,filter:'blur(0px)',duration:0.35},{t:+0.02});",
          "tl.fromTo('#{p}a',{opacity:0},{opacity:1,duration:0.05},{t:+0.3});",
          "tl.fromTo('#{p}b',{opacity:0},{opacity:1,duration:0.05,immediateRender:false},{t:+0.9});"]
    return {"meta": {"title": "selftest", "lang": "en", "style": "_defaults", "profile": "bold", "accent": accent, "flash_start": True,
                     "cta_word": "TEST", "music": "tense_a"},
            "beats": [
                {"t0": 0, "layout": "split", "bg": "dark", "gfx": {"type": "title", "font": "block", "text": "ENGINE TEST", "decode": True, "size": 84}},
                {"t0": "w:3", "layout": "graphic", "bg": "dark", "caption": "none",
                 "gfx": {"type": "counter", "text": "100%", "label": "ready", "font": "serif", "size": 300, "t": "w:4"}},
                {"t0": "w:7", "layout": "graphic", "bg": "black", "caption": "none",
                 "gfx": {"type": "html", "html": html, "js": js, "sfx": [{"t": "+0.02", "kind": "pop"}, {"t": "+0.3", "kind": "typing", "dur": 1.2}]}},
                {"t0": "w:11", "layout": "face", "caption_style": "mix", "cta": True, "emph": []}]}


def main():
    a = sys.argv[1:]
    if a and a[0] in ("-h", "--help"): raise SystemExit(__doc__)
    P = os.path.abspath(os.path.expanduser(a[a.index("--out") + 1])) if "--out" in a else os.path.expanduser("~/reels/_selftest")
    if os.path.isdir(P): shutil.rmtree(P)
    os.makedirs(P); src = os.path.join(P, "_src"); os.makedirs(src)
    for tool in ("ffmpeg", "ffprobe", "node"):
        if not shutil.which(tool): raise SystemExit(f"{tool} is not installed (see install.py)")
    enc = run(["ffmpeg", "-hide_banner", "-encoders"]).stdout
    for e in ("libx264", "libvpx-vp9"):
        if e not in enc: raise SystemExit(f"ffmpeg has no {e} encoder: install a full ffmpeg build (macOS: brew install ffmpeg)")
    step(f"synthetic take → {P}")
    raw, words = synth_take(src)

    import prep   # the real prep steps, with whisper replaced by the known words
    prep.whisper = lambda mp3, lang, prompt=None: {"text": " ".join(w["word"] for w in words), "words": [dict(w) for w in words]}
    prep.init(raw, P, "en"); prep.cut(P, [], 0.18, 0.05, 0.06); prep.voice(P, False, True); prep.face(P, "center")
    step("prep ok (init, cut, voice, face)")
    # the cut-out: the drawn silhouette as a VP9 alpha WebM, exactly what prep.cutout writes
    D = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{P}/work/clean.mp4"]).stdout)
    run(["ffmpeg", "-y", "-v", "error", "-i", f"{P}/work/clean.mp4", "-loop", "1", "-framerate", "30", "-t", f"{D:.3f}", "-i", f"{src}/mask.png",
         "-filter_complex", "[1:v]format=gray,scale=1080:1920[m];[0:v][m]alphamerge,format=yuva420p[v]", "-map", "[v]", "-t", f"{D:.3f}",
         "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30", "-row-mt", "1", "-deadline", "realtime", "-cpu-used", "8", "-auto-alt-ref", "0",
         "-pix_fmt", "yuva420p", f"{P}/work/clean_subject.webm"])
    step(f"cut-out ok (VP9 alpha), clean take {D:.2f}s")
    if sys.platform == "darwin":
        vis = [n for n in ("person_mask", "face_track") if prep.vision_bin(n)]
        step(f"Apple Vision helpers that run here: {', '.join(vis) or 'none (OpenCV / hyperframes fallbacks will be used)'}")

    json.dump(plan(), open(f"{P}/plan.json", "w"), indent=1)
    py = sys.executable
    r = subprocess.run([py, f"{HERE}/plan_lint.py", P], capture_output=True, text=True)
    if "ERROR" in (r.stdout + r.stderr).upper().replace("0 ERRORS", ""): print(r.stdout[-1500:], r.stderr[-800:])
    step("plan_lint done")
    run([py, f"{HERE}/build.py", P]); step("build ok")
    lint = subprocess.run(hf("lint", "."), cwd=f"{P}/hf", capture_output=True, text=True)
    out = lint.stdout + lint.stderr
    if lint.returncode and " 0 error" not in out and "0 errors" not in out: raise SystemExit("hyperframes lint failed:\n" + out[-1500:])
    step("hyperframes lint ok")
    run([py, f"{HERE}/snap.py", P], env=gpu_env()); step(f"contact sheet → {P}/work/snap_sheet.jpg")
    if "--no-render" in a:
        step("render skipped (--no-render)"); return
    run(hf("render", f"{P}/hf", "-o", f"{P}/out/picture.mp4", "--fps", "30", "--quality", "draft"), env=gpu_env())
    step("render ok")
    fin = run([py, f"{HERE}/finish.py", P, f"{P}/out/picture.mp4", "--name", "selftest"])
    used = json.load(open(f"{P}/work/sfx_used.json"))
    kinds = sorted({u["kind"] for u in used})
    pr = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", f"{P}/out/selftest.mp4"]).stdout)
    types = sorted(s["codec_type"] for s in pr["streams"]); dur = float(pr["format"]["duration"])
    if types != ["audio", "video"] or abs(dur - D) > 0.3: raise SystemExit(f"unexpected output: streams {types}, {dur:.2f}s (expected {D:.2f}s)")
    tail = [l for l in fin.stdout.splitlines() if "LUFS" in l or "buried" in l][-2:]
    step(f"finish ok: {dur:.2f}s, sounds: {', '.join(kinds)}" + (f" · {' · '.join(tail)}" if tail else ""))
    print(f"\nSELFTEST OK in {time.time() - T0:.0f}s → {P}/out/selftest_light.mp4")


if __name__ == "__main__":
    main()
