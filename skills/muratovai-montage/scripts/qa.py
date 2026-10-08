#!/usr/bin/env python3
"""QA of a rendered reel against its style profile and the delivered MP4.

  python3 qa.py <project> [out/<slug>.mp4]
Checks the whole file for decode errors, stream/duration integrity and loudness, then writes
out/qa_sheet.jpg (one frame per second) for a human to inspect. Exits 1 on hard failures.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import hashlib, json, math, os, re, statistics as st, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import era_view, load_style  # noqa: E402


class MediaQAError(Exception):
    """A delivered-file problem that should be printed without a traceback."""


def sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True)


def checked(label, *a):
    try:
        result = sh(*a)
    except OSError as exc:
        raise MediaQAError(f"{label}: could not start {a[0]} ({exc})") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-1000:]
        raise MediaQAError(f"{label}: {detail or f'{a[0]} exited {result.returncode}'}")
    return result


def duration_tolerance(expected):
    """Allow container/audio rounding, but not a missing or extra section of the edit."""
    return max(0.15, min(0.5, expected * 0.01))


def check_duration(label, raw, expected):
    try:
        actual = float(raw)
    except (TypeError, ValueError):
        raise MediaQAError(f"{label}: duration unavailable") from None
    if not math.isfinite(actual) or actual <= 0:
        raise MediaQAError(f"{label}: invalid duration {raw!r}")
    tolerance = duration_tolerance(expected)
    if abs(actual - expected) > tolerance:
        raise MediaQAError(f"{label}: {actual:.3f}s, timeline {expected:.3f}s (allowed ±{tolerance:.3f}s)")
    return actual


def inspect_media(video, expected):
    """Probe stream metadata, then decode both streams from start to finish while measuring audio."""
    if not os.path.isfile(video) or os.path.getsize(video) == 0:
        raise MediaQAError(f"delivered MP4 missing or empty: {video}")
    probe = checked("ffprobe failed", "ffprobe", "-v", "error", "-show_entries",
                    "format=duration:stream=codec_type,codec_name,start_time,duration,width,height,nb_frames", "-of", "json", video)
    try:
        info = json.loads(probe.stdout)
    except (TypeError, ValueError) as exc:
        raise MediaQAError(f"ffprobe returned invalid JSON: {exc}") from exc
    if not isinstance(info, dict) or not isinstance(info.get("streams"), list):
        raise MediaQAError("ffprobe returned no stream list")
    streams = info["streams"]
    if not all(isinstance(s, dict) for s in streams):
        raise MediaQAError("ffprobe returned invalid stream metadata")
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        raise MediaQAError(f"expected one video and one audio stream; found {len(videos)} video, {len(audios)} audio")
    for label, stream in (("video", videos[0]), ("audio", audios[0])):
        if not stream.get("codec_name"):
            raise MediaQAError(f"{label} stream has no recognized codec")
        if stream.get("duration") is not None:
            check_duration(f"{label} stream", stream["duration"], expected)
    # Stream durations alone do not catch a late audio start followed by a late audio end.
    try:
        v_start = float(videos[0].get("start_time", 0))
        a_start = float(audios[0].get("start_time", 0))
        v_end = v_start + float(videos[0]["duration"])
        a_end = a_start + float(audios[0]["duration"])
    except (TypeError, ValueError, KeyError) as exc:
        raise MediaQAError(f"A/V sync: missing or invalid stream timestamps ({exc})") from exc
    if not all(math.isfinite(x) for x in (v_start, a_start, v_end, a_end)):
        raise MediaQAError("A/V sync: non-finite stream timestamps")
    if abs(a_start - v_start) > 0.12 or abs(a_end - v_end) > 0.15:
        raise MediaQAError(f"A/V sync: video {v_start:.3f}–{v_end:.3f}s, audio {a_start:.3f}–{a_end:.3f}s")
    try:
        width, height = int(videos[0].get("width") or 0), int(videos[0].get("height") or 0)
    except (TypeError, ValueError):
        width, height = 0, 0
    if width <= 0 or height <= 0:
        raise MediaQAError("video stream has invalid frame dimensions")
    check_duration("MP4 container", (info.get("format") or {}).get("duration"), expected)

    decoded = checked("full MP4 decode failed", "ffmpeg", "-nostdin", "-hide_banner", "-v", "info",
                      "-xerror", "-err_detect", "explode", "-i", video, "-map", "0:v:0", "-map", "0:a:0",
                      "-af", "ebur128=peak=true", "-progress", "pipe:1", "-f", "null", "-")
    if not re.search(r"^progress=end$", decoded.stdout, re.MULTILINE):
        raise MediaQAError("full MP4 decode did not report completion")
    frames = re.findall(r"^frame=(\d+)$", decoded.stdout, re.MULTILINE)
    if not frames or int(frames[-1]) <= 0:
        raise MediaQAError("full MP4 decode produced no video frames")
    declared_frames = videos[0].get("nb_frames")
    if declared_frames and str(declared_frames).isdigit() and int(frames[-1]) + 1 < int(declared_frames):
        raise MediaQAError(f"full MP4 decode produced {frames[-1]} of {declared_frames} declared video frames")
    times = re.findall(r"^out_time=(\d+):(\d+):(\d+(?:\.\d+)?)$", decoded.stdout, re.MULTILINE)
    if not times:
        raise MediaQAError("full MP4 decode did not report its final timestamp")
    h, m, s = times[-1]
    check_duration("decoded media", int(h) * 3600 + int(m) * 60 + float(s), expected)
    loudness = re.search(r"Integrated loudness:\s*I:\s*(\S+) LUFS", decoded.stderr)
    true_peak = re.search(r"True peak:\s*Peak:\s*(\S+) dBFS", decoded.stderr)
    if not loudness or not true_peak:
        raise MediaQAError("loudness or true-peak summary missing after full decode")
    try: I, tp = float(loudness.group(1)), float(true_peak.group(1))
    except ValueError as exc: raise MediaQAError(f"invalid loudness or true-peak summary: {exc}") from exc
    if not math.isfinite(I) or not math.isfinite(tp):
        raise MediaQAError("audio is silent or loudness/true peak is not measurable")
    return I, tp, (width, height)


def visual_faults(video, duration):
    """Detect sustained black/frozen picture in the delivered MP4, with timestamps."""
    result = checked("visual scan failed", "ffmpeg", "-nostdin", "-hide_banner", "-v", "info",
                     "-i", video, "-map", "0:v:0", "-an", "-vf",
                     "blackdetect=d=0.20:pix_th=0.06:pic_th=0.98,freezedetect=n=-60dB:d=1.0",
                     "-f", "null", "-")
    black = []
    for start, end, length in re.findall(
            r"black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)", result.stderr):
        a, b, d = float(start), float(end), float(length)
        if d >= 0.20: black.append((a, min(b, duration)))
    frozen, active = [], None
    for line in result.stderr.splitlines():
        start = re.search(r"freeze_start:\s*([\d.]+)", line)
        end = re.search(r"freeze_end:\s*([\d.]+)", line)
        if start: active = float(start.group(1))
        if end and active is not None:
            frozen.append((active, min(float(end.group(1)), duration)))
            active = None
    if active is not None: frozen.append((active, duration))
    return black, [(a, b) for a, b in frozen if b - a >= 1.0]


def classify_visual_faults(timeline, black, frozen):
    """Only an explicit, justified per-beat intent may defer a visual fault to review."""
    fails, warns = [], []
    beats = timeline["beats"]
    for kind, intervals in (("black", black), ("frozen", frozen)):
        flag = "dark_ok" if kind == "black" else "static_ok"
        for a, b in intervals:
            affected = [beat for beat in beats if min(b, float(beat["t1"])) - max(a, float(beat["t0"])) > .01]
            covered = sum(max(0.0, min(b, float(beat["t1"])) - max(a, float(beat["t0"]))) for beat in affected)
            deliberate = (covered >= b - a - .04 and affected and all(
                isinstance(beat.get("visual_intent"), dict)
                and beat["visual_intent"].get(flag) is True
                and len(str(beat["visual_intent"].get("reason", "")).strip()) >= 12
                for beat in affected))
            finding = f"{kind} picture {a:.2f}–{b:.2f}s ({b - a:.2f}s)"
            if deliberate:
                reasons = "; ".join(dict.fromkeys(beat["visual_intent"]["reason"] for beat in affected))
                warns.append(f"review required: {finding}; intentional per-beat reason: {reasons}")
            elif kind == "frozen" and b - a < 2.0:
                warns.append(f"review required: {finding}; no explicit static intent")
            else:
                fails.append(finding)
    return fails, warns


def fingerprint(path):
    """Hash a stable file; compare again after QA to catch a concurrent rewrite."""
    try:
        before = os.stat(path)
        digest = hashlib.sha256()
        with open(path, "rb") as media:
            for block in iter(lambda: media.read(1024 * 1024), b""):
                digest.update(block)
        after = os.stat(path)
    except OSError as exc:
        raise MediaQAError(f"could not fingerprint {path}: {exc}") from exc
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise MediaQAError(f"media changed while hashing: {path}")
    return {"sha256": digest.hexdigest(), "bytes": after.st_size, "mtime_ns": after.st_mtime_ns}


def build_provenance(P, video_size):
    """Expected hashes and dimensions for the caption manifest of the current build."""
    idx_path = os.path.join(P, "hf", "index.html")
    try:
        with open(idx_path, encoding="utf-8") as file: html = file.read()
    except OSError as exc:
        raise MediaQAError(f"caption safety: could not read HyperFrames composition ({exc})") from exc
    size = re.search(r'data-width="(\d+)"\s+data-height="(\d+)"', html)
    if not size:
        raise MediaQAError("caption safety: HyperFrames composition has no frame dimensions")
    return {
        "plan_sha256": fingerprint(os.path.join(P, "plan.json"))["sha256"],
        "hf_index_sha256": fingerprint(idx_path)["sha256"],
        "words_sha256": fingerprint(os.path.join(P, "work", "words.json"))["sha256"],
        "video_width": video_size[0], "video_height": video_size[1],
        "canvas_width": int(size.group(1)), "canvas_height": int(size.group(2)),
    }


def finish_audit(P, master_fp, light_fp, used):
    """Verify finish.py's hashes so SFX measurements belong to this exact delivery."""
    path = os.path.join(P, "work", "sfx_audit.json")
    try:
        with open(path, encoding="utf-8") as file: audit = json.load(file)
    except (OSError, ValueError) as exc:
        raise MediaQAError(f"finish audit missing or invalid: {exc}") from exc
    if not isinstance(audit, dict):
        raise MediaQAError("finish audit is not an object")
    picture_name = audit.get("picture_path") or "out/picture.mp4"
    picture_path = picture_name if os.path.isabs(picture_name) else os.path.join(P, picture_name)
    checks = {
        "master_sha256": master_fp["sha256"], "light_sha256": light_fp["sha256"],
        "picture_sha256": fingerprint(picture_path)["sha256"],
        "sfx_used_sha256": fingerprint(os.path.join(P, "work", "sfx_used.json"))["sha256"],
        "hf_index_sha256": fingerprint(os.path.join(P, "hf", "index.html"))["sha256"],
        "cue_count": len(used),
    }
    mismatched = [field for field, expected in checks.items() if audit.get(field) != expected]
    if mismatched:
        raise MediaQAError("finish audit does not match current artifacts: " + ", ".join(mismatched))
    try: window = float(audit["isolated_probe_window_s"])
    except (KeyError, TypeError, ValueError): window = 0
    if not 0.055 <= window <= 0.065:
        raise MediaQAError("finish audit has no valid isolated SFX probe window")
    hf_time = os.stat(os.path.join(P, "hf", "index.html")).st_mtime_ns
    picture_time = os.stat(picture_path).st_mtime_ns
    if picture_time < hf_time or master_fp["mtime_ns"] < picture_time or light_fp["mtime_ns"] < master_fp["mtime_ns"]:
        raise MediaQAError("finish audit: render, master and light are older than their inputs")
    return audit


