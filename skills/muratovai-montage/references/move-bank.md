# Move bank: every reel new, same style

Viewers remember openings and signature moves. When two reels in a row open the same way or reuse the same graphics, the second one feels like a copy. Keep the style fixed and rotate the moves.

## What always stays (the style)
- The layout grid: the arch split, the face, the full-frame graphic. Shares and pace follow the active style profile (`<profile>/style-bible.md`).
- Captions of 1–3 words, the engine's fonts, one accent colour per reel: the product's brand colour, or a fixed channel colour if you want every reel to share it.
- The sound system: an opening swell, a whoosh on every scene change, clearly audible pops and clicks, −14 LUFS (profile `bold`; `measured` keeps your style profile's quiet levels).
- A CTA with a keyword and a face close-up at the end.

## Depth is mandatory

Flat mock-ups (notifications, receipts, bar charts, toggles on a light background with thin shadows) read as a slide deck, not as an edit. This is what gives a frame depth:
- **Real proof over drawn mock-ups.** An X post, a docs page, a ranking article. The sharp card lies over its own blurred, darkened copy (`filter: blur(30px) brightness(.32)`, scaled 1.1).
- **A heavy card shadow:** `box-shadow: 0 60px 120px rgba(0,0,0,.6), 0 18px 40px rgba(0,0,0,.35)`. Emoji and logos get a `drop-shadow`; the main object gets an accent glow behind it.
- **Motion through the whole beat:** push the beat root in from 1 to 1.05–1.14 over the full duration; bring the card in with a 3D turn (`rotationX`/`rotationY` 16–28° → 0 with `perspective: 1600px`); sweep a highlighter over the key phrase on its word.
- **Dark saturated backgrounds:** near-black, deep blue, a radial glow. Keep plain white for rare accents.
- **Three layers:** the background (blur or glow), the middle (the card), the foreground (emoji, a medal, a character with a shadow on the floor).
- **Action scenes:** a punch, cracks, shards, a shockwave, camera shake, sparks. Example: an opening where a pixel mascot punches a competitor's logo, which cracks and shatters. How to build a punch that reads:
  - two jumping punches, each with a wind-up: a crouch and a squint;
  - on contact, a 2–3 frame freeze, a white star flash, the logo recoils and springs back, the camera shakes;
  - the cracks grow in stages: half of them after the first punch, all of them after the second; the logo glows hot;
  - the second punch lands exactly on the cut where the logo shatters;
  - sound: `punch`; then, on the cut, the hard stop of the opening riser (`meta.open_sfx`, with a riser in your own kit), a sub hit, `shatter` and the second `punch`.

`plan_lint.py` warns about a flat frame: a custom graphic with no shadow and no blur.

## What changes in every reel (novelty)
Before you plan, open your two most recent plans. `plan_lint.py` compares with them itself when it knows where your projects live: pass `--projects <dir>` or set `$REELS_PROJECTS` (it takes the two newest `plan.json` files up to 4 folders deep; with neither set, the check is skipped). In every slot below, take a move that neither of the last two reels used. Aim for at least one move that has never been used before, and add it to this table.

| slot | moves |
|---|---|
| **opening camera move** | `open_zoom` arch snap-in · `open_punch` punch zoom · `flash_start` flash · no camera move, but graphics moving from the first frame |
| **first frame, graphic** | this reel's own editing timeline assembling itself: video, graphics, captions, music and SFX tracks, clips flying in and snapping (`html`) · a pixel title with `decode` + a logo on dark · a stack of notifications on warm paper (flat: add depth or skip it) · a fight: a character punches a competitor's logo, which cracks and shatters · the tool author's tweet or post (`tweet`) · a terminal window typing a command (`terminal`) · a browser with an address bar and a loading page · a phone in a hand with a screenshot · a Google search with suggestions · a GitHub card whose stars climb (`shot` + `counter`) |
| **the key number** | a serif number rising on white (`counter`, `font: "serif"`) · a gift box that shakes and bursts into confetti on an accent background · an odometer (`counter`) · a receipt or banknote that prints out · an airport split-flap board · a number built from falling coins |
| **price and payoff** | plan and coupon cards · a receipt with a "GIFT" stamp (flat) · the vendor's real post with the amount highlighted, a 3D entrance and a price tag with a shadow · a price tag struck through in red · two baskets, "before / after" · a calculator doing the sum |
| **multiplier "N times"** | a serif "×5" (`counter`, `font: "serif"`) · "before / after" bars (`chart`) · N copies of an icon lining up · scales tipping over · a speedometer |
| **feature name** | italic caps with "it's called" (`title`, `over_style: "caps"`) · a UI toggle, Local → Cloud · the name typed into a search field · a sign lighting up · a card flipping over |
| **mechanism** | a desktop app's input box: links pasted in, the prompt typing in full, the resulting files appearing (`html`) · the `/model` menu with the selection moving (`html`) · a logo relay and a hub (`logos`, `hub`) · a tile moving from a laptop to a server · a dotted path to server racks with blinking lights · a three-block diagram with arrows · a conveyor belt carrying tasks |
| **proof, the model** | crops of the real GitHub page + a big stars plate · a creator's profile grid with covers and view counts (a made-up example creator) · an analysis dashboard of 4 cards with measured numbers (`html`) · a pixel title with the model's name (`title`, `font: "pixel"`) · a ranking mock-up (flat) · a real ranking article with the key phrase highlighted over its blurred copy + a 3D medal · a benchmark chart where one bar grows (`chart`) · a screenshot of the official post (`shot`, `tweet`) · an expert quote with a photo (`tweet`) |
| **"made with this"** | a 3D carousel of your own finished reels · the real waveform of the take: pauses and retakes collapse and the duration shrinks (`html`) · an editing timeline of coloured clips · a film strip of real frames from this very reel · before and after in one frame · a time-lapse of the result (`broll`) |
| **comparison** | two cards, ✓ / ✗ · "VS" with icons sliding together · a table with ticks · a scale with one end lit up |
| **CTA** | the face with the keyword in a gradient (built in) · a comment field where the keyword types in, then the send button · a DM with a reply link · an arrow down to the comments |
| **background** | `white` / `gray` / `dark` · `paper` / `accent` / `black` · `cream` · an accent gradient |
| **music** | bundled dark tense beds `tense_a` → `tense_b` → `tense_c` → `tense_d` (rotate them, reel by reel) · `ambient_tech_90`, `lofi_keys_84` for a calmer topic · your own tracks (`meta.music` takes a path) |
| **transitions** | `auto` (the default) · `flash` on the key number · `leak` on the way into the face · `blur` on the way into a dashboard · `cut` for rhythm |

Moves shown without a component or parameter are custom `html` graphics (see `shot-library.md`).

## How to use it
1. Before you plan, write down which moves your last two reels used. Pick a different one for each slot.
2. Build custom graphics with the `html` type: `shot-library.md` has the syntax and an example, `engine-notes.md` the GSAP pitfalls.
3. `plan_lint.py` fails with an error when the first beat repeats one of the last two reels one to one. It warns when the opening move, the music, or 40 % or more of the graphic beats match the latest reel.
4. After the reel, add any new moves to the table.

`plan_lint.py` only catches repeats; it does not judge a reel. The human editor is the final judge.

## Interfaces, prompts, example people

- **Show an app the way the viewer knows it.** For Claude that is the desktop app (Code tab, dark theme): a sidebar with "+ New", a
  "Welcome back" greeting, the input box "Describe a task or ask a question" with chips, a model pill and the pixel mascot at its
  edge. A terminal only when the reel is about the CLI.
- **The prompt is the instruction, so it types in full**: wrapping lines, synced with the speech, links visible whole. Use normal
  spaces in typed text (not `&nbsp;`), or it will not wrap. Give its `typing` cue a `dur` (see `sound-design.md` §8).
- **No real third party unless the user asks for one.** An example creator is a made-up profile (e.g. `ai.blogger`) with covers
  built for the reel.
- **Adult, premium objects.** Covers and objects in the edit's style: a dark background, an accent glow, big type (Inter 900 with
  an italic serif accent word), logos and mini-UIs (a chat, a terminal, a timeline). Cartoon 3D emoji (robot, rocket, light bulb)
  on bright gradients read as childish.
- **A match cut on an object**: when a beat ends on an object that the next beat starts with, start the next beat's object at the
  settled position of the previous one and cut (`trans: "cut"`), so nothing double-exposes in a dissolve.
