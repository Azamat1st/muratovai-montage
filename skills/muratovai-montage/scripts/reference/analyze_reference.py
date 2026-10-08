#!/usr/bin/env python3
"""Measure how a creator's reels are edited and write a style profile. Works on any folder with raw/*.mp4 (see fetch_reels.py).
Fork without OpenAI: speech → ElevenLabs Scribe, frame tags → the agent itself, in the session (Claude Code or Codex), sound → Demucs stems.

  python3 analyze_reference.py <dir> prep          # probe, audio, 2 fps frames, contact sheets, scene scores, loudness (local, free)
  python3 analyze_reference.py <dir> words         # ElevenLabs Scribe word timestamps (--lang en|ru|uz|…, default en)
  python3 analyze_reference.py <dir> vision        # frame grids + vision_task.md per reel for the agent to tag (local, free)
  python3 analyze_reference.py <dir> vision-import # the agent's work/<id>/vision_tags.tsv → vision.json (checks every value)
  python3 analyze_reference.py <dir> stems         # Demucs voice/background split → music bed level and SFX density (local, free)
  python3 analyze_reference.py <dir> report        # per-reel metrics.json, colours, framing → STYLE_METRICS.md, style.json, style-bible.draft.md
  python3 analyze_reference.py <dir> all           # prep, words, stems, vision; then report once every reel has vision.json

Outputs in <dir>/work/<id>/: audio16.mp3, audio.wav, frames/NNNN.jpg (2 fps, 360x640), sheet.jpg (contact sheet, 10 tiles per row,
tile k = k·0.5 s), scenes.json, loud.json, words.json, vision_grids/, vision_task.md, vision_tags.tsv, vision.json, stems/,
audio_metrics.json, metrics.json. Profile files in <dir>/: STYLE_METRICS.md (medians), style.json (machine targets for
plan_lint.py, qa.py, finish.py, build.py) and style-bible.draft.md (numbers filled in, rules left for you to write from the
contact sheets and beat sheets → style-bible.md).

Keys and options (environment): ELEVENLABS_API_KEY (required for words). DEMUCS_PY = a python that has demucs installed
(default: this python, if it can import demucs). Nobody listens to the music: the sound is described by the stems numbers
(audio_metrics.json) and sfx_probe.py / sfx_extract.py.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import collections, concurrent.futures as cf, glob, json, math, os, re, statistics as st, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from common import SKILL, env_key  # noqa: E402
import transcribe  # noqa: E402
import vision_tags  # noqa: E402
import timeline  # noqa: E402
from vision_tags import FPS_SAMPLE  # noqa: E402

VOCAB = ("Claude Code, Claude, Anthropic, OpenAI, ChatGPT, Gemini, Google, GitHub, MCP, Kling, Seedance, Nano Banana, n8n, Cursor, Lovable, "
         "Vercel, Perplexity, Grok, Kimi, Mistral, Qwen, API, plugin, skill, prompt, SEO, vibe coding")


def sh(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)


def reels(d):
    return sorted(glob.glob(f"{d}/raw/*.mp4"))


def rid(p):
    return os.path.splitext(os.path.basename(p))[0]


def demucs_python():
    """a python that can run demucs, or None: $DEMUCS_PY, else this interpreter if it imports demucs"""
    cand = os.environ.get("DEMUCS_PY") or sys.executable
    return cand if sh(cand, "-c", "import demucs").returncode == 0 else None


# ---------------------------------------------------------------- prep
def prep_one(p, d):
    w = f"{d}/work/{rid(p)}"; os.makedirs(f"{w}/frames", exist_ok=True)
    pr = json.loads(sh("ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate", "-of", "json", p).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video"); dur = float(pr["format"]["duration"])
    info = dict(id=rid(p), dur=dur, w=v["width"], h=v["height"], fps=v["r_frame_rate"], has_audio=any(s["codec_type"] == "audio" for s in pr["streams"]))
    if info["has_audio"] and not os.path.exists(f"{w}/audio16.mp3"):
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", f"{w}/audio16.mp3")
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vn", "-ac", "2", "-ar", "44100", f"{w}/audio.wav")
    if not glob.glob(f"{w}/frames/*.jpg"):
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf", f"fps={FPS_SAMPLE},scale=360:640:force_original_aspect_ratio=decrease,pad=360:640:(ow-iw)/2:(oh-ih)/2", "-q:v", "3", f"{w}/frames/%04d.jpg")
    if not os.path.exists(f"{w}/sheet.jpg"):
        n = len(glob.glob(f"{w}/frames/*.jpg")); rows = math.ceil(n / 10)
        sh("ffmpeg", "-y", "-v", "error", "-framerate", "1", "-i", f"{w}/frames/%04d.jpg", "-vf", f"scale=180:320,tile=10x{rows}", "-frames:v", "1", "-q:v", "4", f"{w}/sheet.jpg")
    if not os.path.exists(f"{w}/scenes.json"):
        out = sh("ffmpeg", "-v", "error", "-i", p, "-vf", "scale=270:480,select='gte(scene,0)',metadata=print:key=lavfi.scene_score:file=-", "-an", "-f", "null", "-").stdout
        ts, sc = [], []
        for line in out.splitlines():
            m = re.search(r"pts_time:([\d.]+)", line)
            if m: ts.append(float(m.group(1)))
            m = re.search(r"lavfi.scene_score=([\d.]+)", line)
            if m: sc.append(float(m.group(1)))
        json.dump(dict(t=ts[:len(sc)], score=sc), open(f"{w}/scenes.json", "w"))
    if info["has_audio"] and not os.path.exists(f"{w}/loud.json"):
        err = sh("ffmpeg", "-v", "info", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-").stderr
        I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1]); LRA = float(re.findall(r"LRA:\s+([\d.]+) LU", err)[-1])
        tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err); json.dump(dict(I=I, LRA=LRA, true_peak=float(tp[-1]) if tp else None), open(f"{w}/loud.json", "w"))
    json.dump(info, open(f"{w}/info.json", "w")); return info["id"]


# ---------------------------------------------------------------- words
def words_one(p, d, lang, vocab):
    w = f"{d}/work/{rid(p)}"
    if os.path.exists(f"{w}/words.json") or not os.path.exists(f"{w}/audio16.mp3"): return rid(p)
    r = transcribe.scribe(f"{w}/audio16.mp3", lang, vocab)
    json.dump(r, open(f"{w}/words.json", "w"), ensure_ascii=False); return f"{rid(p)} ({len(r['words'])} words)"


# ---------------------------------------------------------------- vision (tagged by the agent, see vision_tags.py)
def vision_one(p, d):
    return vision_tags.export(f"{d}/work/{rid(p)}", d)


def vision_import_one(p, d):
    try: return vision_tags.import_tags(f"{d}/work/{rid(p)}")
    except ValueError as e: return f"{rid(p)}: fix {vision_tags.TAGS}:\n{e}"


# ---------------------------------------------------------------- stems
def stems_one(p, d, py):
    w = f"{d}/work/{rid(p)}"
    if not os.path.exists(f"{w}/audio.wav"): return f"{rid(p)}: no sound"
    if not os.path.exists(f"{w}/stems/no_vocals.wav"):
        os.makedirs(f"{w}/stems", exist_ok=True)
        r = sh(py, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", f"{w}/_demucs", f"{w}/audio.wav")
        base = f"{w}/_demucs/htdemucs/audio"
        if not os.path.exists(f"{base}/no_vocals.wav"): return f"{rid(p)} demucs failed: {r.stderr[-300:]}"
        os.replace(f"{base}/vocals.wav", f"{w}/stems/vocals.wav"); os.replace(f"{base}/no_vocals.wav", f"{w}/stems/no_vocals.wav")
    import numpy as np, wave
    def load(f):
        with wave.open(f) as wf:
            n, ch, sr = wf.getnframes(), wf.getnchannels(), wf.getframerate(); a = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32) / 32768
        return a.reshape(-1, ch).mean(axis=1), sr
    voc, sr = load(f"{w}/stems/vocals.wav"); bg, _ = load(f"{w}/stems/no_vocals.wav")
    hop = int(sr * 0.02); n = min(len(voc), len(bg)) // hop
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    rv = np.array([db(voc[i * hop:(i + 1) * hop]) for i in range(n)]); rb = np.array([db(bg[i * hop:(i + 1) * hop]) for i in range(n)])
    speech = rv > -40
    bed = rb[speech] if speech.any() else rb
    sec = [float(np.median(rb[i:i + 50])) for i in range(0, n, 50) if len(rb[i:i + 50]) >= 25]
    on = []   # SFX: onsets in the background = jump of > 9 dB over the previous 100 ms median, local max, background above -38 dBFS
    for i in range(5, n - 1):
        if rb[i] > -38 and rb[i] - np.median(rb[max(0, i - 5):i]) > 9 and rb[i] >= rb[i - 1] and rb[i] >= rb[i + 1]:
            if not on or i * 0.02 - on[-1] > 0.15: on.append(round(i * 0.02, 2))
    sc = json.load(open(f"{w}/scenes.json")); cuts = [p["t_s"] for p in timeline.scene_points(sc, n * 0.02, threshold=0.3)]
    hit = sum(1 for c in cuts if any(abs(c - o) <= 0.12 for o in on))
    voice_ref = float(np.median(rv[speech])) if speech.any() else None
    events = []
    for t in on:
        i = round(t / 0.02)
        peak = float(np.max(rb[i:min(n, i + 5)]))
        prior = rb[max(0, i - 50):max(1, i - 5)]
        bed_before = float(np.median(prior)) if len(prior) else None
        local_voice = float(np.median(rv[i:min(n, i + 5)]))
        near_cut = min(cuts, key=lambda c: abs(c - t)) if cuts else None
        events.append(dict(t_s=t, peak_20ms_dbfs=round(peak, 1),
                           peak_rel_voice_db=round(peak - voice_ref, 1) if voice_ref is not None else None,
                           peak_rel_local_voice_db=round(peak - local_voice, 1),
                           peak_above_bed_db=round(peak - bed_before, 1) if bed_before is not None else None,
                           nearest_cut_offset_ms=round((t - near_cut) * 1000) if near_cut is not None and abs(t - near_cut) <= 0.5 else None,
                           source="demucs_background_transient", classification="candidate"))
    m = dict(voice_median_db=round(float(np.median(rv[speech])), 1) if speech.any() else None,
             bg_under_speech_median_db=round(float(np.median(bed)), 1), bg_1s_medians=[round(x, 1) for x in sec],
             bg_rel_voice_db=round(float(np.median(bed) - np.median(rv[speech])), 1) if speech.any() else None,
             music_bed_share=round(sum(1 for x in sec if x > -50) / max(len(sec), 1), 2),
             sfx_onsets=on, sfx_events=events, sfx_per_10s=round(len(on) / (n * 0.02) * 10, 2), cuts=len(cuts), cuts_with_sfx=hit,
             cuts_with_sfx_share=round(hit / max(len(cuts), 1), 2))
    for key in ("peak_rel_voice_db", "peak_above_bed_db"):
        m[f"sfx_{key}"] = timeline.median_or_none([event[key] for event in events])
    m["sfx_cut_offset_s"] = timeline.median_or_none([event["nearest_cut_offset_ms"] / 1000 for event in events
                                                     if event["nearest_cut_offset_ms"] is not None], 3)
    json.dump(m, open(f"{w}/audio_metrics.json", "w")); return rid(p)


# ---------------------------------------------------------------- colours and framing
def palette_one(w):
    """dominant colours of the frames (coarse 16-level quantisation) and the saturated ones among them (accent candidates)"""
    try:
        from PIL import Image
        import numpy as np
    except ImportError: return {}
    import colorsys
    tot, top = collections.Counter(), collections.Counter()
    for f in sorted(glob.glob(f"{w}/frames/*.jpg")):
        a = (np.asarray(Image.open(f).convert("RGB").resize((36, 64))) // 16 * 16 + 8).reshape(-1, 3)
        px = [tuple(int(v) for v in row) for row in a]
        tot.update(px); top.update(px[:36 * 29])   # top 45 % of the frame, where graphics live in a split
    n = max(sum(tot.values()), 1); hexc = lambda c: "#%02X%02X%02X" % c
    sat = [(c, k) for c, k in tot.most_common(200) if (lambda h, s, v: s > 0.45 and v > 0.35)(*colorsys.rgb_to_hsv(*(x / 255 for x in c)))]
    return dict(colors=[[hexc(c), round(k / n, 3)] for c, k in tot.most_common(8)],
                top_zone=[[hexc(c), round(k / max(sum(top.values()), 1), 3)] for c, k in top.most_common(5)],
                saturated=[[hexc(c), round(k / n, 4)] for c, k in sat[:5]])


def framing_one(p, w, info):
    """Face targets plus a portable, normalised timecoded track (Apple Vision or OpenCV)."""
    if not os.path.exists(f"{w}/vision.json"): return {}, []
    try:
        sys.path.insert(0, os.path.join(HERE, "..")); import prep
        binp = prep.vision_bin("face_track")
        faces = json.loads(sh(binp, p, str(FPS_SAMPLE)).stdout) if binp else prep.face_opencv(p, FPS_SAMPLE)
    except Exception as e:
        print(f"framing skipped for {rid(p)}: {e}"); return {}, []
    if not faces: return {}, []
    tags = json.load(open(f"{w}/vision.json"))["frames"]; by = collections.defaultdict(list)
    track = []
    vertical = abs(info["h"] / max(info["w"], 1) - 16 / 9) <= 0.06
    for fr in faces:
        if not all(k in fr for k in ("t", "w", "h", "eye_y", "cx", "W", "H")) or not fr["W"] or not fr["H"]: continue
        t = float(fr["t"]); index = min(round(t * FPS_SAMPLE), len(tags) - 1)
        if index < 0: continue
        tg = tags[index]
        if "error" in tg: continue
        track.append(dict(t_s=round(t, 3), cx=round(fr["cx"] / fr["W"], 4),
                          eye_y=round(fr["eye_y"] / fr["H"], 4), w=round(fr["w"] / fr["W"], 4),
                          h=round(fr["h"] / fr["H"], 4), layout=tg["layout"], source="face_tracker"))
        if not vertical: continue
        k = 1080 / fr["W"]
        mode = "split" if tg["layout"] == "split_graphic_top_face_bottom" else ("close" if tg["face"] == "closeup" else "medium") if tg["layout"] in ("face_full", "face_full_with_card_overlay") else None
        if mode: by[mode].append((fr["w"] * k, fr["eye_y"] * k, fr["cx"] * k))
    return ({m: dict(w=round(st.median(x[0] for x in v)), eye=round(st.median(x[1] for x in v)), cx=round(st.median(x[2] for x in v)), n=len(v))
             for m, v in by.items() if len(v) >= 3}, track)


# ---------------------------------------------------------------- report
def runs(seq):
    out = []
    for x in seq:
        if out and out[-1][0] == x: out[-1][1] += 1
        else: out.append([x, 1])
    return out


LAY3 = {"split_graphic_top_face_bottom": "split", "graphic_full_no_face": "graphic", "broll_full_no_face": "graphic", "face_full": "face", "face_full_with_card_overlay": "face"}


def report_one(p, d):
    w = f"{d}/work/{rid(p)}"; info = json.load(open(f"{w}/info.json")); m = dict(info); F = []; W = []
    if os.path.exists(f"{w}/loud.json"): m["loud"] = json.load(open(f"{w}/loud.json"))
    sc = json.load(open(f"{w}/scenes.json")); cuts = [t for t, s in zip(sc["t"], sc["score"]) if s > 0.3]; beats = [t for t, s in zip(sc["t"], sc["score"]) if s > 0.1]
    def merge(ts, gap=0.2):
        o = []
        for t in ts:
            if not o or t - o[-1] > gap: o.append(t)
        return o
    cuts, beats = merge(cuts), merge(beats)
    m["hard_cuts"] = len(cuts); m["visual_beats"] = len(beats)
    seg = [b - a for a, b in zip([0] + beats, beats + [info["dur"]])]
    m["beat_len_median"] = round(st.median(seg), 2) if seg else None; m["beat_len_p90"] = round(sorted(seg)[int(len(seg) * 0.9) - 1], 2) if len(seg) > 2 else None
    m["first_change_s"] = round(beats[0], 2) if beats else None
    if os.path.exists(f"{w}/words.json"):
        J = json.load(open(f"{w}/words.json")); W = J.get("words", [])
        if W:
            speech = W[-1]["end"] - W[0]["start"]; m["words"] = len(W); m["wps"] = round(len(W) / max(speech, 1e-6), 2)
            gaps = [b["start"] - a["end"] for a, b in zip(W, W[1:])]
            m["gap_p90"] = round(sorted(gaps)[int(len(gaps) * 0.9)], 2) if gaps else None; m["gaps_over_0_3"] = sum(1 for g in gaps if g > 0.3)
            m["speech_start"] = round(W[0]["start"], 2); m["tail_after_speech"] = round(info["dur"] - W[-1]["end"], 2)
            txt = J.get("text", ""); m["text"] = txt
            m["hook"] = re.split(r"(?<=[.!?])\s", txt.strip())[0] if txt else ""
    if os.path.exists(f"{w}/vision.json"):
        F = [f for f in json.load(open(f"{w}/vision.json"))["frames"] if "error" not in f]
        observations_path = f"{d}/analysis/geometry_observations.json"
        if os.path.isfile(observations_path):
            observations = json.load(open(observations_path))
            if observations.get("schema_version") != 1 or not isinstance(observations.get("measurements"), list):
                raise ValueError(f"invalid {observations_path}: expected schema_version 1 and measurements list")
            F = timeline.apply_observations(F, observations["measurements"], rid(p))
        n = max(len(F), 1); share = lambda k: {v: round(sum(1 for f in F if f[k] == v) / n, 2) for v in sorted({f[k] for f in F})}
        m["layout_share"] = share("layout"); m["face_share"] = share("face"); m["top_bg_share"] = share("top_bg"); m["graphic_share"] = share("graphic")
        m["caption_font_share"] = share("caption_font"); m["caption_color_share"] = share("caption_color")
        m["layout3_share"] = {k: round(sum(1 for f in F if LAY3.get(f["layout"]) == k) / n, 2) for k in ("split", "graphic", "face")}
        caps = [f["caption"].strip() for f in F if f["caption"].strip()]
        chunks = [c for c, _ in runs(caps)]; m["caption_words_median"] = st.median([len(c.split()) for c in chunks]) if chunks else None
        m["caption_frame_share"] = round(len(caps) / n, 2)
        ys = [f["caption_y"] for f in F if f["caption_y"] >= 0]; m["caption_y_median"] = round(st.median(ys), 2) if ys else None
        by = {}
        for f in F:
            if f["caption_y"] >= 0: by.setdefault(f["layout"], []).append(f["caption_y"])
        m["caption_y_by_layout"] = {k: round(st.median(v), 2) for k, v in by.items()}
        m["highlight_share"] = round(sum(1 for f in F if f["highlight"]) / n, 2)
        m["accent_counts"] = dict(collections.Counter(f["accent"].upper() for f in F if re.fullmatch(r"#[0-9A-Fa-f]{6}", f.get("accent", "").strip())))
        m["accents"] = [a for a, _ in sorted(m["accent_counts"].items(), key=lambda x: -x[1])[:4]]
        m["brands"] = sorted({b for f in F for b in f["brands"]})[:25]
        lay = runs([f["layout"] for f in F]); m["layout_runs"] = len(lay); m["layout_run_median_s"] = round(st.median([k / FPS_SAMPLE for _, k in lay]), 2)
        m["first_2s_layouts"] = [f["layout"] for f in F[:4]]; m["last_3s_layouts"] = [f["layout"] for f in F[-6:]]
        m["timeline"] = [f"{f['t']:>5.1f} {f['layout'][:12]:12} {f['face']:7} {f['graphic'][:16]:16} {f['caption_font'][:14]:14} {f['caption'][:28]}" for f in F]
    m["palette"] = palette_one(w)
    fr, face_track = framing_one(p, w, info)
    if fr: m["framing"] = fr
    if os.path.exists(f"{w}/audio_metrics.json"): m["audio"] = json.load(open(f"{w}/audio_metrics.json"))
    T = timeline.make_timeline(info, sc, F, W, m.get("audio"), face_track, f"{w}/frames", FPS_SAMPLE)
    json.dump(T, open(f"{w}/timeline.json", "w"), ensure_ascii=False, indent=1)
    shot_lengths = [s["duration_s"] for s in T["shots"]]
    m["shot_lengths"] = shot_lengths
    m["shot_len_median"] = timeline.median_or_none(shot_lengths)
    m["shot_len_p90"] = sorted(shot_lengths)[min(len(shot_lengths) - 1, math.floor(len(shot_lengths) * 0.9))] if shot_lengths else None
    m["pauses_over_0_3"] = len(T["pauses"])
    m["transition_counts"] = dict(collections.Counter(s["entry_transition"] for s in T["shots"][1:]))
    m["graphic_motion_counts"] = dict(collections.Counter(f.get("graphic_motion") for f in T["frames"] if f.get("graphic_motion") not in (None, "none")))
    for kind, prefix in (("caption", "caption"), ("title", "title"), ("ui_label", "title")):
        by_layout = collections.defaultdict(list)
        for frame in T["frames"]:
            if kind == "title" and frame.get("title_role") == "ui_label": continue
            if kind == "ui_label" and frame.get("title_role") != "ui_label": continue
            box = {key: frame.get(f"{prefix}_{key}") for key in ("x", "y", "w", "h")}
            if all(isinstance(value, (int, float)) and value >= 0 for value in box.values()):
                by_layout[LAY3.get(frame.get("layout"), "other")].append(box)
        m[f"{kind}_bounds_by_layout"] = {layout: {key: timeline.median_or_none([box[key] for box in boxes]) for key in ("x", "y", "w", "h")}
                                         for layout, boxes in by_layout.items()}
    json.dump(m, open(f"{w}/metrics.json", "w"), ensure_ascii=False, indent=1); return m


def aggregate(d, M):
    def vals(k, sub=None):
        v = [(x.get(k) if sub is None else (x.get(k) or {}).get(sub)) for x in M]; return [x for x in v if isinstance(x, (int, float))]
    def med(k, sub=None):
        v = vals(k, sub); return round(st.median(v), 2) if v else None
    def avg_share(k):
        keys = sorted({kk for x in M for kk in x.get(k, {})}); return {kk: round(sum(x.get(k, {}).get(kk, 0) for x in M) / len(M), 2) for kk in keys}
    L = [f"# Style metrics: {len(M)} reels in {os.path.basename(os.path.normpath(d))}", "", "| metric | median |", "|---|---|"]
    for k in ["dur", "wps", "gap_p90", "gaps_over_0_3", "speech_start", "tail_after_speech", "hard_cuts", "visual_beats", "beat_len_median", "shot_len_median", "shot_len_p90", "pauses_over_0_3", "first_change_s", "caption_words_median", "caption_y_median", "caption_frame_share", "highlight_share", "layout_runs", "layout_run_median_s"]:
        L.append(f"| {k} | {med(k)} |")
    L += [f"| loudness I (LUFS) | {med('loud', 'I')} |", f"| true peak | {med('loud', 'true_peak')} |"]
    if any("audio" in x for x in M):
        L += [f"| bg under speech rel. voice (dB) | {med('audio', 'bg_rel_voice_db')} |", f"| music bed share of seconds | {med('audio', 'music_bed_share')} |", f"| SFX onsets per 10 s | {med('audio', 'sfx_per_10s')} |", f"| hard cuts with SFX | {med('audio', 'cuts_with_sfx_share')} |"]
        L += [f"| SFX candidate peak rel. voice (dB) | {med('audio', 'sfx_peak_rel_voice_db')} |",
              f"| SFX candidate rise above bed (dB) | {med('audio', 'sfx_peak_above_bed_db')} |",
              f"| SFX candidate offset from cut (s) | {med('audio', 'sfx_cut_offset_s')} |"]
    for k in ["layout3_share", "layout_share", "face_share", "top_bg_share", "graphic_share", "caption_font_share", "caption_color_share"]:
        if any(k in x for x in M): L += ["", f"## {k} (mean over reels)", ""] + [f"- {kk}: {vv}" for kk, vv in sorted(avg_share(k).items(), key=lambda x: -x[1])]
    pal = collections.Counter(); sat = collections.Counter(); acc = collections.Counter()
    for x in M:
        for c, s in (x.get("palette") or {}).get("colors", []): pal[c] += s / len(M)
        for c, s in (x.get("palette") or {}).get("saturated", []): sat[c] += s / len(M)
        acc.update(x.get("accent_counts") or {a: 1 for a in x.get("accents", [])})
    acc = cluster_accents(acc)
    L += ["", "## Colours", "", "- dominant (share of frame area): " + ", ".join(f"{c} {s:.2f}" for c, s in pal.most_common(8)),
          "- saturated (accent candidates): " + (", ".join(f"{c} {s:.3f}" for c, s in sat.most_common(5)) or "none"),
          "- accents tagged by the vision model (similar colours merged, frames): " + (", ".join(f"{c} ×{k}" for c, k in acc.most_common(6)) or "none")]
    fr = collections.defaultdict(list)
    for x in M:
        for mode, v in (x.get("framing") or {}).items(): fr[mode].append(v)
    if fr:
        L += ["", "## Framing (face box in 1080x1920 px, median over reels)", ""] + [f"- {mode}: face width {round(st.median(v['w'] for v in vs))}, eyes y {round(st.median(v['eye'] for v in vs))}, centre x {round(st.median(v['cx'] for v in vs))} ({sum(v['n'] for v in vs)} frames)" for mode, vs in fr.items()]
    transitions = collections.Counter()
    for x in M: transitions.update(x.get("transition_counts") or {})
    if transitions: L += ["", "## Timed transition candidates", "", "- " + ", ".join(f"{kind}: {count}" for kind, count in transitions.most_common())]
    L += ["", "## Per reel", "", "| id | dur | wps | beats | beat med | first change | layouts S/G/F | hook opens with |", "|---|---|---|---|---|---|---|---|"]
    for x in M:
        l3 = x.get("layout3_share") or {}
        L.append(f"| {x['id']} | {x['dur']:.1f} | {x.get('wps')} | {x.get('visual_beats')} | {x.get('beat_len_median')} | {x.get('first_change_s')} | "
                 f"{l3.get('split', '-')}/{l3.get('graphic', '-')}/{l3.get('face', '-')} | {' '.join((x.get('hook') or '').split()[:6])}{'…' if len((x.get('hook') or '').split()) > 6 else ''} |")
    open(f"{d}/STYLE_METRICS.md", "w").write("\n".join(L) + "\n"); print("\n".join(L[:34]))
    style = make_style(d, M, med, vals, fr, acc, sat)
    style_path = f"{d}/style.json"
    if os.path.isfile(style_path):
        # Editors tune these choices after measurement; a repeat report must not
        # erase that creative decision or replace it with neutral fallbacks.
        previous = json.load(open(style_path))
        style["plan_defaults"].update(previous.get("plan_defaults") or {})
    json.dump(style, open(style_path, "w"), indent=1)
    os.makedirs(f"{d}/analysis", exist_ok=True)
    reference_timeline = {"schema_version": 1, "frame_sample_fps": FPS_SAMPLE,
                          "reels": [json.load(open(f"{d}/work/{x['id']}/timeline.json")) for x in M]}
    json.dump(reference_timeline, open(f"{d}/analysis/reference_timeline.json", "w"), ensure_ascii=False, indent=1)
    if not os.path.exists(f"{d}/style-bible.md"): open(f"{d}/style-bible.draft.md", "w").write(bible_draft(d, style, M))
    print(f"→ {d}/STYLE_METRICS.md, {d}/style.json, {d}/analysis/reference_timeline.json" + ("" if os.path.exists(f"{d}/style-bible.md") else f", {d}/style-bible.draft.md"))


def cluster_accents(acc):
    """merge near-identical accent hexes (the vision model reports the same colour a few units apart) and drop greys"""
    import colorsys
    rgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    out = collections.Counter(); heads = []
    for c, k in acc.most_common():
        r, g, b = rgb(c); h_, s_, v_ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s_ < 0.3 or v_ < 0.25: continue
        head = next((hd for hd in heads if sum((x - y) ** 2 for x, y in zip(rgb(hd), (r, g, b))) ** 0.5 < 48), None)
        if head: out[head] += k
        else: heads.append(c); out[c] += k
    return out


def make_style(d, M, med, vals, fr, acc, sat):
    """machine targets for the engine; ranges are the spread over the reels, widened a little when there are only a few reels"""
    few = len(M) < 6
    def rng(v, pad, lo_min=0.0, hi_max=None):
        if not v: return None
        lo, hi = min(v) - (pad if few else 0), max(v) + (pad if few else 0)
        return dict(lo=round(max(lo_min, lo), 2), hi=round(min(hi_max, hi) if hi_max is not None else hi, 2), median=round(st.median(v), 2))
    s = dict(name=os.path.basename(os.path.normpath(d)), description=f"Measured on {len(M)} reels in {os.path.basename(os.path.normpath(d))} with analyze_reference.py.", reels=len(M))
    pace = {}
    if vals("wps"): pace["wps"] = med("wps")
    if vals("gap_p90"): pace["gap_p90"] = med("gap_p90")
    pace["duration"] = [math.floor(min(vals("dur"))), math.ceil(max(vals("dur")))]
    fc = rng(vals("first_change_s"), 0.6)
    if fc: pace["first_change"] = fc
    if vals("beat_len_median"): pace["beat_len_median"] = med("beat_len_median")
    if vals("layout_run_median_s"): pace["layout_run_median"] = med("layout_run_median_s")
    s["pace"] = pace
    shot_duration = rng(vals("shot_len_median"), 0.25)
    transitions = collections.Counter()
    for reel in M: transitions.update(reel.get("transition_counts") or {})
    s["shots"] = {}
    if shot_duration: s["shots"]["duration_s"] = shot_duration
    if transitions:
        total = sum(transitions.values())
        s["shots"]["transition_share"] = {kind: round(count / total, 3) for kind, count in transitions.items()}
        s["shots"]["transition_evidence"] = "agent_frame_tag_or_scene_score_candidate"
    if any("layout3_share" in x for x in M):
        s["layouts"] = {k: rng([x["layout3_share"][k] for x in M if "layout3_share" in x], 0.1, 0.0, 1.0) for k in ("split", "graphic", "face")}
        first = collections.Counter(LAY3.get((x.get("first_2s_layouts") or ["?"])[0]) for x in M).most_common(1)[0][0]
        last = collections.Counter(LAY3.get((x.get("last_3s_layouts") or ["?"])[-1]) for x in M).most_common(1)[0][0]
        s["open_layout"] = first; s["close_layout"] = last
        s["captions"] = dict(words_per_chunk=med("caption_words_median") or 2, always_on=(med("caption_frame_share") or 0) > 0.35)   # the tagger misses ~half of the captions
    def bounds_by_layout(key):
        layouts = {layout for reel in M for layout in reel.get(key, {})}
        return {layout: {axis: timeline.median_or_none([reel[key][layout][axis] for reel in M if layout in reel.get(key, {})])
                         for axis in ("x", "y", "w", "h")} for layout in sorted(layouts)}
    caption_bounds = bounds_by_layout("caption_bounds_by_layout")
    if caption_bounds:
        s.setdefault("captions", {})["bounds_by_layout"] = caption_bounds
        s["captions"]["bounds_source"] = "agent_frame_tags_normalized"
    title_bounds = bounds_by_layout("title_bounds_by_layout")
    ui_label_bounds = bounds_by_layout("ui_label_bounds_by_layout")
    motion = collections.Counter()
    for reel in M: motion.update(reel.get("graphic_motion_counts") or {})
    if title_bounds or ui_label_bounds or motion:
        s["graphics"] = {}
        if title_bounds:
            s["graphics"]["title_bounds_by_layout"] = title_bounds
            s["graphics"]["title_bounds_source"] = "agent_frame_tags_normalized"
        if ui_label_bounds: s["graphics"]["ui_label_bounds_by_layout"] = ui_label_bounds
        if motion:
            total_motion = sum(motion.values())
            s["graphics"]["motion_share"] = {kind: round(count / total_motion, 3) for kind, count in motion.items()}
            s["graphics"]["motion_source"] = "agent_frame_tags"
    snd = {}
    if vals("loud", "I"): snd.update(lufs=med("loud", "I"), true_peak=med("loud", "true_peak"))
    if any("audio" in x for x in M):
        rel = med("audio", "bg_rel_voice_db")
        if rel is not None: snd.update(music_rel_voice_db=rel, music_mix_rel_db=round(rel - 2, 1))
        snd["music_share"] = med("audio", "music_bed_share")
        sf = rng(vals("audio", "sfx_per_10s"), 1.0)
        if sf: snd["sfx_per_10s"] = sf
        snd["cuts_with_sfx"] = med("audio", "cuts_with_sfx_share")
        for field in ("sfx_peak_rel_voice_db", "sfx_peak_above_bed_db", "sfx_cut_offset_s"):
            spread = rng(vals("audio", field), 3.0 if field.endswith("db") else 0.08, -100 if field.endswith("db") else -0.5)
            if spread: snd[field] = spread
        if any(field in snd for field in ("sfx_peak_rel_voice_db", "sfx_peak_above_bed_db", "sfx_cut_offset_s")):
            snd["sfx_measurement"] = "separated_background_transient_candidates"
    s["sound"] = snd
    if fr: s["framing"] = {mode: dict(w=round(st.median(v["w"] for v in vs)), eye=round(st.median(v["eye"] for v in vs)), cx=round(st.median(v["cx"] for v in vs))) for mode, vs in fr.items()}
    accent = (acc.most_common(1) or sat.most_common(1) or [(None, 0)])[0][0]   # vision-tagged accent cluster first, else the most frequent saturated colour
    brands = sorted({name for reel in M for name in reel.get("brands", [])})
    if brands: s["brand_lexicon"] = brands
    s["timeline_file"] = "analysis/reference_timeline.json"
    s["plan_defaults"] = dict(era="2026", music="ambient_tech_90", trans="auto", **({"accent": accent} if accent and re.fullmatch(r"#[0-9A-Fa-f]{6}", accent) else {}))
    return s


def bible_draft(d, s, M):
    name = s["name"]; L3 = s.get("layouts") or {}; P = s.get("pace", {}); S = s.get("sound", {})
    f = lambda k: (f"{L3[k]['median']} (range {L3[k]['lo']}–{L3[k]['hi']})" if L3.get(k) else "not measured")
    return f"""# Style bible: {name} (DRAFT — finish it, then save as style-bible.md)