def speech_sync(video, voice_path, words, duration):
    """Cross-correlate actual speech waveform near the start and end against delivered audio."""
    try: import numpy as np
    except ImportError as exc: raise MediaQAError("speech sync: numpy is missing") from exc
    def pcm(path):
        try:
            result = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-i", path,
                                     "-map", "0:a:0", "-af", "highpass=f=130,lowpass=f=900",
                                     "-ar", "2000", "-ac", "1", "-f", "f32le", "-"], capture_output=True)
        except OSError as exc:
            raise MediaQAError(f"speech sync: decoder unavailable ({exc})") from exc
        if result.returncode:
            raise MediaQAError(f"speech sync: could not decode {os.path.basename(path)}: {result.stderr[-300:].decode(errors='replace')}")
        return np.frombuffer(result.stdout, dtype="<f4")
    voice, mix = pcm(voice_path), pcm(video)
    if len(voice) < 1000 or len(mix) < 1000:
        raise MediaQAError("speech sync: audio is too short to compare")
    try:
        speech_start, speech_end = float(words[0]["start"]), float(words[-1]["end"])
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise MediaQAError(f"speech sync: invalid word timings ({exc})") from exc
    if not (0 <= speech_start < speech_end <= duration + .1):
        raise MediaQAError("speech sync: word timings fall outside the rendered reel")
    margin = min(.4, duration * .18)
    window = min(2.5, duration - 2 * margin)
    if window < .5: raise MediaQAError("speech sync: too little active audio to compare")
    first = max(margin, min(speech_start, duration - margin - window))
    last = max(margin, min(speech_end - window, duration - margin - window))
    starts = [first] if abs(last - first) < .5 else [first, last]
    max_lag = min(.4, margin * .9)
    measurements = []
    for at in starts:
        i0, i1 = round(at * 2000), round((at + window) * 2000)
        source = voice[i0:i1].astype(np.float64)
        source -= source.mean()
        source_norm = float(np.linalg.norm(source))
        if source_norm < .01:
            raise MediaQAError(f"speech sync: no active voice near {at:.2f}s")
        scores = []
        for lag in range(-round(max_lag * 2000), round(max_lag * 2000) + 1):
            a, b = i0 + lag, i1 + lag
            if a < 0 or b > len(mix): continue
            target = mix[a:b].astype(np.float64)
            target -= target.mean()
            target_norm = float(np.linalg.norm(target))
            if target_norm > .01:
                scores.append((float(np.dot(source, target) / (source_norm * target_norm)), lag))
        if not scores:
            raise MediaQAError(f"speech sync: no comparable delivered audio near {at:.2f}s")
        best = max(score for score, _ in scores)
        # A periodic source can have several equal peaks. Prefer the closest to zero.
        correlation, lag = min(((score, offset) for score, offset in scores if score >= best - .002),
                               key=lambda item: abs(item[1]))
        measurements.append({"window_start_s": round(at, 3), "window_end_s": round(at + window, 3),
                             "offset_s": round(lag / 2000, 4), "correlation": round(correlation, 3)})
    return measurements


