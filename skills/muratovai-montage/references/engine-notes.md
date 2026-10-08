# Engine notes: HyperFrames, and what we took from procedural-film

## Why HyperFrames

A composition is plain HTML. Time is set by the `data-start` / `data-duration` attributes, and all animation is one paused GSAP timeline (`window.__timelines["main"]`). Headless Chrome renders it frame by frame, deterministically: the same HTML gives the same video. So a script can generate the edit from the plan, and any frame can be checked before the render (`snap.py`, which calls `npx hyperframes snapshot`). The contract is in the HyperFrames docs (and in the `hyperframes-core` / `hyperframes-cli` skills, if you have them installed).

How `hf/index.html`, written by `build.py`, is layered:

| layer (bottom to top) | what | how it changes |
|---|---|---|
| `#bg` | the beat's background colour | `tl.set('#bg',{backgroundColor})` at the start of the beat |
| b-roll media | `<video>` elements of full-frame inserts | their own `data-start/duration/media-start` |
| `#gfx` | one section per beat (`class="clip beat"`, `data-start`, `data-duration`) with its graphic | lives exactly for its own time; animations inside are GSAP tweens |
| `#plate` | the whole head, `media/clean.mp4` | in split it is clipped by the arch (`clip-path: inset(1212px 18px 0 18px round 195px 195px 0 0)`), in face it is uncropped, in graphic it is at `opacity:0` |
| `#cut` | the cut-out person `media/clean_subject.webm` (VP9 with alpha), with the same transform | visible only in split; a gradient mask from the top (starting at a line above the hair) keeps anything above the hair from showing through |
| `#caps` | caption phrases, one section per chunk of 1–3 words | appear in 70 ms (scale .94 → 1) |

The head moves only through the wrappers `#plate-inner` / `#cut-inner` (`x`, `y`, `scale`, `transform-origin: 0 0`). Never animate the `<video>` elements themselves: that is a HyperFrames rule (the framework owns clip visibility). Both video tracks start at 0 with `data-media-start="0"`; otherwise the cut-out lags one frame behind.

Framing comes from the face track (2 samples per second): the median within each beat. On macOS the track uses Apple Vision; elsewhere it uses OpenCV (`pip install "opencv-python-headless<5"`: OpenCV 5 dropped the Haar face cascades), and with neither it falls back to a centred estimate (`prep.py face --engine center`). After OpenCV or the estimate, check the head framing on the `snap.py` contact sheet.
The fallback targets (face box width / eye height / centre x, in px at 1080×1920) are in `styles/_defaults/style.json` → `framing`; a style profile overrides them with the framing measured on the creator you analyzed.

| layout | face width | eyes y | centre x |
|---|---|---|---|
| split | 418 | 1337 | 549 |
| face close | 754 | 732 | 541 |
| face medium | 600 | 800 | 540 |

If the source is shot wide (the face is narrower than 300 px), upscaling stops at `face_scale_max` (2.2; `split_scale_max` is 1.8), because beyond that the picture goes soft. Better: ask the speaker to shoot closer (face ≈40 % of the frame width).

## HyperFrames pitfalls we have already hit

- `npx hyperframes lint` warns `nested_structure_needs_subcomposition` on every beat section. It is a warning about Studio convenience and does not affect the render. There must be no errors.
- Fonts come only from `@font-face` rules that point at local files (`assets/fonts/fonts.css`). Otherwise lint fails and the render falls back to a system font.
- A `<video data-start>` must not sit inside another element with `data-start` (error `video_nested_in_timed_element`). That is why video inserts live in a layer of their own, not inside the beat section.
- Change `className` with `tl.set(el,{className:…})`; never tween `display/visibility/autoAlpha` on clips.
- Build the timeline after `document.fonts.ready`; otherwise `fit()` measures text in a system font.
- Render with `npx hyperframes render <project>/hf -o <project>/out/picture.mp4 --fps 30 --quality looks`. On macOS, prefix it with `PRODUCER_BROWSER_GPU_MODE=hardware`: software rendering can time out on laptops. A 54 s reel takes ≈3 min.
- Recent ffmpeg builds dropped `-filter_complex_script`. ffmpeg ≥ 7 reads a long filter graph from a file with `-/filter_complex <file>`; `finish.py` relies on this.

