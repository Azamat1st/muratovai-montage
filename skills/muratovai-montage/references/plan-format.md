# plan.json — the edit plan format

A plan describes the reel as a sequence of **beats**. A beat is a stretch of time with one layout and one main graphic. Beats sit
back to back: the `t0` of the next beat is the end of the current one; the last beat ends at the end of `work/clean.mp4`.
Everything else (captions, sound events, head framing) `build.py` derives on its own.

## meta

| key | what | default |
|---|---|---|
| `title` | project name | folder name |
| `style` | style profile: the path of your own profile folder (see `style-profiles.md`; a `montage-<handle>` skill folder works too). Sets the targets of `plan_lint.py` and `qa.py`, the framing and the `measured` sound levels; fields the profile lacks come from the neutral fallback numbers in `styles/_defaults/style.json` | `_defaults` (fallback numbers only, not a style) |
| `profile` | sound profile. `bold`: clearly audible effects (whoosh/pop 4–6 dB under the voice), music ≈15 dB under the voice, up to 12 cues per 10 s, soft transitions. `measured`: the style's quiet measured levels (fallback: music ≈28 dB under, ≤5 cues per 10 s) | `bold` |
| `trans` | how scenes change: `auto` (punch-in/out to the face, dissolve between graphics, zoom between two graphics), `fade`, `cut` (hard cuts, silent) | `auto` |
| `open_sfx` | the opening "fade" sound. `riser`: the first riser in your kit's `open_riser/` class, sped up 1.2×, its hard stop landing on the first scene change with a sub hit, the music opening on the cut; the bundled kit has no riser, so without your own one this falls back to the swell. `swell`: the synthesised sub swell. A path to your own riser wav works too. `false`: no opening sound | `riser` (`bold`), `swell` (`measured`) |
| `open_rate` | speed-up of an opening riser (pitch rises with it, like a sampler) | `1.2` |
| `caps_font` | font of the big italic caps | `'Noto Serif Display'` for ru, `'Playfair Display'` otherwise |
| `caption_face` | the caption style of every `face` beat that sets none: `wide` = heavy wide caps (Unbounded 900) in two lines at mid-frame (y≈0.5), the line being spoken in the accent with a glow, a lone bridge word (BUT / NOW / INSTEAD) big and alone; a style profile sets it in `plan_defaults` | the layout default |
| `era` | `2026`: arch split with the head popping out, three caption styles. `2025`: 50/50 split with a straight seam, white bold captions in a grey box, face only in the hook and CTA, louder music, up to 12 effects per 10 s. Do not use `caption_style: "mix"` in 2025 mode | `2026` (or the style's `plan_defaults.era`) |
| `open_punch` | punch-in at the start: the whole frame lands from 1.12× with a blur over 0.25 s | `false` |
| `lang` | caption language: `en`, `ru`, … (every bundled font has Cyrillic except Instrument Serif) | `en` |
| `accent` | the colour of the product the reel is about (Claude `#D97757`, OpenAI `#10A37F`, Google `#4285F4` …). One per reel | style's `plan_defaults.accent`, else `#D97757` |
| `accent_face` | colour of the keyword on the face when `accent` is dark or unreadable over video | `accent`, or `#ffd84d` when `accent` is dark |
| `music` | bundled: `tense_a` … `tense_d` (dark tense electronic beds; rotate them between reels), `ambient_tech_90`, `lofi_keys_84`; or a path to your own mp3/wav | the style's `plan_defaults.music`, else `tense_a` |
| `music_rel_db` | music level vs the speech level, dB | from `profile` |
| `sfx_offset_db` | shift of every SFX level, dB | `0` |
| `sfx_cut_offset_s` | scene SFX offset from each cut in seconds; use after listening to the reference. Unclassified background-stem peaks do not set this automatically | `-0.04` |
| `sfx_per_10s` | how many effects per 10 s to keep at most | `12` (`bold`), the style's median (`measured`) |
| `sfx_dir` | your own SFX kit folder (`<class>/<class>_a.wav` …), searched before `$REELS_SFX_DIR` and the bundled kit | — |
| `cta_word` | the CTA keyword ("NOVA", "KEY"); gets the accent on the last beat | — |
| `lead` | how early logos/hub nodes appear before their word, s | `0.3` |
| `face_scale_max`, `split_scale_max` | upscale limits for the head | `2.2`, `1.8` |
| `flash_start` | white exposure flash over the first 0.12 s | `false` |
| `open_zoom` | the speaker starts as a full-frame close-up and snaps into the arch in 0.2 s with motion blur. The first beat must be a split | `false` |
| `leaks` | warm light leak on every entry into the face after a split or graphic. Usually better set per beat with `trans` | `false` |
| `carve` | the music gives up only the voice band (250 Hz–4 kHz) while the speaker talks | `true` |

## A beat

```json
{"t0": "w:12", "layout": "split", "bg": "white", "gfx": {...}, "caption": "auto", "caption_style": "mix", "emph": ["free"], "zoom": "close", "cta": false}
```

| key | values |
|---|---|
| `t0` | start time: seconds · `"w:12"` = start of word 12 of `work/words.txt` minus 0.05 s · `"w:12+0.2"` · the first beat is always 0 |
| `layout` | `split` — graphic on top, head in an arch below, the hair crossing the arch edge · `face` — the face full-frame, close · `graphic` — graphic only, no head · `broll` — full-frame image/video over its own blurred copy |
| `bg` | `white` `#fdfdfd` · `gray` `#f1f1ef` · `paper` `#ece5d8` · `cream` · `dark` `#16171b` · `black` · `accent` · any hex. `face` has no background |
| `gfx` | the beat's main graphic (below). `face` usually has none |
| `caption` | `auto` (captions from the speech) or `none` (when the words are already drawn: counter, "it's called X" title, logo stack with labels) |
| `caption_style` | defaults by layout: split → bold sans 72 px above the head; face → white bold sans on the chest; graphic/broll → heavy italic serif caps 128 px in the lower third. `mix` — italic serif connector above a bold sans keyword (face, emotional lines, CTA). In `era: 2025`: `box_seam`, `box`, `face25` · `wide`: heavy wide caps in two lines at mid-frame (see `meta.caption_face`) |
| `emph` | words of this beat painted in the accent (on the face: a white → accent gradient) |
| `cap_accent` | the accent of this beat's `wide` captions (the meaning colour: red for a mistake, green for "free"), `#RRGGBB` only | `accent` |
| `zoom` | for `face`: `close` (face ≈70 % of the width) or `medium` |
| `cta` | `true` on the last beat: mix captions + `meta.cta_word` in the accent, held to the last frame |
| `trans` | the entry into this beat, overriding `meta.trans`: `fade`, `zoom`, `punch`, `cut`, `blur` (the whole frame), `flash` (white flash), `leak` (warm light leak 0.16 s before the cut and 0.42 s after it, with a soft whoosh: on the entry into a face, on a join between takes, on a new section) |
| `qa_intent` | explicit editorial exception for an intentionally dark or static beat, e.g. `{ "dark_ok": true, "static_ok": true, "reason": "Held white title on black before the reveal" }`. This marks timed QA findings for human review; it never accepts a broken render automatically |

Times inside a graphic accept `"w:N"`, `"+0.4"` (from the beat start) or `"word:Gemini"` (the first such word inside the beat).
Keys that start with `_` (like `_note` in `examples/plan.json`) are ignored by the engine: use them for your own notes.
`build.py` keeps measured caption position/word chunk size, title bounds and tagged title motion, shot framing, and verified SFX timing from the style profile. Unclassified reference transitions remain the default rather than being extrapolated into a dominant effect. It writes `work/timeline.json` (including explicit `qa_intent` as `visual_intent`) and `work/caption_qa.json` for checks of the actual render. Caption boxes in that manifest are container estimates, not measured glyph bounds; inspect the rendered text. The browser rejects caption text below 48 px or still overflowing after fitting. A UI beat whose meaning relies on its fixed 28–46 px labels needs speech captions or a larger focal composition; `plan_lint.py` rejects captionless small UI and primary UI text under 44 px.
In custom HTML, label invented screens and author opinions as illustrations. Keep that disclosure at least 44 px on the 1080 px canvas and above the bottom 300 px reserved for app controls; `plan_lint.py` checks these labels. Inspect the rendered result because a label can still overlap other graphics.

## Graphics (`gfx.type`)

| type | when (trigger in the speech) | parameters |
|---|---|---|
| `logo` | one brand/product is named; a competitor you "no longer need" | `src`, `label`, `size` (300), `plain` (no tile, for emoji/wordmarks), `t`, `strike` (time of the red strike-through, e.g. `"w:9"`) |
| `logos` | a list of brands/things: the big current one + a growing row of small ones | `items:[{src,label,t}]`, `size`, `lead` |
| `hub` | "connects to…", "links X to Y", an ecosystem | `center`, `nodes:[{src,label,t}]`, `radius`, `center_size`, `node_size` |
| `counter` | any number | `text` ("600+", "7 BILLION", "$0.32"), `label` (unit), `over` (italic line above), `font` (`sans` = rolling digits; `serif` = blur-in), `size`, `t`, `label_t`, `color`, `dur` (0.7), `roll: false` (blur-in without rolling), `bg_src` (source image under the number, blurred, darkened, drifting), `label_style: "serif"` + `label_size` (unit in big accent italic) |
| `title` | "it's called X", a list ordinal ("THE SECOND"), a loud claim, a product name | `text`, `font` (`caps` italic serif caps · `heavy` heavy italic serif, not caps, 2025 headlines · `block` big pixel Press Start 2P, reads well in Latin and Cyrillic · `pixel` soft pixel Pixelify: "C"/"С" look like "O", avoid for names with C · `sans` · `serif` · `wide`), `decode: true` (letters run through accent glyph noise and resolve left to right; `decode_dur` up to 0.7 s, never longer than half of the rest of the beat), `over` + `over_style: "caps"` (the signature "IT'S CALLED": italic serif caps, accent → pale gradient, zooms in from blur, soft whoosh), `over_size`, `over_color`, `over_t`, `text_t`, `icon` + `icon_size` + `icon_t`, `sub` + `sub_t`, `sub_font` (`block` / `pixel`), `sub_size`, `sub_color`, `sub_type: true` (types at ≈18 chars/s, `cps`), `highlight:[phrases]` (accent marker), `gradient: true`, `type_on`, `size`, `color` |
| `widget` | "run / generate / install": a mini product UI | `icon`, `name`, `status`, `progress:[from,to]` |
| `terminal` | commands, prompts, a coding agent, logs | `title`, `lines:[{text,t,prompt,color}]` (the first line types itself), `font_size`, `width` |
| `shot` | a site, page, README, document, UI screenshot | `src`, `crop:[x,y,w,h]`, `width`, `chrome` + `url` (browser frame), `box:[x,y,w,h]` + `box_t` (accent frame), `zoom` + `zoom_t` (push into the frame), `drift` |
| `broll` | generations, video results, "look what it made" | `src` (image or video), `media_start` |
| `person` | a real person is named (author, founder) | `src` (a real photo you may use), `name`, `role`, `over`, `w`, `h` |
| `note` | "leaves a note", passing context | `logo`, `title`, `lines`, `tag`, `note_t` |
| `meter` | a limit, "tokens run out", overload | `label`, `to` (0–1), `icon`, `dur` |
| `switcher` | "switches to the next model", picking from options | `cards:[{src,label}]`, `seq:[{t,index,status}]`, `status` |
| `chart` | growth/decline, "50 % less", a comparison | `bars:[numbers]`, `label`, `label_t` |
| `emoji` | an emotion/metaphor without a product (rocket, money, clock) | `src` (Fluent 3D), `size` |
| `tweet` | a quoted post from X | `name`, `handle`, `avatar`, `text`, `highlight`, `meta` |
| `ui` | a dark app screen: "open the app / search / tap / turn on / look at the stats"; every spoken action is acted out on it | `items:[{kind,…}]` (below), `title` (top bar), `taps:[{at,t,x,y}]` (a white ring presses item `at` at `t`; `x`/`y` 0–1 inside the item; a `button` fills with the accent), `focus:[{at,t,zoom,dim}]` (the other items dim to `dim` 0.25, item `at` gets an accent outline, `zoom` > 1 pushes the screen onto it; `at: null` clears). On a `face` beat the screen is a dark glass card over the chest, centred at `y` (0.54) |
| `comment` | the CTA "comment KEYWORD": a comment box over the speaker types the keyword so it ends on the spoken keyword, then an Instagram notification delivers the reward | `word` (default `meta.cta_word`), `done` (when typing ends; default the keyword's own time), `notify` (default 0.55 s after), `message`, `sender`, `app` (Instagram), `placeholder`, `y` (0.49). Only on a `face` beat (the build stops otherwise), best the last one, with `caption: "none"`. A beat that ends less than 0.3 s after the notification gets a warning |
| `html` | the kit lacks the move: before/after, a slot-machine list, a morph, a custom mini panel | `html` (markup), `js` (GSAP lines for `tl`), `sfx:[{t,kind,db}]`. Tokens: `{p}` id prefix of the beat, `{t:w:12}` / `{t:+0.4}` / `{t:word:X}` seconds, `{img:assets/x.png}` staged path, `{accent}` colour. Example in `shot-library.md` |
| `none` | only the big caption on a background | — |

`ui` items (`kind`): `search` (`text`, `done`: typing ends on this time, or `t`: typing starts) · `row` (`title`, `sub`, `right` badge, `avatar` or `color`, `mark`: `win` green check / `lose` red cross on the right, `mark_t`: pops in at this time with a chime / error sound) ·
`profile` (`name`, `handle`, `avatar`, `stats:[["198","posts"],…]`, `bio:[lines]`, `link`) · `stat` (`value`, `label`, `t`: hidden until it rolls up at `t`, `size`, `color`) ·
`ring` (`value` 0–1, `text`, `label`, `t`: draws at `t`, `size`, `color`) · `toggle` (`label`, `on`: flips green at this time) · `button` (`label`, `color`) ·
`text` (`text`, `size`, `color`, `align`) · `grid` (`n`, `views:["12K",…]`, `srcs:[images]`). Any item takes `show` (pops in at that time). Graphics of a
`face` beat are drawn above the speaker.

`widget`, `note` and `switcher` are sized for the top zone of a split. On a full-frame graphic the engine scales them by 1.35, 1.3
and 1.12. `scale: 1.2` sets your own factor, `scale: false` turns it off.

Sounds for your own graphics (`html` → `sfx:[{t, kind}]`): `pop`, `click`, `tick`, `swipe`, `glitch`, `chime`, `ding`, `error`,
`impact`, `punch`, `shatter`, `whoosh`, `whoosh_soft`, `whoosh_low`, `typing`, `count`, and `hero` — a hero moment: riser, music
dip, impact, sparkle (at most three per reel). `tap`, `toggle`, `send`, `shutter`, `blip`, `reveal` work too; without your own
kit they borrow a related bundled sound (see `sound-design.md`).

All image paths are relative to the project folder (`assets/...`) or to the skill's `assets/` folder. Real people only on real
photos you may use.

## Example (the first beats of `examples/plan.json`)

```json
{"meta": {"lang": "en", "style": "_defaults", "profile": "bold", "accent": "#E551BA", "music": "ambient_tech_90", "flash_start": true},
 "beats": [
  {"t0": 0, "layout": "split", "bg": "white", "gfx": {"type": "title", "font": "block", "text": "NEW AI MODEL", "decode": true, "icon": "assets/icon_openai_com.png", "icon_size": 190, "size": 84}},
  {"t0": "w:5", "layout": "split", "bg": "white", "gfx": {"type": "logo", "src": "assets/icon_openai_com.png", "label": "OpenAI", "size": 280}},
  {"t0": "w:8", "layout": "graphic", "bg": "dark", "gfx": {"type": "shot", "src": "assets/shot_example.png", "crop": [0, 80, 1080, 900], "width": 900}},
  {"t0": "w:14", "layout": "graphic", "bg": "white", "caption": "none", "gfx": {"type": "counter", "text": "200×", "label": "times faster", "font": "serif", "size": 300, "t": "w:15"}},
  {"t0": "w:22", "layout": "face", "caption_style": "mix", "emph": ["free"]}
 ]}
```
The whole plan (27 beats, each with a `_note` on why it looks the way it does): `examples/plan.json`.
