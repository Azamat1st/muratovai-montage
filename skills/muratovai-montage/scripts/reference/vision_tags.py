"""Frame tags by the agent itself (replaces the OpenAI vision model in this fork of the kit).

  export(w)            frames/NNNN.jpg → vision_grids/gNN.jpg (8 labelled frames per image) + vision_task.md (what to tag, how)
  parse_tags(text, n)  the agent's vision_tags.tsv → one dict per frame, the same fields the OpenAI model returned (SCHEMA)
  write_vision(w, F)   → vision.json, read by analyze_reference.py report exactly as before

TSV: one line per frame or per range of frames, tab-separated, columns in COLUMNS order. "^" repeats the previous frame's value,
"-" is empty (no accent, no brands, no title, no caption), "12-18" gives frames 12..18 the same line. Lines starting with # are skipped.
"""
import glob, json, os, re

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # this skill's scripts/ folder, wherever it is installed

FPS_SAMPLE = 2          # frames per second sampled by analyze_reference.py prep
GRID_COLS, GRID_ROWS = 4, 2
LABEL_H = 30            # px of the label bar above each tile (keeps the label off the captions)
TASK = "vision_task.md"
TAGS = "vision_tags.tsv"

SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["layout", "face", "top_bg", "graphic", "caption", "caption_font", "caption_color", "caption_y", "highlight", "accent", "title_text", "brands", "motion",
                       "caption_x", "caption_w", "caption_h", "title_x", "title_y", "title_w", "title_h", "title_font", "title_color", "graphic_motion", "transition"],
          "properties": {
              "layout": {"type": "string", "enum": ["split_graphic_top_face_bottom", "face_full", "graphic_full_no_face", "broll_full_no_face", "face_full_with_card_overlay", "other"]},
              "face": {"type": "string", "enum": ["none", "wide", "medium", "closeup"]},
              "top_bg": {"type": "string", "enum": ["white", "light_gray", "black", "dark", "footage_or_image", "none"]},
              "graphic": {"type": "string", "enum": ["none", "single_logo", "logo_row_or_grid", "node_diagram", "ui_or_app_screenshot", "website", "social_post", "terminal_or_code", "chart_or_dashboard", "big_number_or_stat", "text_title", "mascot_or_icon", "broll_video_or_images", "sticky_note_or_callout", "progress_bar", "other"]},
              "caption": {"type": "string"},
              "caption_font": {"type": "string", "enum": ["none", "bold_sans", "italic_serif", "italic_serif_plus_bold_sans", "pixel_or_mono", "bold_italic_caps", "other"]},
              "caption_color": {"type": "string", "enum": ["none", "white", "black", "accent", "mixed"]},
              "caption_y": {"type": "number"},
              "highlight": {"type": "boolean"},
              "accent": {"type": "string"},
              "title_text": {"type": "string"},
              "brands": {"type": "array", "items": {"type": "string"}},
              "motion": {"type": "string", "enum": ["none", "motion_blur", "zoomed_crop", "partial_reveal", "other"]},
              "caption_x": {"type": "number"}, "caption_w": {"type": "number"}, "caption_h": {"type": "number"},
              "title_x": {"type": "number"}, "title_y": {"type": "number"}, "title_w": {"type": "number"}, "title_h": {"type": "number"},
              "title_font": {"type": "string", "enum": ["none", "bold_sans", "italic_serif", "italic_serif_plus_bold_sans", "pixel_or_mono", "bold_italic_caps", "other"]},
              "title_color": {"type": "string", "enum": ["none", "white", "black", "accent", "mixed", "other"]},
              "graphic_motion": {"type": "string", "enum": ["none", "pop", "slide", "type", "scale", "count", "highlight", "fade", "other"]},
              "transition": {"type": "string", "enum": ["none", "cut", "dissolve", "zoom", "blur", "flash", "leak", "other"]}}}