## Person cut-out

On macOS 12+, `prep.py cutout` uses Apple Vision by default: `VNGeneratePersonSegmentationRequest` at `.accurate`, ≈20 frames/s on an Apple-silicon Mac (a 31 s take: under a minute). The mask is merged with the video into VP9 + alpha (`alphamerge`, `yuva420p`). The Vision helpers ship as prebuilt arm64 binaries, `scripts/person_mask` and `scripts/face_track`. When they don't run, `prep.py` rebuilds them from the `.swift` sources with `swiftc` and saves the local build as `<name>.local`, next to the shipped binary.
Elsewhere the cut-out uses `--engine u2net`, which runs `npx hyperframes remove-background` (a local model, any OS). In tests on a bright background (a window), it left a bright blob above the hair; Apple Vision did not.

## What we took from procedural-film (github.com/kuhnhomeuk-cell/procedural-film)

procedural-film is a skill for 30-second animated films where JS draws every pixel on a canvas. We don't use its graphics (we have a live person and interfaces), but we took its **production discipline** whole:

| procedural-film | here |
|---|---|
| `reference-analysis.md`: go through the reference frame by frame, take notes, finish with numbered style rules | `scripts/reference/analyze_reference.py` + a beat sheet per analyzed reel in `<profile>/analysis/`; the rules are in `<profile>/style-bible.md` |
| art bible: the house style is fixed, only the subject's palette changes | design tokens in `assets/base.css`; per reel only `accent` changes |
| storyboard: shots of 1–3 s, boundaries on a grid, every number checked against the tables | `plan.json`: beats of 0.5–4 s, boundaries on words (`w:N`); `plan_lint.py` checks layout shares and pace against the style profile |
| `timeline.js` is the single source of truth; the tools don't change from film to film | `plan.json` → `build.py`; one engine for every reel |
| stub pass: run placeholders through the whole pipeline before drawing any scene | `build.py` + `snap.py` (one still per beat) first, the render after |
| the `check.cjs` gate (6 checks, exit 0) | `plan_lint.py` before the build, `npx hyperframes lint` after it, `qa.py` after the render |
| contact sheets and "critics" measure geometry in pixels, not by eye | `snap.py` → a contact sheet; framing is calibrated on measurements of the analyzed reels' frames (`style.json` → `framing`) |
| sound events on the grid, onsets ≤ 10 ms from the cuts | effects are generated from the graphic events (`work/timeline.json`); the music bed is mixed relative to the speech level |
| delivery: a master + a light copy + a shot list | `finish.py`: the master + `_light` (< 20 MB); `qa.py` writes a contact sheet |

## Modes and signature moves in the engine

- **2025 mode** (`meta.era: "2025"`). The split is a straight seam at 973 px (0.507 H): `#plate` is clipped with `inset(973px 0 0 0)`, the cut-out `#cut` is off, and the head never shows above the seam. Framing uses `FRAME["split25"]` (eyes at 1210 px) and `FRAME["close25"]` (eyes at 672 px). Captions: `cap-box` (a grey box, `rgba(88,88,88,.63)`, at 0.68 H), `cap-box seam` (on the seam), `cap-face25` (no box, at 0.78 H). Sound: the bed at −12 dB, up to 12 effects per 10 s, and with hard cuts a soft whoosh on every third beat.
- **Arch snap-in** (`meta.open_zoom`). The first beat must be split. For it the engine sets no `tl.set` on the clip and the transform; it runs one `fromTo` from a close-up to the arch in 0.2 s. Otherwise a `set` at the same moment wins when seeking to zero, and the first frame already shows the finished arch.
- **Character noise** (`title` with `decode`). `decode()` in `assets/runtime.js` depends only on the tween's progress: each glyph is picked from the letter index and the frame number. So the frame-by-frame render is deterministic, and a snapshot at any moment matches the render.
- **Pixel fonts.** `block` is Press Start 2P: a crisp Latin "C" and Cyrillic "С", Cyrillic included. `pixel` is Pixelify Sans: softer, but its "C" looks like an "O". For "Claude Code", use `block`.
- **Punch zoom** (`meta.open_punch`) scales the `#gfx`, `#plate` and `#cut` layers in from 1.12× with a blur over 0.25 s.

