# Beat planning: how to split a reel into beats

This file gives the order of decisions from transcript to `plan.json` and two worked examples: a one-tool reel and the bundled `examples/plan.json`.
Numbers and moves come from the active style profile (`<profile>/style-bible.md`, picked with `meta.style`), its compact
`analysis/reference_index.md` and selected `analysis/windows/*.json` files when available, and `shot-library.md`. Read the
style bible and one or two matching reference windows before planning. The full timeline is archival evidence; a legacy
profile may have beat sheets instead. The windows separate manually tagged facts from scene-score/SFX candidates; verify the latter
in the source video before copying a specific transition or sound decision. If the user has no profile yet, make one first.

## Workflow

1. **Listen to the raw and clean takes while reading `work/words.txt` in full.** Every word is numbered; that number is
   `w:N` in the plan. Pick the strongest complete opening from the selected take, reject failed retakes and filler, and
   retain the pause or repeated phrase that sets up a contrast. If the cut changes meaning, redo `prep cut` and listen again.
   Mark proper names, brands, amounts and units; compare their exact spelling with the brief or original source asset.
2. **Tag the role of each phrase:**
   - HOOK: the first sentence;
   - NAME: "it's called" (in Russian, «называется»);
   - PROOF: author, company, stars, a page;
   - MECH: what the tool does, the verbs;
   - LIST: "the first", "then", "and finally";
   - NUM: any number;
   - PAIN: a limit, a price, a danger;
   - PAYOFF: the benefit at the end of a sentence: "free", "instantly", "all on its own";
   - BRIDGE: a connector or aside with no product in it: "save this", a new section, a metaphor;
   - CTA: the ending.
3. **Pick the skeleton:** one tool, a list, news or the structure actually heard in this take. Compare similar hooks and
   semantic blocks in the reference timeline; choose a first 3 s that states the question/payoff and can be read at phone size.
4. **Cut into beats.** A beat boundary is the start of a clause:
   - after a full stop;
   - before "which", "so", "and", "plus", "then";
   - before a number;
   - before a name.
   Use the active profile's visual-segment and layout-run measurements as a starting point. Scene-score segments can include
   animation, so move the boundary to the sentence or demonstrated action when needed.
5. **Give each beat a layout** from the table below.
6. **Give each beat one main graphic** from `shot-library.md`. If a beat is long, add events at the words they prove. Change
   scale, proof source or visual mechanism across consecutive semantic blocks; repeated small text on dark cards is not
   meaningful variety. Keep the profile's palette, typography and layout proportions.
7. **Time the events:**
   - a logo on its correctly spelled spoken name (`logos` and `hub` may pre-position a blank slot, then reveal the logo on
     `w:N`; do not disclose later brands early unless the hook intentionally does so);
   - a counter on the number, the unit on the unit word;
   - a box on the word it proves;
   - a state change on the verb.
8. **Colour.** `accent` is the product's brand colour. `emph` goes only on payoff words, 1–2 per F beat, plus the CTA keyword.
9. **Captions.** Automatic by default. Set `caption: "none"` on titles, big numbers and stacks of labelled logos. Use measured
   caption bounds/font as a target, then check the actual 9:16 phone preview: move or enlarge text that hides the face,
   hands, proof, or is too small against a dark mock-up. Keep names and numerals exact.
10. **Run `plan_lint.py`.** Fix the errors. Work through the warnings about layout shares and static beats too; don't ignore them.
11. **Run `build.py`, then `snap.py`**: one still per beat on a contact sheet (`work/snap_sheet.jpg`). Look at it before render.
12. **After rendering and `finish.py`, watch the new MP4 with sound.** Inspect a frame before and after each transition,
    the middle of every semantic block and the opening at short intervals. Check that each visual lands on its word, each
    caption is readable, the moving face stays framed and each SFX is audible in context. Fix the plan/cut, rerender,
    remix and rerun QA when a defect appears. Passing lint or technical QA alone does not accept the edit.

## Decision table: layout

| phrase role | layout | background | why |
|---|---|---|---|
| the first clause of the hook | S with the product graphic | white, or dark for a dark product | the product is on screen from frame 0; your profile's `open_layout` can change the opening layout |
| the second clause of the hook (the payoff) | G or F | white | the first layout change comes by 3 s at the latest; the payoff is in the accent |
| NAME | G | white | a 1.5–1.7 s title, no caption |
| PROOF: a page, README, docs | dark G or B | dark | code and docs go on dark |
| PROOF: a person | S or G | white | photo, name, role |
| MECH | S | white or grey | the speaker explains over the screen |
| NUM | G | white or dark | a number is its own beat, with no caption |
| LIST, an ordinal word | G | white or beige | a title card, no caption |
| PAIN | G | white with red | no speaker, an alarm state |
| the fix after PAIN | S | white | the speaker is back, the state turns green |
| PAYOFF under 2.5 s, with no brand and no number | F | — | a breather: the connector + the keyword in the accent |
| a new section inside an F stretch | F with a leak | — | `"trans": "leak"` |
| CTA | F | — | always |