PROMPT = ("One frame of a vertical short-form video (Reel/TikTok/Short) by a talking-head creator. Tag it strictly by the schema.\n"
          "layout: split_graphic_top_face_bottom = a graphic/screen in the upper part and the speaker in the lower part; face_full = only the speaker fills the frame; "
          "graphic_full_no_face = a designed graphic (logos, text, diagram) fills the frame, no speaker; broll_full_no_face = screen recording, footage or images fill the frame, no speaker; "
          "face_full_with_card_overlay = speaker full frame with a small card on top.\n"
          "face: size of the speaker's head: wide (head < 20% of frame height), medium, closeup (head > 35% of frame height, punched in).\n"
          "caption: the spoken-word subtitle text exactly as shown (not headlines inside the graphic; put those in title_text). caption_y: vertical centre of the caption, 0 = top, 1 = bottom, -1 if none.\n"
          "caption_font: bold_sans (e.g. Inter/Helvetica bold), italic_serif (elegant serif italic), italic_serif_plus_bold_sans (a serif italic word next to a bold sans word), pixel_or_mono, bold_italic_caps (heavy slanted capitals).\n"
          "highlight: true if some text has a coloured marker/background highlight. accent: #RRGGBB hex of the main saturated accent colour used in text or graphics "
          "(never white, black or grey), '' if there is none. brands: product/company logos or names visible.\n"
          "caption_x/y and title_x/y are the centre of visible text as a fraction of frame width/height; w/h are its visible box size. "
          "Use -1 for an unknown or absent box. title_font/title_color describe the main headline, not subtitles. "
          "graphic_motion describes its entrance or change, and transition describes the cut into this frame; use none when unseen. "
          "Inspect frames immediately before and after a suspected transition, since the 2 fps grid alone cannot resolve a short dissolve.")
BASE_COLUMNS = ["idx", "layout", "face", "top_bg", "graphic", "caption_font", "caption_color", "caption_y", "highlight", "accent", "motion",
                "brands", "title_text", "caption"]
DETAIL_COLUMNS = ["caption_x", "caption_w", "caption_h", "title_x", "title_y", "title_w", "title_h", "title_font", "title_color", "graphic_motion", "transition"]
COLUMNS = BASE_COLUMNS + DETAIL_COLUMNS
DETAIL_DEFAULTS = {**{k: -1.0 for k in DETAIL_COLUMNS[:7]}, "title_font": "none", "title_color": "none", "graphic_motion": "none", "transition": "none"}
ENUMS = {k: v["enum"] for k, v in SCHEMA["properties"].items() if "enum" in v}
TRUE, FALSE = {"1", "true", "yes", "y"}, {"0", "false", "no", "n"}


# ---------------------------------------------------------------- parsing the agent's tags
def _value(col, raw):
    """one TSV cell → (value, error or None); raw is already stripped and is not "^" """
    if col in ENUMS:
        return (raw, None) if raw in ENUMS[col] else (None, f"{col} {raw!r} is not one of {', '.join(ENUMS[col])}")
    if col == "caption_y" or col in DETAIL_COLUMNS[:7]:
        try: y = float(raw)
        except ValueError: return None, f"{col} {raw!r} is not a number"
        return (y, None) if y == -1 or 0 <= y <= 1 else (None, f"{col} {raw!r} must be 0..1 or -1")
    if col == "highlight":
        low = raw.lower()
        return (low in TRUE, None) if low in TRUE | FALSE else (None, f"highlight {raw!r} must be 0 or 1")
    if col == "accent":
        if raw in ("-", ""): return "", None
        return (raw.upper(), None) if re.fullmatch(r"#[0-9A-Fa-f]{6}", raw) else (None, f"accent {raw!r} must be #RRGGBB or -")
    if col == "brands":
        return ([] if raw in ("-", "") else [b.strip() for b in raw.split(",") if b.strip()]), None
    return ("" if raw == "-" else raw), None   # title_text, caption