## Scene transitions (`meta.trans`, a beat's `trans`)

- `auto` (the default) picks the transition from the pair of layouts:
  - split ↔ face: `punch`, a push-in or pull-out;
  - the same layout: `zoom`;
  - anything else: `fade`.
- **`fade`.** The outgoing beat's section lives 0.2 s longer (`data-duration` + 0.2); its `.zone` fades out while the new `.zone` resolves from a blur. The `#bg` colour blends across. The head fades in or out through `opacity` on `#plate` and `#cut`. Tween `opacity` only on the `.zone` inside a section, never on the section itself: clip visibility belongs to HyperFrames.
- **`punch`.** One `fromTo` moves the `#plate-inner` / `#cut-inner` transform from the old framing to the new one in 0.2 s; the arch `clipPath` opens or closes in 0.12 s; `#plate` gets a short 6 px blur. The background is set at once; otherwise a grey band flashes for 2–3 frames. The push-in on the face starts after the transition.
- **`zoom`.** The outgoing `.zone` grows to 1.08 and fades; the new one grows from 0.9 out of a blur.
- **Also per beat:** `flash` (a white flash that fades out over 0.14 s), `blur` (the frame resolves from a 14 px blur at 1.06× in 0.24 s), `leak` (a warm light leak that peaks on the cut and fades over 0.42 s).
- **The transition sound** comes from `build.py`: `punch` gets `whoosh_low`, `zoom` gets `whoosh_soft`, pages and posts (`shot`, `tweet`, `broll`) get `swipe`, any other layout change gets `whoosh`. `finish.py` puts the whoosh peak 0.12 s after its event, just after the cut.
- `trans: "cut"` on a beat, or `meta.trans: "cut"` for the whole reel, gives hard cuts, with no sound on the cut.

## Custom graphics pitfalls (`html`)

- **A `fromTo` whose from-state is visible and which starts after the beat begins draws that from-state right away by default.** Example: a gift box with `{y:-760, opacity:1}` as its from-state hung in frame before its drop, and a `flash` transition washed everything white until the cut. Rule: make the from-state invisible (`opacity:0` or `scale:0`), or add `immediateRender:false` to `to`. The engine already does this for `flash` and `blur`.
- **A `fromTo` changes only what `to` names.** A property that appears only in `from` (`attr:{opacity:1}`, `transformOrigin`) is ignored. In one custom opening this left a punching arm invisible, and the fist flew apart from the body. Repeat such properties in `to`. When one element has several `fromTo`s, give every later one `immediateRender:false`:
  ```js
  tl.fromTo('#{p}arm', {attr:{opacity:0}, rotation:-40, transformOrigin:'20% 50%'},
                       {attr:{opacity:1}, rotation:0, transformOrigin:'20% 50%', duration:0.12}, {t:w:12});
  tl.fromTo('#{p}arm', {rotation:0}, {rotation:-40, transformOrigin:'20% 50%', duration:0.2, immediateRender:false}, {t:+1.4});
  ```
- **A match cut on an object between two graphic beats.** The object in the next beat sits at the same point and size as at the end of the previous one. Account for the push-in on the beat root: at scale 1.05 around the origin (ox, oy), a coordinate x becomes ox + (x − ox)·1.05. Let the previous beat's animation settle before the cut: a 0.5 s `bounce.out` was still bouncing 50 px. Use `trans:"cut"` and put the whoosh in the beat's `sfx`, because `cut` places no sound.
- For 3D, put `perspective` on the beat root and `rotationX`/`rotationY` on the card. A laptop lid closes with `rotationX: -86` around its bottom edge (`transform-origin: 50% 100%`).
- Build a pixel-art character as inline SVG with a group per part (body, arms, legs) and `shape-rendering: crispEdges`. It stays sharp when scaled up, and the arms and legs move independently.
