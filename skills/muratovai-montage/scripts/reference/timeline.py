"""Portable, timecoded observations from a reference reel.

The scene detector and separated-background onsets are candidates, not verified
edit decisions or isolated SFX. Keep their provenance in the profile so the
planner can use the measurements without mistaking them for ground truth.
"""
import collections
import math
import os
import statistics as st


FRAME_FIELDS = ("layout", "face", "top_bg", "graphic", "caption_font", "caption_color", "caption_y",
                "caption_x", "caption_w", "caption_h", "highlight", "accent", "motion", "title_font", "title_color",
                "title_x", "title_y", "title_w", "title_h", "title_role", "graphic_motion", "transition")
CHANGE_FIELDS = ("layout", "graphic", "caption_font", "caption_color", "caption_y", "caption_x", "caption_w",
                 "caption_h", "title_font", "title_color", "title_x", "title_y", "title_w", "title_h",
                 "graphic_motion", "accent", "face")
GEOMETRY_FIELDS = {"caption_x", "caption_y", "caption_w", "caption_h", "title_x", "title_y", "title_w", "title_h"}
DETAIL_FIELDS = GEOMETRY_FIELDS | {"title_font", "title_color", "title_role", "graphic_motion", "transition"}
DETAIL_ENUMS = {"title_role": {"headline", "ui_label", "body", "unknown"},
                "title_font": {"none", "bold_sans", "italic_serif", "italic_serif_plus_bold_sans", "pixel_or_mono", "bold_italic_caps", "other"},
                "title_color": {"none", "white", "black", "accent", "mixed", "other"},
                "graphic_motion": {"none", "pop", "slide", "type", "scale", "count", "highlight", "fade", "other"},
                "transition": {"none", "cut", "dissolve", "zoom", "blur", "flash", "leak", "other"}}


def apply_observations(frames, observations, reel_id):
    """Overlay sparse manual reinspection onto old 14-column frame tags."""
    result = [dict(frame) for frame in frames]
    for item in observations:
        if item.get("reel") != reel_id: continue
        index = item.get("frame")
        if not isinstance(index, int) or not 1 <= index <= len(result):
            raise ValueError(f"{reel_id}: observation frame {index!r} outside 1..{len(result)}")
        frame = result[index - 1]
        frame_size = item.get("frame_size_px", [360, 640])
        if not (isinstance(frame_size, list) and len(frame_size) == 2 and all(isinstance(v, int) and v > 0 for v in frame_size)):
            raise ValueError(f"{reel_id} frame {index}: frame_size_px must be [width,height]")
        for kind in ("caption", "title"):
            box = item.get(f"{kind}_box_px")
            if box is None: continue
            width, height = frame_size
            if not (isinstance(box, list) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box)
                    and 0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height):
                raise ValueError(f"{reel_id} frame {index}: invalid {kind}_box_px")
            left, top, right, bottom = box
            frame.update({f"{kind}_x": round((left + right) / (2 * width), 4),
                          f"{kind}_y": round((top + bottom) / (2 * height), 4),
                          f"{kind}_w": round((right - left) / width, 4),
                          f"{kind}_h": round((bottom - top) / height, 4)})
        for key, value in item.items():
            if key in ("reel", "frame", "source", "frame_size_px", "caption_box_px", "title_box_px"): continue
            if key not in DETAIL_FIELDS: raise ValueError(f"{reel_id} frame {index}: unknown observation {key}")
            if key in GEOMETRY_FIELDS and (not isinstance(value, (int, float)) or not 0 <= value <= 1):
                raise ValueError(f"{reel_id} frame {index}: {key} must be 0..1")
            if key in DETAIL_ENUMS and value not in DETAIL_ENUMS[key]:
                raise ValueError(f"{reel_id} frame {index}: invalid {key} {value!r}")
            frame[key] = value
        frame["observation_source"] = item.get("source", "manual_frame_inspection")
    return result


def scene_points(scenes, duration, threshold=0.1, merge_s=0.2):
    """Deduplicate nearby scene-score peaks, keeping the strongest candidate."""
    points = []
    for t, score in zip(scenes.get("t", []), scenes.get("score", [])):
        if not isinstance(t, (int, float)) or not isinstance(score, (int, float)):
            continue
        if not math.isfinite(t) or not math.isfinite(score) or score <= threshold or not 0.05 < t < duration - 0.05:
            continue
        if points and t - points[-1]["t_s"] <= merge_s:
            if score > points[-1]["score"]: points[-1] = dict(t_s=round(t, 3), score=round(score, 3))
        else:
            points.append(dict(t_s=round(t, 3), score=round(score, 3)))
    return points