def _indexes(raw, n):
    m = re.fullmatch(r"(\d+)(?:-(\d+))?", raw)
    if not m: return None, f"idx {raw!r} must be a frame number or a range like 12-18"
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    if not 1 <= a <= b <= n: return None, f"idx {raw!r} is outside 1..{n}"
    return range(a, b + 1), None


def _row(line, prev):
    """one TSV line → (indexes cell, values dict, errors)"""
    cells = [c.strip() for c in line.split("\t")]
    if len(cells) not in (len(BASE_COLUMNS), len(COLUMNS)):
        return None, {}, [f"has {len(cells)} columns, needs {len(COLUMNS)} (or {len(BASE_COLUMNS)} for old tags): {' '.join(COLUMNS)}"]
    cols = COLUMNS if len(cells) == len(COLUMNS) else BASE_COLUMNS
    vals, errs = {}, []
    for col, raw in zip(cols[1:], cells[1:]):
        if raw == "^":
            if prev is None or prev.get(col) is None: errs.append(f"{col}: ^ has no valid previous value to repeat")
            else: vals[col] = prev[col]
            continue
        v, e = _value(col, raw)
        if e: errs.append(e)
        vals[col] = v
    for col, value in DETAIL_DEFAULTS.items(): vals.setdefault(col, value)
    return cells[0], vals, errs


def _gaps(missing):
    out, run = [], []
    for i in missing:
        if run and i != run[-1] + 1: out.append(run); run = []
        run.append(i)
    if run: out.append(run)
    return ", ".join(str(r[0]) if len(r) == 1 else f"{r[0]}-{r[-1]}" for r in out)


def parse_tags(text, n):
    """the agent's TSV → n frame dicts {t, <SCHEMA fields>}; raises ValueError listing every problem with its line number"""
    frames, errs, prev = {}, [], None
    for ln, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#") or line.split("\t", 1)[0].strip() == COLUMNS[0]: continue
        idx, vals, row_errs = _row(line, prev)
        rng, e = _indexes(idx, n) if idx is not None else (None, None)
        errs += [f"line {ln}: {x}" for x in row_errs + ([e] if e else [])]
        for i in rng or []:
            if i in frames: errs.append(f"line {ln}: frame {i} is tagged twice")
            frames[i] = vals
        prev = {**(prev or {}), **{k: v for k, v in vals.items() if v is not None}}
    missing = [i for i in range(1, n + 1) if i not in frames]
    if missing: errs.append(f"frames without tags: {_gaps(missing)}")
    if errs: raise ValueError("\n".join(errs))
    return [dict(t=round((i - 1) / FPS_SAMPLE, 2), **{k: frames[i][k] for k in SCHEMA["required"]}) for i in range(1, n + 1)]


def write_vision(w, frames):
    json.dump(dict(schema_version=2, frames=frames, tokens=[0, 0], model="agent tags"), open(f"{w}/vision.json", "w"), ensure_ascii=False)


def import_tags(w):
    """vision_tags.tsv → vision.json; returns a short status line, raises ValueError on bad tags"""
    n = len(glob.glob(f"{w}/frames/*.jpg"))
    if not os.path.exists(f"{w}/{TAGS}"): return f"{os.path.basename(w)}: no {TAGS} yet ({n} frames to tag, see {TASK})"
    write_vision(w, parse_tags(open(f"{w}/{TAGS}", encoding="utf-8").read(), n))
    return f"{os.path.basename(w)}: {n} frames tagged"


# ---------------------------------------------------------------- export for the agent
def _tile(path, k, label_font):
    from PIL import Image, ImageDraw
    im = Image.open(path).convert("RGB")
    tile = Image.new("RGB", (im.width, im.height + LABEL_H), "#FFD400")
    tile.paste(im, (0, LABEL_H))
    ImageDraw.Draw(tile).text((8, 3), f"#{k}  {(k - 1) / FPS_SAMPLE:.1f}s", fill="black", font=label_font)
    return tile


