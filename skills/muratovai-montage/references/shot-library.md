# Shot library: what to show on which phrase

The main law: everything that is said is shown. A brand gets its logo, a number gets a counter, a verb changes the state of an interface, a claim gets a proof.
The table maps a spoken trigger to a move and to the `plan.json` graphic that builds it. The active style profile (`<profile>/style-bible.md`) says which moves the creator you analyzed prefers; follow it where it differs.
Full component parameters are in `plan-format.md`.

## Trigger → visual

| spoken trigger | the move | `gfx` in the plan | timing |
|---|---|---|---|
| an action in an app: open, search, tap, switch on, post, share | a dark app screen where the action happens: the query types on and ends on its word, a white ring presses the button 0.2–0.4 s before the verb, the result is outlined and the rest dims | `ui`: `items` (`search`, `row`, `button`, `toggle`…), `taps`, `focus` | typing ends on the word; tap `t: "w:N-0.3"` |
| numbers on a screen: views, followers, reach, a score | the stat rolls up or the ring draws inside the app screen, the camera pushes onto it | `ui` item `stat` / `ring` with `t`, `focus` with `zoom: 1.3` | `t: "w:N-0.3"` |
| "comment KEYWORD and I'll send you…" (the CTA) | over the speaker a comment box types the keyword, then an Instagram notification "delivers" the reward; no end card | `comment` on the last `face` beat, `caption: "none"` | typing ends on the spoken keyword |
| one brand or product is named | an app tile or logo at 0.35–0.55 W. It drops in from above with motion blur; an ink blob morphs into the logo; a wordmark assembles with a glitch. No logo available: an invented glossy icon | `logo`: `src`, `label`, `size`, `plain` | 0.15–1.1 s before the word. The engine does not lead a single `logo` by itself: set `"t": "w:12-0.3"` or start the beat on the clause with the name |
| a list of brands | a relay: one big logo, then a row of small ones (7 logos in about 5 s reads well); a 2×3 grid; a row that grows around the mascot | `logos`: `items[{src,label,t}]`, `lead` | each item's `t` on its word; `lead` 0.3 s (default) |
| "connects X to Y", "works with any…" | a hub: the product in the centre, nodes with dashed lines appear one by one | `hub`: `center`, `nodes[{src,label,t}]` | each node on its word, led by `lead` |
| "It's called X" | a 1.5–1.7 s title on a white G: "IT'S CALLED" in an accent gradient, the app tile, the name in silver or a pixel font, a highlighter, a soft swish | `title`: `over: "it's called"`, `over_style: "caps"`, `icon`, `text`, `font: "block"` + `decode: true` or `font: "sans"`, `highlight`; beat `caption: "none"` | the beat starts on "It's"; the name resolves 0.28 s after "IT'S CALLED" |
| author, company, credentials | a photo of the person with their name (e.g. a conference photo); the company logo; "official Anthropic plugin" gets the Anthropic logo | `person`: `src`, `name`, `role`, `over`; or `logo` | on the name |
| social proof: stars, users | a star counter climbing from 0 while the star turns gold; the counter runs past the rounded spoken number and stops on the real one; a GitHub card | `counter` (rolling) + `shot` of the GitHub card (`fetch_assets.py github`) | the counter starts on the number |
| an ordinary number | an odometer counter in the caption slot with a small unit under it | `counter`: `text`, `label`, `t`, `label_t`, `over` | `t` on the number, `label_t` on the unit word |
| a huge number | the number in serif caps over the blurred source, the unit in italics in the accent | `counter`: `font: "serif"`, `bg_src`, `label`; beat `caption: "none"` | its own beat; appears 0–40 ms after the number |
| comparison, growth, percentages | a percentage with arrows over rising bars; two bars with scores and an "N×" total in the accent | `chart`: `bars`, `label`, `label_t`; `counter` for the total | the bars on the first number, the total before the phrase ends |
| a list item number | a 1.0–1.9 s title card: "THE FIRST" in a gradient, an icon or 3D emoji, the name types on its word | `title`: `font: "caps"`, `text: "THE FIRST"`, `gradient`, `icon`, `sub`, `sub_type: true`, `sub_font: "pixel"`; beat `caption: "none"` | cut on "The"; the name types on its own word (`sub_t`) |
| a mechanism: "switches to the next model" | a carousel of models with the centre card outlined, then a ✓ status with the chosen model | `switcher`: `cards`, `seq[{t,index,status}]` | the state flips on the verb |
| "leaves a note", "passes the context" | a yellow sticky note slides out of the logo | `note`: `logo`, `title`, `lines`, `note_t` | on "note" |
| "installs", "generates", "runs" | a mini app with a progress bar up to a ✓ at 100 % | `widget`: `icon`, `name`, `status`, `progress` | the progress runs through the whole beat |
| "scans", "sorts", "finds" | a grid of documents with a counter; a widget counting the items found | `switcher`, `counter`, `widget` or `html` | the count on the verb |
| "sits between X and Y" | a diagram file → scanner → the agent, statuses change on the nouns | `hub` or `html` | each node on its word |
| a problem, a limit, a danger | a meter fills red, the mascot shakes, the whole frame flashes red on "limit"; a big red status word | `meter`: `label`, `to`; `logo` + `strike`; the flash is `html` | on G without the speaker; the fill on "runs out" |
| "free", "no subscription" | a price counts down to $0, the paid competitors' logos get struck through; the face with the keyword "free" in the accent | `counter` + `logo` with `strike` + F with `emph` | the strike on "pay" or on the name |
| the opening of a reel about one product | accent character noise that resolves into the product name in a pixel font | `title`: `font: "block"`, `text` = the product name, `decode: true`; beat `bg: "dark"` | from the first frame |
| a command, a prompt, a coding agent | a terminal with the product's mascot; a line types on | `terminal`: `title`, `lines[{text,t,prompt,color}]` | the first line types from the beat start, the next ones on their words |
| a site, a README, docs, an interface | a sharp card with browser chrome, a push-in, an accent box on the key spot, a highlighter over the name | `shot`: `src`, `crop`, `chrome`, `url`, `box`, `box_t`, `zoom` | the box on the word it proves; the push-in 0.35 s later |
| a long page or list | B: a sharp card scrolls over its own blurred copy | `shot` on a dark G; for B, `broll` with an image | the scroll runs through the whole beat |
| a post on X, a quote | a post card | `tweet`: `name`, `handle`, `avatar`, `text`, `highlight` | on "posted", "said" |
| a generation result, a video | a card over its blurred copy; the vendor's own clip | `broll`: `src` (image or video), `media_start` | the whole beat |
| an emotion, a metaphor | 3D emoji: rocket, money, clock, 🔎 | `emoji`: `src` (Fluent 3D) | on the word |
| talking to the audience ("if you're a beginner") | a character or mascot with a "?" | `emoji`, or `logo` with `plain: true` | on "you" |
| a payoff at the end of a sentence ("completely free", "instantly", "all on its own") | F for 0.6–1.1 s: an italic connector + the keyword in the accent | layout `face`, `caption_style: "mix"`, `emph` | cut at the start of the clause |
| a new section inside a talking stretch | a warm light leak of 170–700 ms | `"trans": "leak"` on the beat | the leak ends on the cut |
| before and after | stacked vertically: the copy on top, the original below, label plates | `html` | on "clone", "before" |
| points inside a real document | a highlighter sweeps through all the points in about a second | `shot` + `box`, or `html` | on the enumeration |
| CTA | F close-up, "comment" in italics, "“KEY”" in a gradient, held to the end | `layout: "face"`, `cta: true`, `meta.cta_word` | always the last beat |