def frame_palette(path):
    """Coarse colours at one timecode; exact text/accent colour still needs tags."""
    try:
        from PIL import Image
    except ImportError:
        return None
    if not os.path.isfile(path): return None
    with Image.open(path) as im:
        small = im.convert("RGB").resize((36, 64))
        pixels = [tuple((v // 16) * 16 + 8 for v in rgb) for rgb in small.getdata()]
    def top(values):
        counts = collections.Counter(values)
        return [["#%02X%02X%02X" % c, round(n / len(values), 3)] for c, n in counts.most_common(3)]
    upper = [pixels[y * 36 + x] for y in range(29) for x in range(36)]
    return {"full": top(pixels), "top": top(upper)}


def _near_word(t, words):
    valid = [w for w in words if isinstance(w.get("start"), (int, float))]
    if not valid: return None
    word = min(valid, key=lambda w: abs(t - w["start"]))
    return round((t - word["start"]) * 1000)


def frame_samples(frames, frame_dir=None):
    out = []
    for i, frame in enumerate(frames):
        if "error" in frame: continue
        f = {"t_s": round(float(frame["t"]), 3), **{k: frame[k] for k in FRAME_FIELDS if k in frame}}
        f["caption_words"] = len(frame.get("caption", "").split())
        f["title_chars"] = len(frame.get("title_text", ""))
        if frame.get("brands"): f["brands"] = frame["brands"]
        if frame.get("observation_source"): f["observation_source"] = frame["observation_source"]
        if frame_dir:
            palette = frame_palette(os.path.join(frame_dir, f"{i + 1:04d}.jpg"))
            if palette: f["palette"] = palette
        out.append(f)
    return out


def visual_events(frames, words, fps_sample):
    out = []
    prev = None
    for frame in frames:
        if prev is not None:
            changed = {k: {"from": prev.get(k), "to": frame.get(k)} for k in CHANGE_FIELDS
                       if prev.get(k) != frame.get(k) and
                       (k not in GEOMETRY_FIELDS or all(isinstance(f.get(k), (int, float)) and f[k] >= 0
                                                        for f in (prev, frame)))}
            if changed:
                t = frame["t_s"]
                out.append({"t_s": t, "changes": changed, "nearest_word_start_offset_ms": _near_word(t, words),
                            "time_uncertainty_ms": round(500 / fps_sample), "source": "sampled_frame_tags"})
        prev = frame
    return out


def speech_pauses(words, duration, min_s=0.3):
    out = []
    ordered = sorted((w for w in words if isinstance(w.get("start"), (int, float)) and isinstance(w.get("end"), (int, float))),
                     key=lambda w: w["start"])
    for a, b in zip(ordered, ordered[1:]):
        start, end = max(0, a["end"]), min(duration, b["start"])
        if end - start >= min_s:
            out.append({"start_s": round(start, 3), "end_s": round(end, 3), "duration_s": round(end - start, 3),
                        "source": "word_timestamps"})
    return out


def _transition_at(t, frames, score):
    tagged = [f for f in frames if f.get("transition") not in (None, "none") and 0 <= f["t_s"] - t <= 0.5]
    if tagged: return min(tagged, key=lambda f: f["t_s"] - t)["transition"], "agent_frame_tag"
    return ("cut_candidate" if score > 0.3 else "visual_change_candidate"), "scene_score"


def shots(points, frames, duration):
    ends = [p["t_s"] for p in points] + [duration]
    starts = [0.0] + [p["t_s"] for p in points]
    result = []
    for i, (start, end) in enumerate(zip(starts, ends)):
        transition, source = ("opening", "reel_start") if i == 0 else _transition_at(start, frames, points[i - 1]["score"])
        sample = [f for f in frames if start <= f["t_s"] < end]
        modes = collections.Counter(f.get("layout") for f in sample if f.get("layout"))
        result.append({"start_s": round(start, 3), "end_s": round(end, 3), "duration_s": round(end - start, 3),
                       "entry_score": None if i == 0 else points[i - 1]["score"], "entry_transition": transition,
                       "transition_source": source, "layout": modes.most_common(1)[0][0] if modes else None})
    return result


def _music_accents(bed, sfx):
    """1 s background-energy peaks; candidates because music and effects share a stem."""
    out = []
    for i in range(1, len(bed) - 1):
        current, left, right = bed[i], bed[i - 1], bed[i + 1]
        if current > -50 and current - max(left, right) >= 3 and not any(abs(i + 0.5 - e.get("t_s", -10)) < 0.35 for e in sfx):
            out.append({"t_s": i + 0.5, "rise_db": round(current - max(left, right), 1),
                        "source": "one_second_background_stem_peak", "classification": "candidate"})
    return out


def sound_timeline(audio):
    if not audio: return {"status": "unmeasured_no_stems", "sfx": [], "music_accents": [], "bed": []}
    sfx = audio.get("sfx_events", [])
    bed = audio.get("bg_1s_medians", [])
    return {"status": "separated_background_candidates", "sfx": sfx,
            "music_accents": _music_accents(bed, sfx),
            "bed": [{"start_s": i, "end_s": i + 1, "median_20ms_dbfs": value} for i, value in enumerate(bed)]}


def make_timeline(info, scenes, frames, words, audio=None, face_track=None, frame_dir=None, fps_sample=2):
    duration = float(info["dur"])
    sampled = frame_samples(frames, frame_dir)
    points = scene_points(scenes, duration)
    shot_list = shots(points, sampled, duration)
    return {"id": info["id"], "duration_s": round(duration, 3), "resolution": {"w": info["w"], "h": info["h"]},
            "shots": shot_list, "frames": sampled, "visual_events": visual_events(sampled, words, fps_sample),
            "pauses": speech_pauses(words, duration), "face_track": face_track or [], "audio": sound_timeline(audio),
            "measurement_notes": ["Scene-score boundaries are shot candidates and may include graphic animation.",
                                  "Frame tags are sampled; event times carry half-sample uncertainty.",
                                  "Audio transients and music accents are candidates from a separated background stem."]}


def median_or_none(values, digits=2):
    values = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
    return round(st.median(values), digits) if values else None