def caption_safety(manifest, duration, provenance=None, words=None):
    """Check caption timing/containers; provenance binds metadata to this build, not visible glyphs."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("captions"), list):
        raise MediaQAError("caption safety: invalid caption_qa.json")
    try:
        width, height = float(manifest["width"]), float(manifest["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MediaQAError(f"caption safety: missing frame size ({exc})") from exc
    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
        raise MediaQAError("caption safety: invalid frame size")
    errors = []
    if provenance is not None:
        for field in ("plan_sha256", "hf_index_sha256", "words_sha256", "video_width", "video_height"):
            if manifest.get(field) != provenance[field]:
                errors.append(f"caption safety: {field} does not match current plan/render inputs")
        if width != provenance["canvas_width"] or height != provenance["canvas_height"]:
            errors.append("caption safety: canvas dimensions do not match current HyperFrames composition")
    # 5% sides, 10% top and 17% bottom reserve app controls and the account handle.
    left, top, right, bottom = .05 * width, .10 * height, .95 * width, .83 * height
    for caption in manifest["captions"]:
        if not isinstance(caption, dict):
            errors.append("caption safety: invalid caption entry")
            continue
        label = str(caption.get("id", "?"))
        try:
            t0, t1 = float(caption["t0"]), float(caption["t1"])
            x0, y0, x1, y1 = map(float, caption["box_px"])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"caption {label}: invalid timing or box ({exc})")
            continue
        if not all(math.isfinite(v) for v in (t0, t1, x0, y0, x1, y1)) or not (0 <= t0 < t1 <= duration + .05):
            errors.append(f"caption {label}: invalid timing or box")
        elif x0 < left - 1 or y0 < top - 1 or x1 > right + 1 or y1 > bottom + 1 or x0 >= x1 or y0 >= y1:
            errors.append(f"caption {label}@{t0:.2f}s outside safe zone: box {x0:.0f},{y0:.0f}–{x1:.0f},{y1:.0f}; safe {left:.0f},{top:.0f}–{right:.0f},{bottom:.0f}")
        starts = caption.get("starts")
        ends = caption.get("word_ends")
        if starts is not None or ends is not None or provenance is not None:
            try: word_starts = [float(x) for x in starts]
            except (TypeError, ValueError): word_starts = []
            try: word_ends = [float(x) for x in ends]
            except (TypeError, ValueError): word_ends = []
            if (not word_starts or len(word_starts) != len(word_ends)
                    or not all(math.isfinite(x) for x in word_starts + word_ends)
                    or any(end <= start for start, end in zip(word_starts, word_ends))
                    or any(b < a for a, b in zip(word_starts, word_starts[1:]))):
                errors.append(f"caption {label}: invalid word timing metadata")
            elif t0 < word_starts[0] - .15 or t0 > word_starts[0] + .08 or t1 < word_ends[-1] - .08:
                errors.append(f"caption {label}@{t0:.2f}s is out of sync with words {word_starts[0]:.2f}–{word_ends[-1]:.2f}s")
            elif words is not None and any(not any(
                    abs(float(word["start"]) - start) <= .02 and abs(float(word["end"]) - end) <= .02
                    for word in words) for start, end in zip(word_starts, word_ends)):
                errors.append(f"caption {label}: word timings differ from work/words.json")
    return errors


def sfx_audibility(used, duration, measured, project=None, planned=None):
    """Check each intended foreground cue against its masking bed.

    A measured style may call for a quieter cue, but an inaudible cue still
    needs an editor's review before its MP4 can be published.
    """
    if not isinstance(used, list):
        return ["SFX manifest is not a list"], []
    beds = {"typing", "count"}
    fails, warns = [], []
    for index, cue in enumerate(used):
        if not isinstance(cue, dict):
            fails.append("SFX manifest has an invalid cue")
            continue
        kind = str(cue.get("kind", "?"))
        try: at = float(cue["t_peak"])
        except (KeyError, TypeError, ValueError):
            fails.append(f"{kind} SFX has no peak timestamp")
            continue
        if not math.isfinite(at) or at < -0.05 or at > duration + .05:
            fails.append(f"{kind} SFX peak {at:.2f}s is outside the finished reel")
        planned_foreground = any(
            isinstance(event, dict) and event.get("kind") == kind
            and abs(float(event.get("t", -100)) - float(cue.get("t", at))) <= .15
            and (event.get("foreground") is True or event.get("hero") is True
                 or event.get("dur") is not None or event.get("db") is not None)
            for event in (planned or [])
        ) if kind in beds else False
        if kind in beds and cue.get("foreground") is not True and not planned_foreground:
            if cue.get("audibility_status") not in (None, "bed_not_scored"):
                fails.append(f"{kind}@{at:.2f}s unscored bed has inconsistent audibility status")
            continue
        try: snr = float(cue["isolated_best_band_snr_db"])
        except (KeyError, TypeError, ValueError):
            fails.append(f"{kind}@{at:.2f}s has no isolated cue audibility")
            continue
        if not math.isfinite(snr):
            fails.append(f"{kind}@{at:.2f}s has invalid isolated cue audibility")
        else:
            expected_status = "review_required" if snr < 0 else "audible"
            if "audibility_status" in cue and cue["audibility_status"] != expected_status:
                fails.append(f"{kind}@{at:.2f}s audibility status disagrees with isolated probe")
            if snr < 0:
                finding = f"{kind}@{at:.2f}s masked in isolated stem ({snr:.1f} dB best-band SNR)"
                (warns if measured else fails).append(
                    f"review required: {finding}" if measured else finding)
        if project is not None:
            probe = os.path.join(project, "work", "_mix", f"probe_{index}.wav")
            try: expected_hash = cue["isolated_probe_sha256"]
            except KeyError: expected_hash = None
            try: actual_hash = fingerprint(probe)["sha256"]
            except MediaQAError: actual_hash = None
            if not expected_hash or expected_hash != actual_hash:
                fails.append(f"{kind}@{at:.2f}s isolated probe missing or changed")
            try: audit_t0 = float(cue["audit_t0"])
            except (KeyError, TypeError, ValueError): audit_t0 = float("nan")
            if not math.isfinite(audit_t0) or abs(audit_t0 - max(0, at - .03)) > .04:
                fails.append(f"{kind}@{at:.2f}s isolated probe timestamp invalid")
    return fails, warns


def make_sheet(P, video, duration):
    out = os.path.join(P, "out", "qa_sheet.jpg")
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if os.path.exists(out): os.remove(out)
        fd, pending = tempfile.mkstemp(prefix=".qa_sheet-", suffix=".jpg", dir=os.path.dirname(out))
        os.close(fd)
    except OSError as exc:
        raise MediaQAError(f"contact sheet failed: could not prepare output ({exc})") from exc
    try:
        rows = max(1, math.ceil((duration + duration_tolerance(duration)) / 9))
        checked("contact sheet failed", "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video,
                "-vf", f"fps=1,scale=180:-1,tile=9x{rows}", "-frames:v", "1", "-q:v", "4", pending)
        if os.path.getsize(pending) == 0:
            raise MediaQAError("contact sheet failed: ffmpeg produced no image")
        os.replace(pending, out)
    except (MediaQAError, OSError) as exc:
        if os.path.exists(pending): os.remove(pending)
        if isinstance(exc, MediaQAError): raise
        raise MediaQAError(f"contact sheet failed: {exc}") from exc
    return out


def review_points(timeline, captions=()):
    """Frames for editorial inspection: opening, both sides of every cut, beat and caption centres."""
    duration = float(timeline["duration"])
    marks = [(0.07, "open 0.07s"), (0.5, "open 0.50s"), (1.0, "open 1.00s"),
             (2.0, "open 2.00s"), (2.9, "open 2.90s")]
    beats = timeline["beats"]
    for i, beat in enumerate(beats):
        a, b = float(beat["t0"]), float(beat["t1"])
        marks.append(((a + b) / 2, f"beat {i} middle {((a + b) / 2):.2f}s"))
        if i:
            marks.extend(((a - .067, f"cut {i} before {a - .067:.2f}s"),
                          (a + .067, f"cut {i} after {a + .067:.2f}s")))
    for caption in captions:
        if isinstance(caption, dict) and "t0" in caption and "t1" in caption:
            try:
                at = (float(caption["t0"]) + float(caption["t1"])) / 2
                marks.append((at, f"caption {caption.get('id', '?')} {at:.2f}s"))
            except (TypeError, ValueError): pass
    by_frame = {}
    last = max(0, math.floor(duration * 30) - 1)
    for at, label in marks:
        if math.isfinite(at) and 0 <= at < duration:
            frame = max(0, min(last, round(at * 30)))
            by_frame.setdefault(frame, (frame / 30, label))
    return [by_frame[n] for n in sorted(by_frame)]


def make_review_sheet(P, video, points):
    """Extract the actual rendered frames in one decode and label them for human review."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise MediaQAError("review sheet failed: Pillow is missing") from exc
    if not points:
        raise MediaQAError("review sheet failed: no valid sample times")
    out_dir = os.path.join(P, "out")
    out = os.path.join(out_dir, "qa_review.jpg")
    pending = None
    try:
        os.makedirs(out_dir, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".qa_frames-", dir=out_dir) as frames_dir:
            indexes = [round(at * 30) for at, _ in points]
            selector = "+".join(f"eq(n,{n})" for n in indexes)
            checked("review sheet failed", "ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-y",
                    "-i", video, "-vf", f"fps=30,select='{selector}',scale=270:-2", "-fps_mode", "vfr",
                    os.path.join(frames_dir, "frame-%04d.jpg"))
            files = sorted(os.path.join(frames_dir, name) for name in os.listdir(frames_dir) if name.endswith(".jpg"))
            if len(files) != len(points):
                raise MediaQAError(f"review sheet failed: extracted {len(files)} of {len(points)} requested frames")
            cols, tw, th, label_h = 8, 270, 480, 32
            rows = math.ceil(len(files) / cols)
            sheet = Image.new("RGB", (cols * tw, rows * (th + label_h)), "white")
            draw = ImageDraw.Draw(sheet)
            font = ImageFont.load_default()
            for i, (frame, (_, label)) in enumerate(zip(files, points)):
                x, y = (i % cols) * tw, (i // cols) * (th + label_h)
                with Image.open(frame) as image:
                    sheet.paste(image.convert("RGB").resize((tw, th)), (x, y + label_h))
                draw.text((x + 5, y + 8), label[:37], fill="black", font=font)
            fd, pending = tempfile.mkstemp(prefix=".qa_review-", suffix=".jpg", dir=out_dir)
            os.close(fd)
            sheet.save(pending, quality=88)
            os.replace(pending, out)
            pending = None
    except (MediaQAError, OSError, ValueError) as exc:
        if pending and os.path.exists(pending): os.remove(pending)
        if isinstance(exc, MediaQAError): raise
        raise MediaQAError(f"review sheet failed: {exc}") from exc
    return out


def write_report(P, video, payload, master_fp, light_fp):
    """Bind machine findings to the exact MP4 so a later edit cannot reuse stale QA."""
    out = os.path.join(P, "out", "qa_report.json")
    try:
        payload = dict(payload, video_sha256=master_fp["sha256"], video_bytes=master_fp["bytes"],
                       light_sha256=light_fp["sha256"], light_bytes=light_fp["bytes"])
        fd, pending = tempfile.mkstemp(prefix=".qa_report-", suffix=".json", dir=os.path.dirname(out))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as target:
                json.dump(payload, target, ensure_ascii=False, indent=2)
                target.write("\n")
            os.replace(pending, out)
        finally:
            if os.path.exists(pending): os.remove(pending)
    except OSError as exc:
        raise MediaQAError(f"QA report failed: {exc}") from exc
    return out


def main(P, video):
    started = time.monotonic()
    # A failed rerun must not expose a previous contact sheet as evidence for this video.
    for name in ("qa_sheet.jpg", "qa_review.jpg", "qa_report.json"):
        old_sheet = os.path.join(P, "out", name)
        if os.path.exists(old_sheet):
            try: os.remove(old_sheet)
            except OSError as exc:
                print(f"FAIL contact sheet: could not remove old image: {exc}")
                return 1
    try:
        with open(f"{P}/work/timeline.json") as f: tl = json.load(f)
        with open(f"{P}/work/words.json") as f: W = json.load(f)["words"]
        with open(f"{P}/plan.json") as f: meta = json.load(f).get("meta", {})
        sfx_path = f"{P}/work/sfx_used.json"
        if os.path.exists(sfx_path):
            with open(sfx_path) as f: sfx = json.load(f)
        else: sfx = tl["sfx"]
        caption_path = f"{P}/work/caption_qa.json"
        if os.path.exists(caption_path):
            with open(caption_path) as f: caption_manifest = json.load(f)
        else: caption_manifest = None
        with open(f"{P}/hf/index.html") as f: idx = f.read()
        D = float(tl["duration"])
        if not math.isfinite(D) or D <= 0 or not tl.get("beats") or not W:
            raise ValueError("timeline needs a positive duration, beats and words")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL project data: {exc}")
        return 1
    try:
        if video.endswith("_light.mp4"):
            raise MediaQAError("pass the master MP4, not its light copy")
        light = os.path.splitext(video)[0] + "_light.mp4"
        master_fp, light_fp = fingerprint(video), fingerprint(light)
        I, tp, video_size = inspect_media(video, D)
        light_I, light_tp, light_size = inspect_media(light, D)
        if video_size != light_size:
            raise MediaQAError(f"light copy dimensions {light_size} differ from master {video_size}")
        if abs(I - light_I) > .2 or abs(tp - light_tp) > .2:
            raise MediaQAError("light copy audio loudness/peak differs from master")
        black, frozen = visual_faults(video, D)
        light_black, light_frozen = visual_faults(light, D)
    except MediaQAError as exc:
        print(f"FAIL media: {exc}")
        return 1
    fails, warns = [], []
    for label, bk, fr in (("master", black, frozen), ("light", light_black, light_frozen)):
        vf, vw = classify_visual_faults(tl, bk, fr)
        fails.extend(f"{label}: {finding}" for finding in vf)
        warns.extend(f"{label}: {finding}" for finding in vw)
    if caption_manifest is None:
        fails.append("caption metadata missing: work/caption_qa.json; rebuild the current plan")
        captions = []
    else:
        try:
            provenance = build_provenance(P, video_size)
            fails.extend(caption_safety(caption_manifest, D, provenance, W))
        except MediaQAError as exc: fails.append(str(exc))
        captions = caption_manifest.get("captions", []) if isinstance(caption_manifest, dict) else []
    S = era_view(load_style(meta.get("style"), P), meta.get("era", "2026")); pace, snd, L = S["pace"], S["sound"], S["layouts"]
    bold = meta.get("profile", "bold") != "measured"
    if not os.path.exists(sfx_path):
        fails.append("SFX audibility unverified: work/sfx_used.json missing")
    elif os.path.exists(sfx_path):
        sf, sw = sfx_audibility(sfx, D, measured=not bold, project=P, planned=tl["sfx"])
        fails.extend(sf); warns.extend(sw)
        try: finish_audit(P, master_fp, light_fp, sfx)
        except MediaQAError as exc: fails.append(str(exc))
    speech_measurements = {}
    for label, path in (("master", video), ("light", light)):
        try:
            measures = speech_sync(path, os.path.join(P, "work", "voice.wav"), W, D)
            speech_measurements[label] = measures
            for item in measures:
                if item["correlation"] < .25:
                    fails.append(f"{label}: spoken content could not be matched near {item['window_start_s']:.2f}s (correlation {item['correlation']:.2f})")
                elif abs(item["offset_s"]) > .08:
                    fails.append(f"{label}: speech offset {item['offset_s']:+.3f}s near {item['window_start_s']:.2f}s")
            if len(measures) > 1 and abs(measures[-1]["offset_s"] - measures[0]["offset_s"]) > .08:
                fails.append(f"{label}: speech timing drifts across the reel")
        except MediaQAError as exc:
            fails.append(f"{label}: {exc}")
    if abs(I - (-14.0)) > 1.0: fails.append(f"loudness {I} LUFS (target -14 ±1)")
    if tp > -0.5: fails.append(f"true peak {tp} dBTP (must be ≤ -0.5)")
    gaps = sorted(b["start"] - a["end"] for a, b in zip(W, W[1:])); wps = len(W) / max(W[-1]["end"] - W[0]["start"], 1e-6)
    if gaps and gaps[-1] > 0.6: warns.append(f"longest pause {gaps[-1]:.2f}s — re-run prep.py cut with a smaller --max-gap")
    share = {"split": 0, "graphic": 0, "face": 0}; runs = []
    for b in tl["beats"]:
        lay = "graphic" if b["layout"] in ("graphic", "broll") else b["layout"]; d = b["t1"] - b["t0"]; share[lay] += d / D
        if runs and runs[-1][0] == lay: runs[-1][1] += d
        else: runs.append([lay, d])
    if S.get("open_layout") and tl["beats"][0]["layout"] != S["open_layout"]: fails.append(f"opening beat is not {S['open_layout']} (style '{S.get('name')}')")
    if S.get("close_layout") and tl["beats"][-1]["layout"] != S["close_layout"]: fails.append(f"closing beat is not {S['close_layout']} (style '{S.get('name')}')")
    first_change = tl["beats"][1]["t0"] if len(tl["beats"]) > 1 else D
    dens = 10 * len(sfx) / D; ref_sfx = snd["sfx_per_10s"]
    cap_sfx = 13 if bold else ref_sfx["hi"] + 2
    if dens > cap_sfx: warns.append(f"{dens:.1f} SFX per 10 s — busier than the {'bold profile' if bold else 'style'} allows; lower meta.sfx_per_10s")
    caps = len(re.findall(r'class="clip cap ', idx))
    if caps < len(W) / 3.5 and S.get("captions", {}).get("always_on", True): fails.append(f"only {caps} caption chunks for {len(W)} words (style: ~1 chunk per 2 words, captions on almost all the time)")
    print(f"style '{S.get('name')}'\n{'metric':28} {'this reel':>12} {'style':>12}")
    for k, v, r in [("duration s", f"{D:.1f}", f"{pace['duration'][0]}–{pace['duration'][1]}"), ("words per second", f"{wps:.2f}", pace["wps"]),
                    ("pause p90 s", f"{gaps[int(len(gaps) * .9)]:.2f}" if gaps else "-", pace["gap_p90"]),
                    ("first visual change s", f"{first_change:.2f}", pace["first_change"]["median"]), ("layout run median s", f"{st.median(r[1] for r in runs):.2f}", pace["layout_run_median"]),
                    ("split share", f"{share['split']:.2f}", L["split"]["median"]), ("graphic share", f"{share['graphic']:.2f}", L["graphic"]["median"]), ("face share", f"{share['face']:.2f}", L["face"]["median"]),
                    ("caption chunks", caps, "~words/2"), ("SFX per 10 s", f"{dens:.1f}", "bold 8–12" if bold else f"{ref_sfx['lo']}–{ref_sfx['hi']}"),
                    ("loudness LUFS", I, snd["lufs"]), ("true peak dBTP", tp, snd["true_peak"])]:
        print(f"{k:28} {str(v):>12} {str(r):>12}")
    try:
        sheet = make_sheet(P, video, D)
        points = review_points(tl, captions)
        review = make_review_sheet(P, video, points)
    except MediaQAError as exc:
        fails.append(str(exc))
        sheet = None; review = None
        points = []
    try:
        if fingerprint(video) != master_fp or fingerprint(light) != light_fp:
            fails.append("master or light MP4 changed while QA was running")
    except MediaQAError as exc: fails.append(str(exc))
    review_required = any("review required:" in warning for warning in warns)
    try:
        report = write_report(P, video, {
            "status": "fail" if fails else "review_required" if review_required else "pass",
            "video": os.path.basename(video), "timeline_duration_s": D,
            "loudness_lufs": I, "true_peak_dbtp": tp,
            "light_loudness_lufs": light_I, "light_true_peak_dbtp": light_tp,
            "black_intervals_s": black, "frozen_intervals_s": frozen,
            "light_black_intervals_s": light_black, "light_frozen_intervals_s": light_frozen,
            "caption_count_checked": len(captions),
            "caption_check_scope": "provenance, timing and conservative container bounds; rendered glyphs and face overlap require human review",
            "sfx_count_checked": len(sfx) if isinstance(sfx, list) else 0,
            "sfx_check_scope": "isolated pre-master cue stems against voice, music and other SFX; listen to final mix",
            "speech_sync": speech_measurements,
            "review_frames": [{"time_s": at, "label": label} for at, label in points],
            "qa_elapsed_s": round(time.monotonic() - started, 3),
            "failures": fails, "warnings": warns,
            "human_review_required": ["inspect actual caption glyphs and face overlap in qa_review.jpg",
                                      "watch and listen to the full master and light MP4"],
        }, master_fp, light_fp)
    except MediaQAError as exc:
        fails.append(str(exc))
        report = None
    for f in fails: print("FAIL", f)
    for w in warns: print("warn", w)
    if sheet:
        print("sheet →", f"{sheet} (inspect rendered caption glyphs, face overlap and empty frames)")
    if review:
        print("review →", f"{review} ({len(points)} rendered frames: opening, before/after every cut, beat and caption centres; listen to the MP4 too)")
    if report: print("report →", report)
    return 1 if fails else 2 if review_required else 0


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): raise SystemExit(__doc__)
    P = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2: v = sys.argv[2]
    else:
        try:
            candidates = (os.path.join(P, "out", f) for f in os.listdir(f"{P}/out") if f.endswith(".mp4") and not f.endswith("_light.mp4") and f != "picture.mp4")
            v = max(candidates, key=os.path.getmtime)
        except (OSError, ValueError):
            raise SystemExit("FAIL media: no finished MP4 found in out/ (run finish.py first)") from None
    sys.exit(main(P, v))
