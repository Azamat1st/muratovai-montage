# Example plan

`plan.json` is a complete edit plan for a 54-second English talking-head reel about setting up a newly released AI model ("Nova"
is a placeholder name). It uses the engine defaults (`_defaults`) and the `bold` sound profile; a real edit uses the user's own style profile. Each beat has a `_note` with its role
(HOOK, NAME, PROOF, MECH, LIST, NUM, PAIN, PAYOFF, BRIDGE, CTA) and why the graphic looks the way it does; the engine ignores
keys that start with `_`.

Read it as a pattern, not as a project to build: the `w:N` times point into the `work/words.txt` of the original take, which is
not shipped. `references/beat-planning.md` walks through it beat by beat.

## How it maps to the pipeline

| pipeline step | in this example |
|---|---|
| `prep.py init/cut` | produced `work/words.txt`; every `"t0": "w:N"` is the start of word N of the clean cut minus 0.05 s |
| `fetch_assets.py` | every image in the plan can be fetched: `logo claude google` (Simple Icons), `favicon openai.com openrouter.ai`, `emoji "Robot" "Rocket" "E-mail" "Star" "Speech balloon" "Megaphone" "Money bag" "Stopwatch"`, `shot https://example.com example` |
| `autoplan.py` | wrote a draft with the same beat borders and `TODO` graphics; the graphics were then chosen with `shot-library.md` |
| `meta` | `style` (targets), `profile` (sound), `accent` + `accent_face` (one colour per reel), `music`, `flash_start` (opening move), `cta_word` |
| beats | 27 beats: layouts `S S G G G F S F S S G G S G S F G G S G G S G G F S F` (split ≈0.38, graphic ≈0.42, face ≈0.20 of the time) |
| graphics used | `title` with `decode`, `logo`, `logos`, `shot` (with `chrome`, `box`, `zoom`), `counter` (odometer and serif, with `bg_src`), `widget`, `terminal`, `hub`, `switcher`, `emoji`, `chart`, `meter`, faces with `caption_style: "mix"` and `emph`, a light leak (`trans: "leak"`), the CTA (`cta: true`) |
| `plan_lint.py` → `build.py` → `snap.py` → render → `finish.py` → `qa.py` | the same commands as in `SKILL.md`; with your own take, re-map the `w:N` indexes to your `words.txt` |

## Using it with your own take

1. Record the take and run `prep.py` (see `SKILL.md`).
2. Run `autoplan.py` for your own draft, then use this file side by side: find the beat in the example with the same role and
   copy its graphic, changing the text, the assets and the `w:N` times.
3. Fetch the assets you need into `<project>/assets/`, then lint, build and look at the contact sheet before rendering.
