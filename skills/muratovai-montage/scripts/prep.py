#!/usr/bin/env python3
"""Raw talking-head take → project folder ready for planning (tight jump cuts, words, voice, cutout, face track).

  python3 prep.py init   <raw.mp4> <project> [--lang en|ru|…] [--vocab "Name1, Name2"] [--script script.txt]
                         normalize to 1080x1920 @30, whisper word timings, work/phrases.txt for retake review
  python3 prep.py cut    <project> [--drop 3.2-7.9,20.1-22.4] [--keep 0.8-9.2,11.5-20.5] [--max-gap 0.18] [--style <profile>] [--hold-pause 3.2-3.9] [--keep-repeats] [--words-only]
                         keep only speech: every pause longer than max-gap is cut, marked retakes are dropped → work/clean.mp4, work/words.txt
  python3 prep.py words  <project> [--lang ..] [--script ..]   re-transcribe work/clean.mp4 (after cutting a take full of retakes)
  python3 prep.py voice  <project> [--isolate] [--chain]    work/voice.wav; --isolate = ElevenLabs voice isolation + EQ/compression chain,
                                                            --chain = the EQ/compression chain without isolation
  python3 prep.py cutout <project> [--engine auto|vision|u2net]   work/clean_subject.webm (person cut-out, VP9 with alpha)
  python3 prep.py face   <project> [--engine auto|vision|opencv|center]   work/face.json (face track for framing)
  python3 prep.py all    <raw.mp4> <project> [--lang ..] [--isolate] [--drop ..]

Keys (environment only): ELEVENLABS_API_KEY (Scribe transcription, required for init/words; also --isolate).
Engines: on macOS the cutout and the face track use Apple Vision (prebuilt arm64 binaries, rebuilt from the .swift sources
with swiftc when they do not run). Elsewhere the cutout uses `npx hyperframes remove-background` (local u2net model) and the
face track uses OpenCV (`pip install "opencv-python-headless<5"`) or, without it, a centred estimate.
Retakes: `cut --keep a-b,c-d,...` keeps only these ranges (their pauses are cut by the energy envelope), then
`words <project> --script text.txt` re-transcribes the clean cut: whisper glues repeated attempts, raw timings lie there.
Fixing words by hand: edit work/raw_words.json, then `cut --words-only` (cut rebuilds words.json, so edits to words.json are lost).
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import difflib, json, os, re, subprocess, sys, wave
try:
    import numpy as np
except ImportError:
    raise SystemExit("this script needs numpy and Pillow: python3 -m pip install -r requirements.txt (in the skill folder)")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import env_key, curl, sh, hf, load_style  # noqa: E402
import transcribe  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# names whisper tends to mangle in AI-tool reels; extend per take with --vocab
VOCAB = ("Claude Code, Claude, Anthropic, OpenAI, ChatGPT, Codex, Gemini, Google, GitHub, MCP, API, Kling, Seedance, Nano Banana, "
         "n8n, Cursor, Lovable, Vercel, OpenRouter, Perplexity, NotebookLM, HyperFrames, plugin, skill, prompt")
CHAIN = ("highpass=f=85:poles=2,equalizer=f=260:t=q:w=1.2:g=-2.5,equalizer=f=3200:t=q:w=1.0:g=2.5,equalizer=f=6500:t=q:w=1.2:g=1.5,"
         "deesser=i=0.35:m=0.5:f=0.5,acompressor=threshold=-19dB:ratio=3:attack=6:release=90:makeup=4:knee=4,alimiter=limit=0.89:level=0:attack=3:release=50")


def whisper(mp3, lang, prompt=VOCAB):
    """word timings with ElevenLabs Scribe (this fork has no OpenAI); the result keeps whisper's shape: text, words[word, start, end]"""
    return transcribe.scribe(mp3, lang, prompt)


def dur_of(p):
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p).stdout)


