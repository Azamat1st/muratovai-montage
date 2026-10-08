# Style profiles: measure a creator, then edit in their style

A **style profile** is a folder that tells the engine and the planner how a particular creator's reels are edited. The skill ships
no built-in style: every user first makes a profile from 2–5 reels of a creator they choose, then edits a new talking-head take in
that style. `scripts/reference/make_skill.py` can pack the profile as its own skill, `montage-<handle>`. The engine keeps neutral
fallback numbers in `styles/_defaults/style.json`, used only for fields a profile lacks; `styles/_template/style-bible.md` is the
section skeleton of a style bible.

## What is in a profile

| file | who writes it | who reads it |
|---|---|---|
| `style.json` | `analyze_reference.py report` (edit it if a number looks wrong) | `autoplan.py` (opening layout, visual-segment duration, caption bounds, defaults), `plan_lint.py` and `qa.py` (targets), `build.py` (face framing), `finish.py` (levels of the `measured` sound profile) |
| `STYLE_METRICS.md` | `analyze_reference.py report` | you, when writing the style bible |
| `style-bible.md` | you, from `style-bible.draft.md` | the planner, before every plan in this style |
| `analysis/<id>.md` | you, with `references/beat-sheet-prompt.md` | you and the planner, as worked examples |
| `analysis/reference_timeline.json` | `analyze_reference.py report` | planner and reviewer: per-reference timestamps for candidate visual segments, visual tags, sampled colours, face track, pauses and sound events; no transcript or frame images |
| `analysis/reference_index.md` and `analysis/windows/*.json` | `make_skill.py` when a timeline exists | planner: small representative windows selected by reel and semantic slot; read only matching windows by default |
| `analysis/geometry_observations.json` (optional) | agent reinspection of selected source frames | `analyze_reference.py report` overlays verified text boxes and transitions onto older frame tags; packaged for provenance |
| `raw/`, `work/` | `fetch_reels.py`, `analyze_reference.py` | private working files, never packaged |
| `sources.json` | `fetch_reels.py` | optional reference URLs, packaged when present |

`raw/` holds the downloaded reels and `work/` their frames and transcripts. They are for private analysis: keep them out of any
repository you publish (a profile you share needs only the four files above).

## Make a profile ("analyze this creator's montage")

```bash
S=<scripts folder of the installed skill>          # wherever your agent installed it
D=~/reels/styles/<handle>                          # a folder next to your projects, not inside the skill
python3 $S/reference/fetch_reels.py $D <link or file> <link or file> ...
python3 $S/reference/analyze_reference.py $D all --lang en
```

1. **Collect 2–5 reels.** Links to Instagram reels, TikToks, YouTube Shorts, or local video files. With `APIFY_TOKEN` set,
   Instagram links go through Apify (≈ $0.01 per reel); otherwise, and for all other sites, `yt-dlp` downloads them. Instagram
   often blocks anonymous downloads: then pass cookies to yt-dlp (`--yt-dlp-args "--cookies-from-browser chrome"`), set
   `APIFY_TOKEN`, or ask the user to download the reels and give you the files. Pick reels of the same format and period: one
   creator can change their edit a lot within a year.
2. **Measure.** `analyze_reference.py all` extracts 2 frames per second, contact sheets, scene-score candidates, words
   (ElevenLabs Scribe), the Demucs voice/background split (music-bed level and background transients with per-event peak,
   rise and offset from cuts), and frame grids. Tag every frame's layout, face scale, graphic, caption/font/colour, and where
   visible the normalized caption/title boxes, graphic motion and transition type in `vision_tags.tsv`. The old 14-column
   format still imports, leaving new fields unknown. `vision-import` and `report` add sampled palette per timecode, face track,
   word pauses and `analysis/reference_timeline.json`. A scene-score boundary may be an animated UI rather than a camera cut;
   a Demucs onset may be music rather than an SFX. Inspect the source before naming either. Listen to the reference audio
   when identifying a sound or musical accent; do not infer its genre or individual gain from stem energy alone.
3. **Look.** Read `STYLE_METRICS.md`; inspect selected reels/time windows in `analysis/reference_timeline.json` without
   loading the whole file into the agent context. Open every `work/<id>/sheet.jpg` (tile k = k·0.5 s)
   and full-size frames of anything unclear. Inspect frames immediately before and after transitions, text at phone size,
   and listen to suspected SFX/music accents. Record sparse reinspection of older references in
   `analysis/geometry_observations.json` using `frame`, `caption_box_px` or `title_box_px` `[left,top,right,bottom]`,
   `frame_size_px` if not 360×640, and optional `transition`/`title_font`/`title_role`.