Measured on {len(M)} reels with scripts/reference/analyze_reference.py. Numbers below are medians from STYLE_METRICS.md and
style.json. Every "TODO" is yours to write from the contact sheets (work/<id>/sheet.jpg), full-size frames and the beat sheets
(references/beat-sheet-prompt.md). Keep this section order (the skeleton is styles/_template/style-bible.md): the planner
reads this file before every plan in this style.

## 1. Passport
| metric | median |
|---|---|
| duration | {P.get('duration')} s (min–max) |
| words per second | {P.get('wps')} |
| first visual change | {(P.get('first_change') or {}).get('median')} s |
| beat length (visual change every) | {P.get('beat_len_median')} s |
| layout run | {P.get('layout_run_median')} s |
| loudness | {S.get('lufs')} LUFS, true peak {S.get('true_peak')} |
| music under the voice | {str(S['music_rel_voice_db']) + ' dB' if 'music_rel_voice_db' in S else 'not measured (needs the stems step)'} |
| SFX per 10 s | {(S.get('sfx_per_10s') or {}).get('median', 'not measured (needs the stems step)')} |

## 2. Layouts
- split (graphic top, speaker bottom): {f('split')}
- full-frame graphic / b-roll: {f('graphic')}
- face full-frame: {f('face')}
- opens on: {s.get('open_layout')}; ends on: {s.get('close_layout')}
- TODO: the exact shape of the split (arch with the head popping out = meta.era "2026", or a straight seam = meta.era "2025"),
  what each layout is used for, the order rules (never two faces in a row?).