def rms_env(wav, hop=0.01):
    with wave.open(wav) as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels(); a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    a = a.reshape(-1, ch).mean(axis=1); h = int(sr * hop)
    return np.array([np.sqrt(np.mean(a[i * h:(i + 1) * h] ** 2)) + 1e-9 for i in range(len(a) // h)])


def punctuate(words, text):
    """copy trailing punctuation from whisper's full text onto word tokens (word-level output has none);
    re-join hyphenated words that whisper split (co-created → 'co' + 'created')"""
    toks = re.findall(r"[\w'’%$€₽.-]+[.,!?;:…]*", text)
    norm = lambda x: re.sub(r"[^\w%$€₽]", "", x.lower())
    out, j, i = [], 0, 0
    while i < len(words):
        w = dict(words[i])
        for k in range(j, min(j + 4, len(toks))):
            tk = toks[k]
            if "-" in tk.strip(".,!?;:…-") and i + 1 < len(words) and norm(tk) == norm(w["word"] + words[i + 1]["word"]):
                w = dict(word=tk.rstrip(".,!?;:…"), start=w["start"], end=words[i + 1]["end"]); i += 1
            if norm(tk) == norm(w["word"]):
                m = re.search(r"[.,!?;:…]+$", tk)
                if m and not w["word"].endswith(m.group(0)): w["word"] = w["word"] + m.group(0)
                j = k + 1; break
        out.append(w); i += 1
    return out


def video_stream(path):
    """Probe the displayed geometry and colour transfer before irreversible normalization."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    streams = json.loads(r.stdout)["streams"]
    if not streams: raise SystemExit(f"no video stream in {path}")
    stream = streams[0]
    rotation = int(float(stream.get("tags", {}).get("rotate", 0)))
    for side in stream.get("side_data_list", []):
        if "rotation" in side: rotation = int(float(side["rotation"]))
    width, height = int(stream["width"]), int(stream["height"])
    if rotation % 180: width, height = height, width
    return dict(width=width, height=height, rotation=rotation,
                color_transfer=stream.get("color_transfer", "unknown"),
                color_primaries=stream.get("color_primaries", "unknown"),
                color_space=stream.get("color_space", "unknown"))


def source_faces(video):
    """Use the same tracker as final framing, but on the uncropped displayed source."""
    tracker = vision_bin("face_track")
    if tracker:
        return json.loads(sh(tracker, video, "2").stdout), "vision"
    track = face_opencv(video)
    return (track or []), "opencv" if track is not None else "unavailable"


def crop_x_expression(track, source_width, source_height):
    """Smoothly follow the face in a wide source after scaling its height to 1920.

    Crop x is evaluated per frame by ffmpeg, so a subject walking across the take
    stays inside the 9:16 crop. Missing detections are bridged by interpolation.
    """
    scale = max(1080 / source_width, 1920 / source_height)
    scaled_width = source_width * scale
    limit = max(0.0, scaled_width - 1080)
    if limit < 1: return "0"
    points = sorted((float(f["t"]), min(limit, max(0.0, float(f["cx"]) * (source_width / f["W"]) * scale - 540)))
                    for f in track if all(k in f for k in ("t", "cx", "W")) and f["W"] > 0)
    if not points: raise SystemExit("wide source: no face was detected before cropping; supply a take with a visible face")
    # A single lost detection must not swing the camera. A three-sample median
    # removes isolated jumps, while leaving sustained movement intact.
    smooth = []
    for i, (t, x) in enumerate(points):
        vals = [points[j][1] for j in range(i - 1, i + 2)] if 0 < i < len(points) - 1 else [x]
        smooth.append((t, float(np.median(vals))))
    # Keep a point at least every 1.5 s and whenever the crop travels 16 px.
    key = [smooth[0]]
    for t, x in smooth[1:-1]:
        if t - key[-1][0] >= 1.5 or abs(x - key[-1][1]) >= 16: key.append((t, x))
    if len(smooth) > 1 and smooth[-1][0] > key[-1][0]: key.append(smooth[-1])
    if len(key) == 1: return f"{key[0][1]:.2f}"
    expr = f"{key[-1][1]:.2f}"
    for (a, x0), (b, x1) in reversed(list(zip(key, key[1:]))):
        slope = (x1 - x0) / max(0.001, b - a)
        expr = f"if(lt(t,{b:.3f}),{x0:.2f}+(t-{a:.3f})*{slope:.4f},{expr})"
    return expr


def hdr_filter(transfer):
    """Map PQ/HLG to Rec.709 using float linear light; fail if support is absent."""
    if transfer not in ("smpte2084", "arib-std-b67"): return []
    filters = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True, check=True).stdout
    if " zscale " not in filters:
        raise SystemExit("HDR source needs FFmpeg with zscale for correct Rec.709 tone mapping; install an FFmpeg build with libzimg")
    return ["zscale=t=linear:npl=100", "format=gbrpf32le", "tonemap=tonemap=mobius:desat=0", "zscale=p=bt709:t=bt709:m=bt709:r=tv"]


def init(raw, P, lang, vocab="", script=None):
    for d in ("work", "assets", "out"): os.makedirs(f"{P}/{d}", exist_ok=True)
    src = f"{P}/work/raw.mp4"
    source = video_stream(raw)
    scaled_width = source["width"] * max(1080 / source["width"], 1920 / source["height"])
    follow = scaled_width > 1110
    track, tracker = source_faces(raw) if follow else ([], "not_needed")
    x = crop_x_expression(track, source["width"], source["height"]) if follow else "(iw-ow)/2"
    vf = hdr_filter(source["color_transfer"]) + [
        "scale=1080:1920:force_original_aspect_ratio=increase",
        f"crop=1080:1920:x='{x}':y='(ih-oh)/2'", "fps=30", "setsar=1", "format=yuv420p"]
    sh("ffmpeg", "-y", "-v", "error", "-i", raw, "-vf", ",".join(vf),
       "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-g", "30", "-keyint_min", "30", "-pix_fmt", "yuv420p",
       "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
       "-af", "aresample=async=1:first_pts=0", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", src)
    # phone MOVs often start the sound 0.1–0.7 s after the picture; first_pts=0 pads that gap with silence, so every extracted
    # wav/mp3 and every whisper time below is on the picture's clock (without it captions and cuts slide by the offset)
    sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", f"{P}/work/raw16.mp3")
    sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "44100", f"{P}/work/raw.wav")
    r = whisper(f"{P}/work/raw16.mp3", lang, VOCAB + (", " + vocab if vocab else "")); r["words"] = punctuate(r.get("words", []), r.get("text", ""))
    if script:
        json.dump(r, open(f"{P}/work/raw_words.whisper.json", "w"), ensure_ascii=False, indent=0)
        r["words"] = align_script(r["words"], open(script).read()); print(f"script aligned: {len(r['words'])} words (whisper's own result kept in work/raw_words.whisper.json)")
    json.dump(r, open(f"{P}/work/raw_words.json", "w"), ensure_ascii=False, indent=0)
    W = r.get("words", [])
    # phrase list for retake review: split at pauses > 0.45 s
    lines, cur = [], []
    for w in W:
        if cur and w["start"] - cur[-1]["end"] > 0.45: lines.append(cur); cur = []
        cur.append(w)
    if cur: lines.append(cur)
    txt = [f"{k:02d} [{L[0]['start']:6.2f}-{L[-1]['end']:6.2f}] {' '.join(x['word'] for x in L)}" for k, L in enumerate(lines)]
    open(f"{P}/work/phrases.txt", "w").write("\n".join(txt) + "\n")
    repeats = retake_candidates(W)
    json.dump(repeats, open(f"{P}/work/retakes.json", "w"), indent=1)
    json.dump(dict(raw=os.path.abspath(raw), lang=lang, duration=dur_of(src), source=source,
                   vocab_names=[name.strip() for name in vocab.split(",") if name.strip()],
                   crop=dict(mode="face_follow" if follow else "center", tracker=tracker, detections=sum("cx" in f for f in track))),
              open(f"{P}/work/source.json", "w"))
    print(f"init: {dur_of(src):.1f}s, {len(W)} words, {len(lines)} phrases, {len(repeats)} possible retakes → {P}/work/phrases.txt (mark retakes with --drop)")


def align_script(words, script):
    """lay the known script text over whisper's word timings: keeps whisper's times, takes the script's spelling and punctuation.
    Whisper drops full stops in some languages and mangles product names; the script says what was meant. Words the speaker added
    stay as whisper heard them; script words he skipped are dropped."""
    import difflib
    toks = re.findall(r"[\w'’%$€₽+#-]+[.,!?;:…»\")]*", script)   # shown as written (ё stays); matching ignores ё/е below
    norm = lambda x: re.sub(r"[^\w%$€₽+#]", "", x.lower().replace("ё", "е"))
    A = [norm(w["word"]) for w in words]; B = [norm(t) for t in toks]; out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
        if op == "equal":
            out += [dict(words[i1 + k], word=toks[j1 + k]) for k in range(i2 - i1)]
        elif op == "replace":
            span = words[i1:i2]; a0, a1 = span[0]["start"], span[-1]["end"]; T = toks[j1:j2]
            if len(T) == len(span): out += [dict(span[k], word=T[k]) for k in range(len(T))]
            elif len(T) <= 2 * len(span) + 2:   # re-split the span by character count
                L = [max(1, len(norm(t))) for t in T]; tot = sum(L); t = a0
                for tk, l in zip(T, L):
                    d = (a1 - a0) * l / tot; out.append(dict(word=tk, start=round(t, 3), end=round(t + d, 3))); t += d
            else: out += span   # too different to trust: keep what was heard
        elif op == "delete": out += words[i1:i2]
    return out


def keep_segments(env, keep, max_gap, pre, post, thr, D):
    """speech segments inside the kept ranges, from the energy envelope only: every silence longer than max_gap goes"""
    segs = []
    for a, b in keep:
        i0, i1 = int(a / 0.01), min(len(env), int(b / 0.01)); on = env[i0:i1] > thr; k = 0
        while k < len(on):
            if not on[k]: k += 1; continue
            j = k
            while j + 1 < len(on) and (on[j + 1] or on[j + 1:j + 1 + int(max_gap / 0.01)].any()): j += 1
            s0 = max(a, (i0 + k) * 0.01 - pre); s1 = min(b, D, (i0 + j + 1) * 0.01 + post)
            if s1 - s0 > 0.12:
                if segs and s0 - segs[-1][1] < 0.02: segs[-1][1] = s1
                else: segs.append([round(s0, 3), round(s1, 3)])
            k = j + 1
    return segs


def retake_candidates(words):
    """Find nearby nearly identical clauses; editorial choice stays explicit."""
    groups, current = [], []
    for i, word in enumerate(words):
        current.append(word)
        next_word = words[i + 1] if i + 1 < len(words) else None
        if re.search(r"[.!?]$", word["word"]) or next_word is None or next_word["start"] - word["end"] > 0.45:
            if len(current) >= 3: groups.append(current)
            current = []
    normalized = lambda group: " ".join(re.sub(r"[^\w]+", "", w["word"].casefold()) for w in group)
    found = []
    for i, first in enumerate(groups):
        a = normalized(first)
        for second in groups[i + 1:]:
            if second[0]["start"] - first[-1]["end"] > 30: break
            b = normalized(second)
            if min(len(a), len(b)) < 12: continue
            if difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() >= .86:
                found.append(dict(first=[first[0]["start"], first[-1]["end"]],
                                  second=[second[0]["start"], second[-1]["end"]]))
    return found


def merge_held_pauses(segments, words, holds, rhetorical_gap, drop=(), keep=None):
    """Keep a bounded phrase-ending pause or an explicitly protected raw interval."""
    if not 0 <= rhetorical_gap <= .9: raise ValueError("rhetorical gap must be between 0 and 0.9 s")
    if any(b <= a or b - a > 2.0 for a, b in holds): raise ValueError("each --hold-pause range must last > 0 and <= 2.0 s")
    if len(segments) < 2: return segments
    out = [list(segments[0])]
    for seg in segments[1:]:
        left, right = out[-1][1], seg[0]
        requested = any(a < right and b > left for a, b in holds)
        protected = any(a <= left and b >= right for a, b in holds)
        before = next((w for w in reversed(words) if w["end"] <= left + .15), None)
        after = next((w for w in words if w["start"] >= right - .15), None)
        word_gap = after["start"] - before["end"] if before and after else float("inf")
        rhetorical = bool(before and re.search(r"[.!?…]$", before["word"])) and 0 < word_gap <= rhetorical_gap
        crosses_drop = any(a < right and b > left for a, b in drop)
        inside_keep = keep is None or any(a <= out[-1][0] and seg[1] <= b for a, b in keep)
        if requested and not protected and inside_keep and not crosses_drop:
            raise ValueError(f"--hold-pause must cover the full omitted gap {left:.2f}-{right:.2f}s; a partial overlap would restore unrequested footage")
        if (protected or rhetorical) and inside_keep and not crosses_drop:
            out[-1][1] = seg[1]
        else: out.append(list(seg))
    return out


def words(P, lang, vocab="", script=None):
    """whisper on work/clean.mp4 itself → words.json / words.txt (+ script spelling and punctuation). Use after cut when the take
    had retakes: whisper glues repeated attempts together, so raw timings remapped by cut can point at the wrong attempt."""
    mp3 = f"{P}/work/clean16.mp3"; sh("ffmpeg", "-y", "-v", "error", "-i", f"{P}/work/clean.mp4", "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", mp3)
    r = whisper(mp3, lang, VOCAB + (", " + vocab if vocab else "")); W = punctuate(r.get("words", []), r.get("text", ""))
    if script: W = align_script(W, open(script).read())
    W = [dict(word=w["word"], start=round(w["start"], 3), end=round(w["end"], 3)) for w in W]
    old = json.load(open(f"{P}/work/words.json")) if os.path.exists(f"{P}/work/words.json") else {}
    json.dump(dict(words=W, segments=old.get("segments", [])), open(f"{P}/work/words.json", "w"), ensure_ascii=False, indent=0)
    open(f"{P}/work/words.txt", "w").write("\n".join(f"{i:3d} {w['start']:7.2f} {w['word']}" for i, w in enumerate(W)) + "\n")
    print(f"words: {len(W)} words from the clean cut → work/words.txt")


def cut(P, drop, max_gap, pre, post, words_only=False, keep=None, hold_pause=(), rhetorical_gap=.54, keep_repeats=False):
    W = json.load(open(f"{P}/work/raw_words.json"))["words"]; src = f"{P}/work/raw.mp4"; D = dur_of(src)
    dropped = lambda w: any(a <= (w["start"] + w["end"]) / 2 <= b for a, b in drop)
    W = [w for w in W if not dropped(w)]
    selected = [w for w in W if keep is None or any(a <= (w["start"] + w["end"]) / 2 <= b for a, b in keep)]
    repeats = retake_candidates(selected)
    if repeats and not keep_repeats:
        spans = ", ".join(f"{r['first'][0]:.2f}-{r['first'][1]:.2f} / {r['second'][0]:.2f}-{r['second'][1]:.2f}" for r in repeats[:5])
        raise SystemExit(f"cut: possible repeated take at {spans}; choose --drop or --keep after listening, or --keep-repeats for intentional repetition")
    env = rms_env(f"{P}/work/raw.wav"); speech_lvl = np.median(env[env > np.percentile(env, 60)]); thr = speech_lvl * 0.12
    def refine_end(t):   # extend until energy falls (trailing consonants), max +0.12 s
        i = int(t / 0.01)
        for k in range(i, min(len(env), i + 12)):
            if env[k] < thr: return k * 0.01
        return t + 0.12
    def refine_start(t):  # move back to onset, max -0.10 s
        i = int(t / 0.01)
        for k in range(i, max(0, i - 10), -1):
            if env[k] < thr: return k * 0.01
        return t - 0.1
    segs = keep_segments(env, keep, max_gap, pre, post, thr, D) if keep else []
    for w in ([] if keep else W):
        a = max(0.0, refine_start(w["start"]) - pre); b = min(D, refine_end(w["end"]) + post)
        if segs and a - segs[-1][1] <= max_gap - pre - post: segs[-1][1] = max(segs[-1][1], b)
        elif segs and a < segs[-1][1]: segs[-1][1] = max(segs[-1][1], b)
        else: segs.append([a, b])
    segs = merge_held_pauses(segs, selected, hold_pause, rhetorical_gap, drop, keep)
    if not segs: raise SystemExit("cut: no speech found (check work/raw_words.json and the --keep/--drop ranges)")
    fc, lab = [], ""
    for i, (a, b) in enumerate(segs):
        d = b - a
        fc.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}]")
        fc.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.008,afade=t=out:st={max(d - 0.008, 0):.3f}:d=0.008[a{i}]")
        lab += f"[v{i}][a{i}]"
    fc.append(f"{lab}concat=n={len(segs)}:v=1:a=1[v][a]")
    script = f"{P}/work/_cut_filter.txt"; open(script, "w").write(";\n".join(fc))
    if not words_only:   # ffmpeg ≥ 7 reads long graphs with -/filter_complex <file> (-filter_complex_script is gone in 9)
        sh("ffmpeg", "-y", "-v", "error", "-i", src, "-/filter_complex", script, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
           "-g", "30", "-keyint_min", "30", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", f"{P}/work/clean.mp4")
    # remap word timings into the clean timeline
    out, c = [], 0.0
    for a, b in segs:
        for w in W:
            if a <= w["start"] < b: out.append(dict(word=w["word"], start=round(c + w["start"] - a, 3), end=round(min(c + w["end"] - a, c + b - a), 3)))
        c += b - a
    json.dump(dict(words=out, segments=segs), open(f"{P}/work/words.json", "w"), ensure_ascii=False, indent=0)
    open(f"{P}/work/words.txt", "w").write("\n".join(f"{i:3d} {w['start']:7.2f} {w['word']}" for i, w in enumerate(out)) + "\n")
    gaps = sorted(b["start"] - a["end"] for a, b in zip(out, out[1:]))
    wps = len(out) / max(out[-1]["end"] - out[0]["start"], 1) if out else 0
    print(f"cut: {D:.1f}s → {dur_of(f'{P}/work/clean.mp4'):.1f}s, {len(segs)} segments, {len(out)} words, {wps:.2f} words/s, gap p90 {gaps[int(len(gaps) * .9)] if gaps else 0:.2f}s → work/words.txt")


def voice(P, isolate, chain=False):
    raw = f"{P}/work/voice_raw.wav"; out = f"{P}/work/voice.wav"
    sh("ffmpeg", "-y", "-v", "error", "-i", f"{P}/work/clean.mp4", "-vn", "-ac", "1", "-ar", "44100", raw)
    key = env_key("ELEVENLABS_API_KEY", required=False) if isolate else None
    if isolate and not key: print("voice: ELEVENLABS_API_KEY is not set, so there is no isolation; applying the EQ/compression chain only"); chain = True
    if key:
        iso = f"{P}/work/voice_iso.mp3"
        code = curl("https://api.elevenlabs.io/v1/audio-isolation", f"xi-api-key: {key}", "-X", "POST", "-F", f"audio=@{raw}", "-o", iso, "-w", "%{http_code}", timeout=400)
        if code.strip() != "200": raise SystemExit(f"voice isolation: HTTP {code.strip()} (check the ElevenLabs plan and key)")
        sh("ffmpeg", "-y", "-v", "error", "-i", iso, "-af", CHAIN, "-ar", "48000", "-ac", "2", out)
    elif chain:
        sh("ffmpeg", "-y", "-v", "error", "-i", raw, "-af", CHAIN, "-ar", "48000", "-ac", "2", out)
    else:
        sh("ffmpeg", "-y", "-v", "error", "-i", raw, "-af", "highpass=f=80,alimiter=limit=0.9:level=0", "-ar", "48000", "-ac", "2", out)
    print("voice →", out, "(isolated + chain)" if key else "(chain)" if chain else "(light: high-pass + limiter)")


def vision_bin(name):
    """path of a working Apple Vision helper (prebuilt arm64, or rebuilt from its .swift source with swiftc); None if unavailable"""
    if sys.platform != "darwin": return None
    shipped, src = os.path.join(HERE, name), os.path.join(HERE, f"{name}.swift")
    local = f"{shipped}.local"   # a local rebuild sits next to the shipped binary and never overwrites it
    def works(p):
        try: return os.path.exists(p) and subprocess.run([p], capture_output=True, text=True, timeout=30).returncode in (0, 1)   # usage message = it runs
        except (OSError, subprocess.SubprocessError): return False
    for p in (shipped, local):
        if works(p): return p
    try:
        r = subprocess.run(["swiftc", "-O", "-target", f"{os.uname().machine}-apple-macos12.0", "-o", local, src], capture_output=True, text=True)
        if r.returncode == 0 and works(local): return local
        print(f"{name}: could not rebuild with swiftc: {r.stderr[-300:]}")
    except OSError:
        print(f"{name}: the prebuilt binary does not run here and swiftc is missing (install the Xcode command line tools: xcode-select --install)")
    return None


def cutout(P, engine="auto"):
    """person cut-out of clean.mp4 as VP9+alpha WebM. 'vision' = macOS Apple Vision person segmentation (clean hair edges, no
    background blobs, ~2 min per minute of video); 'u2net' = `npx hyperframes remove-background` (local model, any OS,
    ~3 min per minute, can keep bright blobs near the hair). 'auto' = vision when it runs, else u2net."""
    out = f"{P}/work/clean_subject.webm"
    binp = vision_bin("person_mask") if engine in ("auto", "vision") else None
    if engine == "vision" and not binp: raise SystemExit("cutout: Apple Vision is unavailable here (macOS 12+ only); use --engine u2net")
    if binp:
        sh(binp, f"{P}/work/clean.mp4", f"{P}/work/clean_mask.mp4")
        sh("ffmpeg", "-y", "-v", "error", "-i", f"{P}/work/clean.mp4", "-i", f"{P}/work/clean_mask.mp4", "-filter_complex",
           "[1:v]format=gray,scale=1080:1920[m];[0:v][m]alphamerge,format=yuva420p[v]", "-map", "[v]", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "20",
           "-row-mt", "1", "-deadline", "good", "-cpu-used", "4", "-auto-alt-ref", "0", "-pix_fmt", "yuva420p", out)
        engine = "vision"
    else:
        r = subprocess.run(hf("remove-background", f"{P}/work/clean.mp4", "-o", out, "--quality", "best"), capture_output=True, text=True)
        if r.returncode or not os.path.exists(out): raise SystemExit("remove-background failed:\n" + (r.stderr or r.stdout)[-800:])
        engine = "u2net"
    print(f"cutout ({engine}) →", out)


def face_opencv(video, fps=2.0):
    """OpenCV Haar-cascade face track in the face_track JSON format; None when opencv is not installed"""
    try: import cv2
    except ImportError: return None
    if not hasattr(cv2, "CascadeClassifier"):   # OpenCV 5 moved the Haar cascades out of the main package
        print(f"face: OpenCV {cv2.__version__} has no Haar cascades; install opencv-python-headless<5 for this fallback"); return None
    casc = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    cap = cv2.VideoCapture(video); vfps = cap.get(cv2.CAP_PROP_FPS) or 30; n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); out, t = [], 0.0
    while t * vfps < n:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * vfps)); ok, fr = cap.read()
        if not ok: break
        H, W = fr.shape[:2]; g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        faces = casc.detectMultiScale(g, scaleFactor=1.1, minNeighbors=6, minSize=(int(W * 0.12), int(W * 0.12)))
        if len(faces):
            x, y, w, h = [float(v) for v in max(faces, key=lambda f: f[2])]
            y += h * 0.06; h *= 0.94; x += w * 0.035; w *= 0.93   # Haar boxes are ~7 % wider and start higher than Apple Vision's (calibrated on a test take)
            out.append(dict(t=t, x=x, y=y, w=w, h=h, eye_y=y + h * 0.36, cx=x + w / 2, W=float(W), H=float(H)))
        else: out.append(dict(t=t, W=float(W), H=float(H)))
        t += 1.0 / fps
    return out


def face(P, engine="auto"):
    video = f"{P}/work/clean.mp4"; data = None; used = engine
    if engine in ("auto", "vision"):
        binp = vision_bin("face_track")
        if binp: data = json.loads(sh(binp, video, "2").stdout); used = "vision"
        elif engine == "vision": raise SystemExit("face: Apple Vision is unavailable here; use --engine opencv or center")
    if data is None and engine in ("auto", "opencv"):
        data = face_opencv(video); used = "opencv"
        if data is None and engine == "opencv": raise SystemExit("face: OpenCV with Haar cascades is not installed (pip install \"opencv-python-headless<5\")")
    if data is None:   # no tracker at all: a centred talking head, face ≈ 1/3 of the frame width, eyes at 0.40 of its height
        used = "center"; D = dur_of(video)
        data = [dict(t=k * 0.5, x=360.0, y=560.0, w=360.0, h=420.0, eye_y=768.0, cx=540.0, W=1080.0, H=1920.0) for k in range(int(D * 2) + 1)]
        if engine == "auto":
            print("face: no face tracker available (Apple Vision on macOS, or pip install \"opencv-python-headless<5\"); using a centred estimate. "
                  "Framing will be approximate: check the head in snap.py's contact sheet.")
    open(f"{P}/work/face.json", "w").write(json.dumps(data))
    F = [f for f in data if "w" in f]
    if not F: raise SystemExit("face: no face found in work/clean.mp4")
    print(f"face ({used}): {len(F)} samples, face width median {sorted(f['w'] for f in F)[len(F) // 2]:.0f}px (targets: split 418, close-up 754)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): raise SystemExit(__doc__)
    opt = lambda k, d=None: (a[a.index(k) + 1] if k in a else d)
    lang = opt("--lang", "en"); drop = [tuple(map(float, x.split("-"))) for x in opt("--drop", "").split(",") if x]
    mg, pre, post = float(opt("--max-gap", 0.18)), float(opt("--pre", 0.05)), float(opt("--post", 0.06))
    cmd = a[0]
    vocab = opt("--vocab", "")   # extra product names for whisper, e.g. --vocab "HyperFrames, Kimi"
    script = opt("--script")     # the text the speaker read: restores punctuation and spelling on top of whisper's timings
    style = opt("--style")
    style_gap = load_style(style, os.path.abspath(a[1] if cmd == "cut" else a[2]))["pace"].get("gap_p90", .18) if style and cmd in ("cut", "all") else .18
    rhetorical_gap = float(opt("--rhetorical-gap", min(.9, max(.4, 3 * float(style_gap)))))
    holds = [tuple(map(float, x.split("-"))) for x in opt("--hold-pause", "").split(",") if x]
    if cmd == "init": init(a[1], os.path.abspath(a[2]), lang, vocab, script)
    elif cmd == "cut":
        keep = [tuple(map(float, x.split("-"))) for x in opt("--keep", "").split(",") if x] or None
        cut(os.path.abspath(a[1]), drop, mg, pre, post, "--words-only" in a, keep, holds, rhetorical_gap, "--keep-repeats" in a)
    elif cmd == "words": words(os.path.abspath(a[1]), lang, vocab, script)
    elif cmd == "voice": voice(os.path.abspath(a[1]), "--isolate" in a, "--chain" in a)
    elif cmd == "cutout": cutout(os.path.abspath(a[1]), opt("--engine", "auto"))
    elif cmd == "face": face(os.path.abspath(a[1]), opt("--engine", "auto"))
    elif cmd == "all":
        P = os.path.abspath(a[2]); init(a[1], P, lang, vocab, script); cut(P, drop, mg, pre, post, hold_pause=holds,
                                                                         rhetorical_gap=rhetorical_gap, keep_repeats="--keep-repeats" in a)
        voice(P, "--isolate" in a, "--chain" in a); face(P, opt("--face-engine", "auto")); cutout(P, opt("--engine", "auto"))
    else: raise SystemExit(__doc__)