4. **Break it down.** Write `analysis/<id>.md` per reel with `references/beat-sheet-prompt.md` (roles and trigger words, never the
   script).
5. **Write the style bible.** Turn `style-bible.draft.md` into `style-bible.md`: keep the section order of
   `styles/_template/style-bible.md`, fill every TODO with what you saw, and end with 10–20 numbered rules for the planner, each with
   numbers. Map every observation onto an engine feature (table below).
6. **Check `style.json`.** `shots.duration_s` comes from candidate visual changes, not verified camera cuts;
   `shots.transition_share` includes `cut_candidate` and `visual_change_candidate` until source windows are manually checked.
   Caption/title `bounds_by_layout` are normalized centre x/y and width/height from observed boxes. `sound.sfx_peak_*` describes
   unclassified separated-background transients, not an isolated SFX mix target. Ranges come from only a few reels; fix anything
   that contradicts your eyes and set `plan_defaults` (accent, era, music, trans). A repeat report preserves curated defaults.
7. **Report to the user** in 5–8 lines: pace, layout mix, captions, colours, sound, the 2–3 signature moves, and the profile path.

## Edit in a profile ("edit my video in this style")

```bash
python3 $S/autoplan.py $P --style ~/reels/styles/<handle> --cta WORD --lang en
```
`autoplan.py` stores the profile path in `plan.json → meta.style`. From then on: read the profile's `style-bible.md` and,
when packaged, `analysis/reference_index.md` before planning. Open one or two matching `analysis/windows/*.json` files;
the complete timeline is archival evidence for targeted follow-up. Legacy profiles without a timeline use their beat sheets.
The engine docs in `references/` stay the same; `plan_lint.py`, `build.py`, `finish.py` and `qa.py` use the style's numbers
automatically. A `montage-<handle>` skill folder is a valid profile too. Without `--style` the engine has only the fallback
numbers of `styles/_defaults`, which are not a style: make a profile first (SKILL.md part A).

## Observation → engine feature

| you see in the analyzed reels | use |
|---|---|
| split with an arch, the head crossing its top edge | default split (`era: "2026"`) |
| straight 50/50 split, captions in a grey box | `meta.era: "2025"` |
| hard cuts only | `meta.trans: "cut"` |
| soft push-ins, dissolves, zooms between scenes | `meta.trans: "auto"` |
| effects clearly audible, many per 10 s | `meta.profile: "bold"` |
| effects felt more than heard, few per 10 s | `meta.profile: "measured"` (levels from `style.json`) |
| the frame punches in at the start | `meta.open_punch` |
| the speaker snaps from a close-up into the split at the start | `meta.open_zoom` |
| a white flash at the start | `meta.flash_start` |
| warm light leaks on some cuts | `"trans": "leak"` on those beats |
| a title that scrambles through glyphs | `title` with `decode: true` |
| caption styles | `caption_style` per beat (`split`, `face`, `caps`, `mix`, `box`, `box_seam`, `face25`) |
| a font the kit does not have | the closest bundled one (Inter, Playfair Display, Noto Serif Display, Press Start 2P, Pixelify Sans, JetBrains Mono, Unbounded, Instrument Serif); to add a font, put its woff2 files in `assets/fonts/` with its licence and add `@font-face` rules to `assets/fonts/fonts.css` |
| a signature move the kit lacks | an `html` beat (see `shot-library.md`) |
| the face bigger or smaller than the fallback framing | `style.json → framing` (measured automatically when a face tracker is available) |

## Limits

- The engine builds one grid: split / face / full-frame graphic / b-roll. Other layouts (picture-in-picture, side-by-side) need
  `html` beats with the head hidden, or are out of reach.
- Caption animation is limited to the engine's caption styles; exotic kinetic typography can be approximated with `html`.
- Fonts, music and the creator's own footage are not copied: use free fonts, your own music and your own screenshots and clips.
- Framing and colours are measured; taste is not. The style bible is only as good as the breakdowns you write.
- Learn from public reels, do not copy them: don't reuse their frames, audio or script.