**Balance rules for the neutral fallback example below (replace with the active profile's measured shares):**
- F takes ≈20–25 % of the time. A brief adjacent F beat is fine when the expression or action changes meaningfully.
- A cut should change the visual idea; it need not change the layout every time.
- A 30–50 s reel may have 12–20 layout runs; the reference profile sets the actual target.

**Signs of a bad beat:**
- The graphic is not about what is being said: someone else's logo, a number that doesn't match the spoken one.
- The S zone is empty, or a picture stands unchanged for more than 2 s.
- A caption repeats a title that is already drawn.
- Two visually identical face beats, or a face held longer than the style uses without a performance change.
- A number is said but not shown; a brand is named but has no logo.
- The scene comes from a world that is not the viewer's. Show the use case in the viewer's own world: their local tools, currency and services.

## Example 1. A one-tool reel (35 s)

A generic skeleton for a reel about one open-source tool: hook, proof, a name reveal, the mechanism, a pain and its fix, the CTA. The triggers are roles, not a script; put your own words in.

| t | role · trigger | layout | `gfx` |
|---|---|---|---|
| 0.00 | HOOK · the product name, the promise | S, dark | `terminal` with the product's mascot; a `logo` can stand in for the mascot |
| 2.07 | HOOK · the payoff phrase | G, white | `title` `font: "sans"`, the payoff in caps, `gradient`; a custom symbol can be built with `html` |
| 3.57 | PROOF · the platform it lives on | S, white | `logo` of the platform, `t` on its name minus 0.5 s |
| 5.57 | PROOF · what it gives | B | `shot` of the README on dark |
| 6.30 | NUM · a huge number | G, dark, no caption | `counter` with the number, `font: "serif"`, `bg_src` README, `label` = the unit |
| 8.23 | PAYOFF · the last word of the sentence | F | mix, `emph` on that word |
| 9.10 | LIST · a run of model names | S, white | `logos`: one item per name, each `t` on its word |
| 15.17 | NAME · "it's called X" | G, white, no caption | `title`: `over` "it's called", `icon` of the repo, `text` = the name, `font: "pixel"`, `highlight` |
| 16.97 | MECH · "connects X to Y" | S, white | `hub`: the product in the centre, the connected tools as nodes |
| 18.50 | NUM · a count | S, white | `counter` with the count, `label` = the unit |
| 20.13 | PAYOFF · a short benefit | F | plain white captions |
| 21.73 | PAIN · a limit that runs out | G, white | `meter` with the limit's name, `to: 0.97` |
| 23.60 | MECH · "switches", "picks the best" | S, white | `switcher`: option cards, `seq` on the verbs |
| 25.93 | PAYOFF | F | — |
| 27.13 | MECH · "leaves a note", "passes the context" | S, white | `note`, `note_t` on "note" |
| 31.77 | CTA · "comment" + the keyword | F | `cta: true`, `meta.cta_word` |

Layouts: S G S B G F S G S S F G S F S F, 15 runs in 35 s. The accent (the product's brand colour) appears only on the payoff title, the unit of the huge number, the keyword on the first face, the count and the CTA keyword.

## Example 2. `examples/plan.json`: setting up a new AI model (EN, 54 s)

A worked plan for an English take about a newly released AI model; "Nova" is a placeholder name. Each beat carries a `_note` with its role and the reason for the choice; the engine ignores it. The `w:N` indices point into the original take's `work/words.txt`, which is not shipped, so read the plan as a pattern, not as a project to build. Its assets come from `fetch_assets.py` (`favicon openai.com openrouter.ai`, `logo claude google`, `emoji "Robot" "Rocket"`, `shot https://example.com example`…).
Meta: `style: "_defaults"` (the engine's fallback numbers; a real edit names your style profile), `profile: "bold"`, `accent: "#E551BA"` with `accent_face: "#FF7AD1"` for keywords on the face, `music: "ambient_tech_90"`, `flash_start: true`, `cta_word: "NOVA"`.

| # | `t0` | layout | `gfx` | role and why (from `_note`) |
|---|---|---|---|---|
| 0 | `0` | S, white | `title` "NEW AI MODEL", `font: "block"`, `decode: true`, OpenAI `icon` | HOOK: who made it and where they came from; the pixel title decodes from frame 0 |
| 1 | `w:5` | S, white | `logo` OpenAI | HOOK: the company they left; a named brand gets its logo |
| 2 | `w:8` | G, dark | `shot` of the model's site, cropped | PROOF: a claim gets the real page, on a dark full-frame card |
| 3 | `w:14` | G, white, no caption | `counter` "200×", `font: "serif"`, `label` "times faster" | NUM: the first number gets its own beat |
| 4 | `w:18` | G, white, no caption | `counter` "400×", `font: "serif"`, in the accent colour | NUM + PAYOFF: the second number, in the accent |
| 5 | `w:22` | F | mix, `emph: ["free"]` | PAYOFF: "free, anyone can use it"; one keyword in the accent |
| 6 | `w:31` | S, white | `widget` "Nova setup", `progress` 0.08 → 1.0 | MECH: "step by step" becomes a mini app with a progress bar |
| 7 | `w:42` | F | mix, `emph: ["save"]` | BRIDGE: "save this", a short breather on the face |
| 8 | `w:45` | S, white | `logos`: Google → Nova | MECH: two brands in a row make a logo relay |
| 9 | `w:50` | S, white | `terminal`: 3 lines at `w:50`, `w:56`, `w:59` | MECH: console steps; each line appears on its verb |
| 10 | `w:61` | G, white | `logo` Claude Code, `size: 340` | NAME: the tool the prompt goes into, as a big logo |
| 11 | `w:69` | G, dark | `terminal` "Claude Code" with the prompt | PROOF: the prompt itself; code goes on dark |
| 12 | `w:76` | S, white | `hub`: Nova in the centre, 6 nodes | MECH: "goes through huge amounts of data"; the tool sits in the centre |
| 13 | `w:90` | G, white, no caption | `logos`: 4 labelled 3D emoji | LIST: four kinds of data |
| 14 | `w:98` | S, white | `switcher`: 4 cards; "Urgent" at `w:105`, "Spam" + "✓ 200 sorted" at `w:108` | MECH: sorts, flags urgent, drops spam; the states flip on the verbs |
| 15 | `w:109` | F | mix, `emph: ["data"]` | PAYOFF: "like nothing else"; the keyword in the accent |
| 16 | `w:116` | G, dark | `emoji` rocket | BRIDGE: a metaphor with no product, a 3D emoji on dark |
| 17 | `w:122` | G, white, no caption | `counter` "742", `over` "one guy ran", `label` "ads" | NUM: what one user ran through it |
| 18 | `w:130` | S, white | `logo` stopwatch emoji, `plain: true`, `label` "40 seconds" | NUM: how long it took |
| 19 | `w:132` | G, white | `chart`, `label` "↑ better ads" at `w:138` | PAYOFF: better results |
| 20 | `w:139` | G, dark, no caption | `counter` "120,000,000", `font: "serif"`, `bg_src` = the site | NUM: free tokens, a huge number over the blurred site |
| 21 | `w:148` | S, white | `meter` "Free tokens running out", `to: 0.97` | PAIN: when they run out, the meter fills red |
| 22 | `w:152` | G, white | `logo` OpenRouter | MECH: the fallback provider gets its icon |
| 23 | `w:156` | G, gray | `shot` with `chrome`, `url`, `box`, `zoom` | PROOF: a gallery of real projects on a site card |
| 24 | `w:165` | F, `trans: "leak"` | mix, `emph: ["friend"]` | BRIDGE: a new section ("send this to a friend") opens with a warm light leak |
| 25 | `w:175` | S, white | `title` "HOURS SAVED", `font: "pixel"`, `highlight: ["SAVED"]` | PAYOFF: hours saved |
| 26 | `w:182` | F, `cta: true` | the keyword `meta.cta_word` in the accent | CTA: a face close-up to the last frame |

Layouts: S S G G G F S F S S G G S G S F G G S G G S G G F S F, 19 runs.
Measured on the original test take: layout shares S 0.38, G 0.42, F 0.20; the first change at 1.65 s; 5 effects per 10 s; −14.0 LUFS.
Differences from the fallback targets in `styles/_defaults/style.json`: the take was slower (3.65 words/s against 4.0), and F came out slightly under the norm.

## Other languages (e.g. Russian)

- **Language.** Set `meta.lang` in the plan and `--lang` in `prep.py init`.
- **Captions.** Russian words are longer, so the engine packs caption chunks by characters: 16–20 characters, 1–2 words. Product names stay in Latin script (Claude Code).
- **Fonts.** Inter, Playfair Display, Pixelify Sans and Press Start 2P include Cyrillic; Instrument Serif does not. With `meta.lang: "ru"` the engine sets Noto Serif Display for the big italic caps, because Playfair's italic Cyrillic "Т" reads like an apostrophe. For other Cyrillic languages, set `meta.caps_font` yourself.
- **CTA.** Keep the same form: a face close-up, an italic connector, the keyword in the accent, held to the last frame. The wording is the speaker's own. Use `caption_style: "mix"` with `emph` on the key words; `meta.cta_word` is only needed when the CTA asks for one comment keyword.
- **The viewer's world.** Show the use case with the viewer's own tools, currency and services.
- **Music** is always on; leave no silent gaps.