def _font():
    from PIL import ImageFont
    try: return ImageFont.load_default(size=22)
    except TypeError: return ImageFont.load_default()


def export_grids(w):
    """frames → vision_grids/gNN.jpg, GRID_COLS × GRID_ROWS labelled frames each; returns the grid paths"""
    from PIL import Image
    frames, per, font = sorted(glob.glob(f"{w}/frames/*.jpg")), GRID_COLS * GRID_ROWS, _font()
    os.makedirs(f"{w}/vision_grids", exist_ok=True); out = []
    for g in range(0, len(frames), per):
        tiles = [_tile(p, g + j + 1, font) for j, p in enumerate(frames[g:g + per])]
        tw, th = tiles[0].size
        sheet = Image.new("RGB", (tw * GRID_COLS, th * GRID_ROWS), "#202020")
        for j, t in enumerate(tiles): sheet.paste(t, ((j % GRID_COLS) * tw, (j // GRID_COLS) * th))
        path = f"{w}/vision_grids/g{g // per + 1:02d}.jpg"; sheet.save(path, quality=88); out.append(path)
    return out


def export(w, d):
    """grids + the task file for one reel; returns a short status line"""
    if os.path.exists(f"{w}/vision.json"): return f"{os.path.basename(w)}: vision.json exists"
    grids = sorted(glob.glob(f"{w}/vision_grids/g*.jpg")) or export_grids(w)
    n = len(glob.glob(f"{w}/frames/*.jpg"))
    open(f"{w}/{TASK}", "w", encoding="utf-8").write(task_text(w, d, n, grids))
    return f"{os.path.basename(w)}: {n} frames in {len(grids)} grids → tag into {w}/{TAGS} (see {TASK})"


def task_text(w, d, n, grids):
    enums = "\n".join(f"- {k}: {' | '.join(v)}" for k, v in ENUMS.items())
    example1 = "\t".join(["1", "face_full", "medium", "none", "none", "bold_sans", "white", "0.72", "0", "-", "none", "-", "-", "this is how",
                          "0.50", "0.62", "0.05", "-1", "-1", "-1", "-1", "none", "none", "none", "none"])
    example2 = "\t".join(["2-3"] + ["^"] * 12 + ["I edit"] + ["^"] * len(DETAIL_COLUMNS))
    return f"""# Tag the frames of {os.path.basename(w)}

{n} frames, {FPS_SAMPLE} per second (frame #k is at (k-1)/{FPS_SAMPLE} s). They are laid out {GRID_COLS * GRID_ROWS} per image in
{len(grids)} grids, left to right, top to bottom, each with a yellow label "#k  t". Open every grid with your image-viewing tool,
in order (Claude Code: Read; Codex: `view_image`). A caption too small to read in a grid: open the single frame
{w}/frames/NNNN.jpg (k zero-padded to 4 digits) the same way.

## What each field means
{PROMPT}

## Allowed values
{enums}
- caption_y/x/w/h and title_x/y/w/h: 0..1 or -1 if unknown/absent; x/y are box centres, w/h are box dimensions.
- highlight: 0 or 1 · accent: #RRGGBB or - · brands: comma-separated or -
- title_text: headline text inside the graphic, or - · caption: the subtitle exactly as shown, or -

## Output: {w}/{TAGS}
One line per frame, or one line per range of frames that look the same, tab-separated, in this column order:
{chr(9).join(COLUMNS)}
"^" repeats the previous frame's value; "-" is empty; "12-18" in idx gives frames 12..18 the same line. Every frame 1..{n} exactly once.
Example:
{example1}
{example2}

Then check it: python3 {os.path.join(SCRIPTS, "reference", "analyze_reference.py").replace(os.path.expanduser("~"), "~")} {d} vision-import
(it lists every bad value with its line; fix and run it again until it reports the frames as tagged).

## Grids
""" + "\n".join(grids) + "\n"
