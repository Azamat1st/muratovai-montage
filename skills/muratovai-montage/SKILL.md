---
name: muratovai-montage
description: Edits a vertical talking-head video (Reels, TikTok, Shorts) into a fast, graphics-driven reel in the editing style the user picks. It measures a creator's style from 2–5 of their reels, packs it as a new skill, then edits in it. Arch split, face punch-ins, full-frame graphics, 1–3-word captions, logos, counters and mini-UIs on the words, designed sound, CTA. Engine — HyperFrames. Use it for "edit my video like <creator>", "analyze this creator's editing", "edit this talking head with graphics and captions", "add sound design to my reel", or in Russian «смонтируй», «смонтируй в стиле…», «разбери монтаж», «сделай звуки в рилсе», «установи» for this kit, or in Uzbek «montaj qil», «uslubida montaj qil», «montajini tahlil qil», «oʻrnat». For a talking-head reel it owns the edit end to end, so prefer it over a generic video workflow when one is offered.
---
# Reels montage

> **Кратко по-русски.** Скилл монтирует вертикальный ролик с говорящей головой в стиле, который выбрал сам пользователь. Своего
> стиля в скилле нет: сначала пользователь называет блогера (`@ник` в Instagram) или даёт 2–5 его роликов, скилл измеряет их и
> сохраняет стиль отдельным скиллом `montage-<ник>`. Потом монтирует видео пользователя в этом стиле: паузы, графика и логотипы
> на словах, подписи, музыка, звуки, проверки качества. Путь: «Установи скилл» (ссылка на пакет или архив) → «Разбери монтаж @ник» (или ссылки,
> или файлы) → сильная модель (Claude Code — Opus, Codex — `gpt-6-sol` на `xhigh`) → «Смонтируй в стиле @ник» + видео.
> По-узбекски те же шаги: «Skillni oʻrnat», «@nik montajini tahlil qil», «@nik uslubida montaj qil». Недостающее спрашивай у
> пользователя сам (раздел «Ask first»).
> Ключи: `ELEVENLABS_API_KEY` (обязателен: распознавание речи), `APIFY_TOKEN` (желателен: ролики по `@нику`), в
> `~/.config/muratovai-montage/keys.env`. Отвечай на языке пользователя, коротко, без технических подробностей, пока он сам не спросит.

The skill turns a raw talking-head take into a reel edited the way the creator the user chose edits. There is no built-in style:
every style is measured from reels the user picks, frame by frame (pace, cuts, layout shares, captions, fonts, colours, sound) and
kept as a style profile that is also its own skill.

It has three parts:
1. **Style profiles**: the numbers and rules of one creator's edit (`style.json`, `style-bible.md`, beat sheets), made with
   `scripts/reference/` and packed as a skill `montage-<handle>` by `make_skill.py`. `styles/_defaults/` holds only neutral
   fallback numbers for fields a profile lacks; `styles/_template/style-bible.md` is the skeleton of a style bible.
2. **The engine** (`scripts/`): a plan (`plan.json`) is turned deterministically into a HyperFrames HTML composition, then into mp4,
   then sound is designed from the graphic events.
3. **Quality gates**: the plan is linted before the build, a contact sheet is checked before the render, the finished reel is
   compared with the style's targets after.

Your job as the editor is the decisions: where to cut, which layout each beat gets, what to draw on each phrase. The scripts do
everything mechanical.

## The flow (as the user sees it)

| the user says | do |
|---|---|
| «Установи скилл» / «Skillni oʻrnat» + the kit link or archive / "install the skill" | the kit: its `START_HERE.md` and `install.py`. If the skill is already installed: `python3 $S/selftest.py`, report, and give the next prompt |
| «Разбери монтаж @ник» / «Разбери его монтаж и на основе этого создай уникальный скилл» / «@nik montajini tahlil qil» + an Instagram @handle, reel links or files / "analyze this creator's editing" | **A. Make a style skill** |
| «Смонтируй в стиле @ник» / «Смонтируй в моём стиле» / «@nik uslubida montaj qil» + a video / "edit my video in my style / like <creator>" | **B. Edit a take** with the user's style skill (`montage-<handle>`); ask which one if there are several |
| an edit request and the user has no style yet | explain in one line that the style comes from a creator they like, ask for their @handle (or 2–5 links or files), do A, then B |
| "make the sound" for an existing project | step 7 of B (`finish.py`) |