## 3. Cuts and transitions
- TODO: hard cuts or soft moves (meta.trans "cut" vs "auto"), where a cut sits relative to the word, special moves (flash, light leak, zoom-in start).

## 4. Captions
- words per chunk: {(s.get('captions') or {}).get('words_per_chunk')}; captions on screen most of the time: {(s.get('captions') or {}).get('always_on')}
- TODO: font per layout (see caption_font_share in STYLE_METRICS.md), colour, height, which words get the accent, CTA keyword look.

## 5. Colour
- accent candidate: {s.get('plan_defaults', {}).get('accent', 'TODO')} (see the Colours section of STYLE_METRICS.md)
- TODO: backgrounds and what each one means (dark for code, white for results…), where the accent is allowed.

## 6. Fonts
- TODO: the closest bundled fonts (Inter, Playfair Display, Noto Serif Display, Press Start 2P, Pixelify Sans, JetBrains Mono,
  Unbounded, Instrument Serif) for each caption and title style you see.

## 7. Motion
- TODO: entrances (blur, pop, slide), how long anything stays still, how logos/numbers/UIs are timed against the words.

## 8. Sound
- TODO from the stems numbers (audio_metrics: music bed, SFX per 10 s, cuts with a sound) and sfx_probe.py: opening sound,
  what gets a whoosh/pop/click, music level, density. Nobody listened to the music: name its genre only if the user tells you.
  Pick meta.profile "measured" if the reference is quiet and sparse, "bold" if its effects are clearly audible.