## Free-form graphics: `html`

When the kit lacks a move, build it in place. Good edits do the same: every reel gets its own mini-interfaces.
A beat with `"type": "html"` inserts your markup into the beat's zone and adds your GSAP lines to the shared timeline `tl`.
Tokens:
- `{p}`: this beat's unique id prefix;
- `{t:w:57}`, `{t:+0.4}`, `{t:word:Gemini}`: a time in seconds (word 57; 0.4 s after the beat starts; the word "Gemini" inside the beat);
- `{img:assets/x.png}`: the path to an image;
- `{accent}`: the accent colour.

Example: before and after.
```json
{"t0": "w:40", "layout": "graphic", "bg": "white", "gfx": {"type": "html",
  "html": "<div class='center' style='gap:28px'><div id='{p}a' class='card' style='width:900px;height:480px;background:url({img:assets/clone.png}) center/cover'></div><div id='{p}b' class='card' style='width:900px;height:480px;background:url({img:assets/original.png}) center/cover'></div></div>",
  "js": ["tl.fromTo('#{p}a',{y:60,opacity:0,filter:'blur(12px)'},{y:0,opacity:1,filter:'blur(0px)',duration:0.35},{t:+0.02});",
         "tl.fromTo('#{p}b',{y:60,opacity:0,filter:'blur(12px)'},{y:0,opacity:1,filter:'blur(0px)',duration:0.35},{t:word:original});"],
  "sfx": [{"t": "+0.02", "kind": "pop"}, {"t": "word:original", "kind": "pop"}]}}
```
Custom graphics follow the same rules as the kit:
- enter in 0.3–0.4 s (blur, fade, scale);
- change state on the word;
- nothing holds still for longer than 2 s;
- `assets/base.css` already has the classes `card`, `tile`, `label`, `over`, `box`, `mark` and the variables `--accent`, `--ink`;
- animate only through `tl`, and never touch `display` or `visibility` on a `section`;
- give the frame depth (shadow, blur, glow): `plan_lint.py` warns about flat custom graphics. Depth recipes are in `move-bank.md`, GSAP pitfalls in `engine-notes.md`.