Recommend the strongest model available for A and B (Claude Code: `/model` → Opus; Codex: e.g. `gpt-6-sol` at reasoning effort `xhigh`).

## Ask first

Ask only for what is missing, in one short message, then work without further questions.
- **Before A:** the creator's Instagram `@handle` (with `APIFY_TOKEN`, `fetch_reels.py` takes their latest 5 reels), or 2–5 links
  (Instagram, TikTok, YouTube Shorts) or files of reels by ONE creator, same format and period; the language of those reels.
  Without `APIFY_TOKEN` a `@handle` cannot be fetched: ask for links or files. If Instagram refuses a link, offer their browser
  cookies (they must be logged in to Instagram there): Chrome on macOS (macOS asks once for "Chrome Safe Storage" access, they
  click Allow), Firefox on Windows (`--yt-dlp-args "--cookies-from-browser firefox"`); or an Apify token, or the files themselves.
- **Before B:** the video file (vertical, the face about 40 % of the frame width); which style if they have several; what the
  reel is about in one sentence and the names of products, sites or people it mentions (for the logos, screenshots and the
  transcription vocabulary); the call to action at the end (a keyword for comments, a link in the bio, or none); the accent colour (their
  brand, or the style's); the language. Offer, don't require: the script text (better captions), their own screenshots or screen
  recordings, links to what they mention, their own music. ElevenLabs gives a studio-clean voice if they have a key.
- Never ask them to paste API keys into the chat: open `~/.config/muratovai-montage/keys.env` for them to paste into.
- The sound of the analyzed reels and of their own take goes to ElevenLabs with their key for transcription; frames are looked at
  by you in this session; the video files stay on the computer. Say so once, before A.

## What to read and when

| when | file |
|---|---|
| before any plan, always | the style bible of the user's profile: `<profile>/style-bible.md` (a `montage-<handle>` skill folder is a profile) |
| choosing the graphic for a phrase | `references/shot-library.md` — trigger in the speech → move → `gfx` |
| cutting the text into beats | `references/beat-planning.md` — order of decisions and worked examples |
| writing `plan.json` | `references/plan-format.md` — every key of the plan and every graphic's parameters |
| making each reel feel new within the style | `references/move-bank.md` — moves by slot, and how to add depth |
| sound: what goes where, levels, checks | `references/sound-design.md`; background research: `references/sound-research.md` |
| the render breaks or looks odd | `references/engine-notes.md` — layers, framing, HyperFrames pitfalls, fallbacks off macOS |
| making a style profile | `references/style-profiles.md` and `references/beat-sheet-prompt.md` |
| a complete plan | `examples/plan.json` (a fictional reel, 27 beats, each with a `_note` on why) and `examples/README.md` |

## Requirements

- **HyperFrames**: the CLI pinned to the tested version, `npx -y hyperframes@0.8.78 …` (the scripts use the same pin;
  `$REELS_HYPERFRAMES` overrides it), Node 22+. In Claude Code, the `hyperframes-core` / `hyperframes-cli` skills describe the
  engine contract in more detail, if installed (optional).
- **ffmpeg 7+** (with libx264 and libvpx-vp9), **Python 3.9+** with `numpy` and `Pillow`. `install.py` puts them (and `yt-dlp`,
  and OpenCV off macOS) into the kit's own environment `~/.local/share/muratovai-montage/venv`; every script re-runs itself there, so
  plain `python3 $S/<script>.py` is always right. Demucs + soundfile (sound stems in the analyzer: the only source of the sound
  numbers in this fork; `install.py` adds them). `playwright` with its headless Chromium: site screenshots (the kit's `install.py` adds both).
- **macOS 12+ on Apple Silicon recommended**: the person cutout and the face track use Apple Vision through the prebuilt arm64
  helpers `scripts/person_mask` and `scripts/face_track`; when they do not run, `prep.py` rebuilds them from the `.swift` sources
  with `swiftc`. Elsewhere the cutout uses `hyperframes remove-background` (local u2net model) and the face track uses OpenCV or a
  centred estimate: check the head framing in the contact sheet then.
- **Windows**: call Python as `python` (or `py`) wherever this file says `python3`, and drop `PRODUCER_BROWSER_GPU_MODE=hardware`
  from the render command. The scripts switch themselves to UTF-8, so Cyrillic and Uzbek text is safe in any console.
- **Keys** (never print them, never paste them into commands or files yourself): `ELEVENLABS_API_KEY` (required: Scribe
  transcription of the reference reels and of the take; also voice isolation and SFX generation), `APIFY_TOKEN` (optional:
  Instagram downloads). Looked up in the environment, `~/.config/muratovai-montage/keys.env`, `export` lines of
  `~/.zshrc`/`~/.bashrc`, then `~/.env/<service>.key`. A missing required key stops the script with a message. No OpenAI key.
- Costs: Scribe transcription spends a little of the user's ElevenLabs credit per minute of audio; frame tagging is your own
  work in the session (≈ 100 grid images for five 80-second reels); Apify ≈ $0.01 per reel. ElevenLabs isolation and
  `sfx_gen.py` spend more of those credits: ask before running them.

All commands below use:
```bash
S=<scripts folder of this installed skill>     # wherever your agent installed this skill's scripts folder
P=~/reels/<date>-<slug>                        # the project folder, never inside the skill
```

## A. Make a style skill ("analyze their editing and create a unique skill")

```bash
D=~/reels/styles/<handle>
python3 $S/reference/fetch_reels.py $D @handle                             # or 2–5 links/files: Instagram, TikTok, Shorts, local files
python3 $S/reference/analyze_reference.py $D all --lang <en|ru|uz|…>        # frames, cuts, words, sound stems, frame grids to tag
```
`all` stops after writing the frame grids: **you tag the frames yourself** (no vision API in this fork). Each reel has
`$D/work/<id>/vision_task.md` (the fields, allowed values, the TSV format) and `vision_grids/gNN.jpg` (8 labelled frames each).
Open every grid with your image-viewing tool (Claude Code: Read; Codex: `view_image`) and write `$D/work/<id>/vision_tags.tsv`;
use ranges and `^` where nothing changes. Tag reels one at a time, in this same session, start to finish, before moving to the
next one. Then:
```bash
python3 $S/reference/analyze_reference.py $D vision-import      # checks every value, lists bad lines; fix until all reels are tagged
python3 $S/reference/analyze_reference.py $D report             # → STYLE_METRICS.md, style.json, style-bible.draft.md
```
Then read `$D/STYLE_METRICS.md` and every `$D/work/<id>/sheet.jpg`, write a beat sheet per reel with
`references/beat-sheet-prompt.md` into `$D/analysis/`, turn `$D/style-bible.draft.md` into `$D/style-bible.md` (the skeleton is
`styles/_template/style-bible.md`, end it with 10–20 numbered rules with numbers), and check `$D/style.json`. Details, the
observation → engine-feature table and the limits are in `references/style-profiles.md`. The downloaded reels stay private in
`$D/raw`: never republish them, never reuse their frames, music or script.
`$D/analysis/reference_timeline.json` keeps per-reel timestamps for candidate visual segments, tagged layouts/type and
colour, word gaps, face positions, and Demucs background transients with relative levels. Inspect source frames around any
boundary before calling it a particular transition or SFX. New tags can record caption/title boxes, motion and transition
types; old 14-column TSVs still import, with those details left unknown.

Pack the profile as its own skill, so «смонтируй в моём стиле» works in any later session:
```bash
python3 $S/reference/make_skill.py $D --title "@<handle>"      # → montage-<handle>/ under the first $REELS_STYLES root
                                                                 # (SKILL.md + the profile)
```
Report to the user in 5–8 lines: pace, layout mix, captions, colours, sound, the 2–3 signature moves, and the skill's name. Then
the next prompt: «Смонтируй в моём стиле» with their video attached.

## B. Edit a take

**1. Prepare the take**
```bash
python3 $S/prep.py init <raw.mov> $P --lang en --vocab "ProductName, OtherName" [--script script.txt]
```
Normalizes to 1080×1920 @30, follows the face before cropping a wide source, and requires FFmpeg `zscale` for HDR→Rec.709. It gets word timings from ElevenLabs Scribe and writes `work/phrases.txt` and `work/retakes.json`. Listen to the source while
reading the phrases: choose the strongest self-contained opening, identify failed retakes and mark meaningful pauses. Verify
each person's, product's and brand's spelling against the brief/source before drawing text. `--vocab` teaches Scribe keyterms;
`--script` lays a known script over the timings. The sound offset of phone MOVs is fixed automatically.
```bash
python3 $S/prep.py cut $P --drop 12.4-15.1,40.2-41.0 --style <profile folder>
```
Cuts accidental pauses while retaining bounded sentence-ending pauses in the style's measured range. Review the pause report
and detected repeats before cutting. Use `--hold-pause 3.2-3.9` for a specific meaningful raw-source pause (up to 2 s), or
`--rhetorical-gap <seconds>` to adjust the automatic limit. Repeated attempts halt the cut until you choose `--drop` or `--keep`;
use `--keep-repeats` only for intentional repetition. The cut writes `work/clean.mp4` and numbered `work/words.txt`. Listen
to the clean cut to confirm sentence connections and meaning survived. The word number is
`w:N` in the plan. **A take full of repeated attempts:** keep only the good ranges with `cut $P --keep 0.8-9.1,11.5-20.6,...`,
then re-transcribe the clean cut with `prep.py words $P --script script.txt` (the transcriber glues repeats together, so raw timings lie).
```bash
python3 $S/prep.py voice $P --isolate
python3 $S/prep.py face $P
python3 $S/prep.py cutout $P
```
Voice clean-up (`--isolate` uses ElevenLabs Audio Isolation, then the EQ/compression chain; without the key, the chain only), face track
(`work/face.json`), person cutout (`work/clean_subject.webm`). `prep.py all <raw> $P --lang en` runs everything.

**2. Assets** go to `$P/assets/`: logos, 3D emoji, GitHub cards and site screenshots come from `fetch_assets.py` (examples in
`shot-library.md`). The product needs real screenshots and screen recordings. A real person named in the script appears only on a
real photo you may use. Build every visual fresh for this reel.

**3. Plan**
```bash
python3 $S/autoplan.py $P --cta KEYWORD --lang en --style <profile folder> [--accent "#D97757"] [--era 2025]
```
Gives `plan.draft.json`: beats cut near the measured shot length, verified transition types spread at their measured share, and `TODO` placeholders instead of graphics. Unclassified visual-change candidates retain the style's normal transition. Without
`--style` it uses the user's only profile, or stops and asks. Read the profile's `style-bible.md`,
`analysis/reference_index.md` when present, plus `beat-planning.md` and `shot-library.md`. Open only one or two indexed
`analysis/windows/*.json` files that match the current semantic slot. An unpacked profile may have only the complete
`analysis/reference_timeline.json`: extract the relevant reel/time window into a small view instead of loading that entire
file. Compare the same semantic slot at real reference
timecodes: shot length, face/title placement, word-triggered graphics, transitions and sound. Scene-score boundaries and
separated-background transients are candidates until checked in the source. Replace every `TODO` with a concrete visual,
vary the visual idea across consecutive blocks, move beat borders/layouts where needed, and save as `plan.json`.

**4. Lint the plan**
```bash
python3 $S/plan_lint.py $P [--projects ~/reels]
```
Zero errors required. Resolve the warnings about layout shares, long static beats, two faces in a row and a late first change. Dense captionless UI and sub-44 px primary UI text are errors: recompose or add readable speech captions.
With `--projects` (or `$REELS_PROJECTS`) it also fails a plan whose opening repeats one of the user's two latest reels.

**5. Build and contact sheet** (gate)
```bash
python3 $S/build.py $P
(cd $P/hf && npx -y hyperframes@0.8.78 lint .)
python3 $S/snap.py $P
```
Lint must show 0 errors (`nested_structure_needs_subcomposition` warnings are expected and harmless). `build.py` also writes `work/caption_qa.json` with timed caption containers and source hashes; these bounds are estimates, so inspect actual glyphs in snapshots. The browser rejects captions that shrink below 48 px or still overflow after fitting. `snap.py` writes one still
per beat to `work/snap_sheet.jpg`. Look at it with your image-viewing tool (Read in Claude Code, `view_image` in Codex) and
check: every beat shows what is being said; no empty zones; captions readable and off the eyes; the head sits right in the arch
with nothing floating above the hair. Inspect at 360×640 phone size: main titles, names, numbers and active controls must read
without zooming, and captions must not hide the face, hands or key proof. Fix the plan and rebuild: a
snapshot takes seconds, a render takes minutes.

**6. Render**
```bash
PRODUCER_BROWSER_GPU_MODE=hardware npx -y hyperframes@0.8.78 render $P/hf -o $P/out/picture.mp4 --fps 30 --quality looks
```
About 2–3 minutes per 30–60 s of reel on a recent Mac; run it in the background. Drop the GPU variable off macOS. If Chrome
exits at once (a sandboxed agent shell on macOS blocks it), run the render with the sandbox off or ask the user to run the
command in their terminal; `npx -y hyperframes@0.8.78 doctor` shows what is missing.

**7. Sound and delivery** (details: `references/sound-design.md`)
```bash
python3 $S/finish.py $P $P/out/picture.mp4 --name <slug>
```
The engine places sounds from the graphic events: the opening swell (or the user's own riser in `open_riser/` of their kit), a whoosh on every scene change by transition type, pops,
clicks, typing, counter rolls that lock with a click, up to three hero moments (riser, music dip, impact, sparkle). Variants
rotate, pitch and level vary slightly, the music gives up only the voice band, and each cue is measured against voice, music and other SFX from its own short stem. Buried cues are raised until they cut
through. Profile `bold` (default) keeps every cue clearly audible; `measured` reproduces the style's quiet measured levels. Output:
`out/<slug>.mp4` at −14 LUFS and a light copy `out/<slug>_light.mp4` under 20 MB. `work/sfx_used.json` records isolated audibility per cue; `work/sfx_audit.json` binds the result to the rendered files by SHA-256.

**8. Compare with the style** (gate)
```bash
python3 $S/qa.py $P
```
Compares pace, pauses, first change, layout shares, effect density and loudness with the style's targets and writes
`out/qa_sheet.jpg` (one frame per second). Look at it, then watch the newly rendered MP4 with sound from start to end. Inspect
frames just before/after every transition and at the middle of each semantic block; confirm names, captions and SFX timing
in the final mix. If a title is tiny, graphic premature, face badly cropped, pause damaging meaning or cue inaudible, fix
the edit/plan and render, finish and QA again. Passing QA is not editorial acceptance.

## Craft rules that hold in any style

Use the active profile's measured timing and visual grammar, then protect meaning and legibility:
1. **Start with the strongest complete thought** available in the take. Give the viewer a readable subject/action in the first
   3 s; align the first visual change to the profile and the sentence, not an arbitrary global cutoff.
2. **Cut on a semantic boundary**, normally at the clause/word start (`t0: "w:N"`). Keep the setup needed for a payoff and a
   pause that makes the next word land; verify the clean cut by listening.
3. **Change the visual idea when the meaning changes.** Meet the style's layout shares over the reel, but allow adjacent
   beats in the same layout when the subject moves, proof changes or a strong face performance carries it.
4. **Draw the important claims at their spoken trigger.** A brand → its correctly spelled logo on the name. A number → a
   counter on the number. A verb → a UI state change. A claim → proof: a
   screenshot, README or post. A person → their real photo you may use.
5. **Keep movement purposeful.** Use the profile's measured shot length and in-beat motion; avoid a long run of visually
   identical dark cards or rapid effects that bury the explanation.
6. **One accent colour per reel**: only benefits, numbers, highlights and the CTA keyword get it.
7. **Captions** in the style's chunk size; no caption where the word is already drawn.
8. **Sound follows the picture**: place cues on the specific action/transition and check each one in the final mix. Music
   supports the voice; do not add a whoosh to every cut merely because a cut exists.
9. **Every reel new, the style the same**: keep the grid, captions, accent discipline and sound system; change the opening, number
   treatment, backgrounds, music and custom moves each time (`references/move-bank.md`).
10. **Real interfaces, whole prompts, adult objects**: show an app the way viewers know it; a prompt types on screen in full, with
    the keyboard audible (`typing` with `dur`); an example person is made up, never a real third party without permission; objects
    are dark and premium (glow, big type, logos, mini-UIs), not cartoon 3D emoji on bright gradients.

A move the kit lacks (before/after, a slot-machine list, a logo morph) is built right in the plan as an `html` beat (example in
`shot-library.md`). Transitions are soft by default (`meta.trans: "auto"`); hard cuts are `meta.trans: "cut"`. Built-in moves:
the speaker snapping into the arch (`meta.open_zoom`), a white flash (`meta.flash_start`), glyph noise resolving into a pixel title
(`title` + `decode`), "IT'S CALLED" (`over_style: "caps"`), a warm light leak (`trans: "leak"`), a red strike through a
competitor's logo (`strike`). The 50/50 split with boxed captions is `meta.era: "2025"`. Dark app screens with typing, taps and zooms are `ui`; the "comment KEYWORD" ending (a comment box types the keyword, then an Instagram notification) is `comment`; heavy wide caps at mid-frame with the spoken line in the accent are captions `wide` (`meta.caption_face`, a style sets it in `plan_defaults`). Graphics of a `face` beat are drawn above the speaker.

## Pitfalls

- **Word indexes.** `w:N` points into `work/words.txt` of the clean cut. After re-cutting or `--words-only`, the numbers shift:
  re-check the plan.
- **Product names.** The transcriber mangles names and splits hyphenated words; pass new names with `--vocab` and check
  `work/phrases.txt` after `init`. Before `finish`, check every caption that shows a name against the list you were given:
  Scribe can swap in a similar-sounding wrong one (e.g. one AI model or tool name for another) even after `--vocab`.
- **Wide shots.** If the face is under ~300 px wide in the take, the close-up hits `face_scale_max` (2.2) and gets soft. Ask for
  takes where the face is about 40 % of the frame width.
- **Long numbers.** Numbers longer than 6 digits read better with `font: "serif"` (blur-in) than as a rolling odometer.
- **HyperFrames rules.** No video inside an element with `data-start`; animate only through `tl`; local fonts only. More in
  `engine-notes.md`.
- **Scores are not approval.** Script, lint and model scores are checks, not a verdict: the user judges the reel.

## Other languages

Every bundled font has Cyrillic except Instrument Serif. For Russian the engine sets the big italic caps to Noto Serif Display
(Playfair's italic Cyrillic "Т" reads like an apostrophe). Captions are cut by characters (16–20 per chunk). Keep product names in
Latin script. The CTA keeps its form (face close, italic connector, keyword in the accent) with the creator's own words; set the
keyword with `--cta` / `meta.cta_word`.

## Files

```
SKILL.md · README.md · ASSETS.md · LICENSE · THIRD_PARTY_NOTICES.md · requirements.txt
references/  shot-library · beat-planning · plan-format · engine-notes · move-bank · sound-design · sound-research
             style-profiles · beat-sheet-prompt
styles/      _defaults/style.json (engine fallback numbers) · _template/style-bible.md (skeleton)
examples/    plan.json (a fictional reel) · README.md
scripts/     prep · autoplan · plan_lint · build · snap · finish · qa · selftest · fetch_assets · sfx_gen · sfx_synth · common · _env (.py)
             face_track(.swift) · person_mask(.swift)
             reference/ fetch_reels · analyze_reference · make_skill · sfx_probe · sfx_extract · sfx_classify (.py)
assets/      base.css · runtime.js · fonts/ (+ LICENSES/) · vendor/gsap.min.js · sfx/<class>/ · music/
```