## 9. Hook (first 3 s)
- TODO: what is on screen at frame 0, when the first change happens, the hook formulas (as templates, not quotes).

## 10. Structure and CTA
- TODO: the skeletons (single tool / list / news …), how the CTA looks and how long it holds.

## 11. Rules for the planner
1. TODO: 10–20 numbered, concrete rules with numbers, most important first.
"""


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2 or a[0] in ("-h", "--help"): raise SystemExit(__doc__)
    d = os.path.abspath(os.path.expanduser(a[0])); step = a[1]
    lang = next((x.split("=", 1)[1] for x in a if x.startswith("--lang=")), a[a.index("--lang") + 1] if "--lang" in a else "en")
    vocab = VOCAB + (", " + a[a.index("--vocab") + 1] if "--vocab" in a else "")
    P = reels(d); os.makedirs(f"{d}/work", exist_ok=True)
    if not P: raise SystemExit(f"no reels in {d}/raw/*.mp4 — run fetch_reels.py first")
    if step in ("words", "all"): env_key("ELEVENLABS_API_KEY")
    if step in ("prep", "all"):
        with cf.ThreadPoolExecutor(6) as ex: print("prep", list(ex.map(lambda p: prep_one(p, d), P)), flush=True)
    if step in ("words", "all"):
        with cf.ThreadPoolExecutor(4) as ex: print("words", list(ex.map(lambda p: words_one(p, d, lang, vocab), P)), flush=True)
    if step in ("stems", "all"):
        py = demucs_python()
        if py:
            for p in P: print("stems", stems_one(p, d, py), flush=True)
        else: print("stems skipped: Demucs is not installed (~/.local/share/muratovai-montage/venv/bin/python -m pip install demucs, "
                    "or DEMUCS_PY=<a python with demucs>). Music level and SFX density stay unmeasured.", flush=True)
    if step in ("vision", "all"):
        for p in P: print("vision", vision_one(p, d), flush=True)
    if step == "vision-import":
        for p in P: print("vision-import", vision_import_one(p, d), flush=True)
    if step in ("report", "all"):
        untagged = [rid(p) for p in P if not os.path.exists(f"{d}/work/{rid(p)}/vision.json")]
        if step == "all" and untagged:
            raise SystemExit(f"next: tag the frames of {', '.join(untagged)} (work/<id>/vision_task.md), run vision-import, then report")
        if untagged: print(f"WARNING: no vision.json for {', '.join(untagged)}: layouts, captions and accents miss these reels", flush=True)
        aggregate(d, [report_one(p, d) for p in P])