Not in the kit, so build them with `html`: a logo morph, a slot-machine list of models, a highlighter sweep through a document, before and after, mascot animation, a red alarm flash.
Already built in: character noise in a title (`decode`), "IT'S CALLED" (`over_style: "caps"`), the speaker snapping into the arch at the start (`meta.open_zoom`), a white flash at the start (`meta.flash_start`), a warm light leak (`trans: "leak"`), a red strike-through on a logo (`strike`).

## Where to get assets

| what | how |
|---|---|
| a brand logo | `fetch_assets.py <project> logo anthropic claude google github`: a Simple Icons SVG in the brand colour (`github:000000` forces a colour). Simple Icons returns 404 for OpenAI, so use a local SVG or `favicon openai.com`. For any brand missing from Simple Icons: `favicon <domain>` (a 256 px site icon) |
| a 3D emoji | `fetch_assets.py <project> emoji "Rocket" "Money bag"`: Microsoft Fluent Emoji 3D, MIT licence. Names follow the folders of github.com/microsoft/fluentui-emoji |
| a repository card | `fetch_assets.py <project> github owner/repo`: the GitHub social card (1200×600) with name, description and stars |
| a site screenshot | `fetch_assets.py <project> shot https://site.com [name] [--mobile] [--dark] [--scroll-to="Heading"] [--full]`: Playwright, desktop 1440×900 @2x or mobile 430×932 @3x. Needs `pip install playwright && playwright install chromium` |
| a photo of a person | show a real person named in the script only on a real photo you are allowed to use, e.g. their public profile photo. On pbs.twimg.com, drop the `_400x400` suffix to get the full-size original. Never generate or stock-photo a named person |
| your own screen recording | put the mp4 in `assets/` and use it as a `broll` video; `media_start` is the second it starts from |

Build every visual fresh for the reel; don't reuse images made for other posts.
Logos, screenshots and posts are third-party material. Use them the way news and commentary reels do, and follow the rules of your platform and country.
