# Sound design: how the engine places and mixes sound

Sound is half of the edit, not polish. Two things carry most of it: the opening "fade" (a short swell under the first word) and cues that are clearly audible on graphic events.

This file covers:
- what a quiet, measured mix looks like;
- the two sound profiles;
- how the kit, the placement and the mix work;
- how to check the result without hearing it.

The research behind these rules (15 rules, a rulebook, public sources) is in `sound-research.md`.

## 1. A quiet, measured mix: typical values

These are typical values of a quiet talking-head mix; your style profile measures its own. Method: the background of each analyzed reel is separated from the voice with Demucs. Bursts above the music are cut out (`scripts/reference/sfx_extract.py`) and classified by an audio model (`scripts/reference/sfx_classify.py`). The time of each sound is checked against the cuts, and each cut against frame differences (±15 ms).

| what | measurement |
|---|---|
| **opening "fade"** | a sub swell, now and then a reverse swell. Energy in 45–90 Hz is 8 dB above the music. It rises smoothly by about 25 dB over 0.24 s, holds to 0.36 s, drops 7 dB and dies away by 0.6 s. It sits under the first word without masking it |
| cues per reel | about 4 noticeable ones, mostly whooshes and clicks, now and then a dull sub hit, a glitch, a slide, a scratch or a chime |
| whoosh | mostly a low "whoomp" (spectral centre 80–250 Hz), sometimes a high airy one. 0.1–0.4 s long. It starts 100–170 ms after the cut and peaks 200–260 ms after it: the sound follows the graphic flying in, not the cut |
| click | dry and short, 0.08–0.28 s, on a UI element appearing |
| level | whoosh and click peaks sit 24–26 dB under the average voice, almost level with the music. The cue is felt more than heard |
| music | ambient electronic around 90 BPM, 29 dB under the voice, continuous. The mids are dipped for the first 0.6 s: the music floats in under the opening swell |
| a dense edit (`era: "2025"`) | music 9–13 dB under the voice, 11–15 cues per 10 s, sound on 30 % of cuts |

## 2. Two profiles: `bold` and `measured`

Set `meta.profile` in the plan.

- **`bold`** (default). Every cue is clearly audible: whoosh and pop peaks sit 4–6 dB under the voice's speech RMS, the music ≈15 dB under the voice, up to 12 cues per 10 s. This level was chosen because in tests the quiet measured levels read as "no sound" to viewers.
- **`measured`**. The style profile sets the music level (`sound.music_mix_rel_db`) and cue density (`sound.sfx_per_10s.median`). A loud measured bed needs louder cues than a quiet one: when the plan has no explicit `sfx_offset_db`, `finish.py` lifts ordinary cues by at most 18 dB toward a peak about 6 dB above the bed's mean. Unclassified Demucs background transients are not treated as isolated SFX gain measurements. A plan's explicit offset takes precedence.

Rules for both profiles:
- **The opening sound matters most.** It is the first thing the viewer hears. Profile `bold` opens on a riser if your own kit has `open_riser/`, otherwise on the synthesised sub swell; `measured` opens on the swell (§7).
- **Every scene change gets a soft transition and a whoosh.** Only hard cuts (`"trans": "cut"`) stay silent.
- **There is always music.** For tech reels a dark, tense electronic bed around 100 BPM works better than a lounge one (§8).
- **Clean the voice before the mix** (§8).

## 3. Which event gets which sound

The engine (`build.py`) places sounds on graphic events. `finish.py` sets their level, alignment and thinning.

| event | sound | alignment |
|---|---|---|
| first frame (`measured`, or `bold` without a riser in your kit) | `open`: the synthesised sub swell (`open/open_swell_{a,b,c}`, `sfx_synth.py`). It owns the first 0.6 s: other cues before 0.6 s are dropped, except staged `punch`/`shatter` hits | starts at 0 |
| first frame, `bold` with `open_riser/` in your kit, `meta.open_sfx: "riser"` or a path | `open_riser`, see §7 | starts at 0, hard stop on the first scene change |
| layout change (`fade`, `blur`, `flash`, `leak`) | `whoosh` (5 variants: low whoomps and airy ones) | the event sits 0.04 s before the cut; the peak lands 0.12 s after the event, mid-transition |
| punch-in or pull-out between split and face (`punch`) | `whoosh_low` | peak 0.10 s after the event |
| graphic change inside the same layout (`zoom`, or a soft transition into the same layout) | `whoosh_soft` | as for `whoosh` |
| a screenshot, post or b-roll comes in | `swipe`: it slides in like paper | as for `whoosh` |
| hard cut (`cut`) | nothing | — |
| element appears (logo, photo, emoji, card) | `pop` / `click` | peak on its first visible frame |
| hub node, carousel item | `tick` / `click` | on its word |
| counter roll | `count`, then a lock `click` when it stops | with the start of the roll |
| terminal typing, title type-on | `typing` | with the start of typing |
| marker, box on a screenshot | `swipe` | on the word they prove |
| character scramble in a title | `glitch` | with the start of the scramble |
| strike-through, meter hitting red | `error` | on the strike |
| done: ✓ in a terminal, progress at 100 %, a ✓ status in a switcher | `ding` / `chime` | on the check |
| chart bars grow | `reveal` (plays `chime` unless your kit has `reveal`) | as the bars start to grow |
| big number, "IT'S CALLED X" | `hero`: a hero moment, see §4 | on the appearance |
| light leak on a hard cut | `whoosh_soft` | 0.12 s before the cut |
| custom `html` graphic | your own list: `sfx: [{t, kind, db}]` | — |

## 4. Techniques that make the sound work

- **Hero moment** (`hero`, at most 3 per reel; later ones are dropped):
  - `riser_soft` ends exactly on the appearance;
  - 0.35 s before the appearance the music dips 9 dB;
  - on the appearance an `impact` hits (sub, 250–700 Hz body and attack);
  - 0.8 s later a `chime` sparkles, if nothing else is there.
- **No machine gun.**
  - Each frequent class has 2–5 variants, rotated. The same file never plays twice in a row.
  - Pitch and speed vary ±3 % (±6 % for whooshes, which repeat most), level ±1.5 dB.
- **Frequencies.**
  - Everything except the opening sound, `impact` and `whoosh_low` is high-passed at 140 Hz (whooshes at 110 Hz): the low end stays with the voice and the music.
  - Whooshes are low-passed at 6.5 kHz (`whoosh_low` at 5 kHz), so they never get a bright "ninja" top.
  - Hits and the opening swell carry 250–700 Hz; without that band a phone speaker can't play them.
- **The music gives way to the voice only in its band.** While the speaker talks, 250 Hz–4 kHz of the bed ducks up to 6 dB (sidechain ratio 4, attack 15 ms, release 380 ms); lows and highs stay. Then the whole bed "breathes" another 1–2 dB (ratio 1.8, 25/450 ms). The bed fades in over 0.3 s and out over the last 1.2 s. `meta.carve: false` turns the carve off.
- **Density.** `bold`: at most 12 cues per 10 s. `measured`: the style profile's median (fallback ≈5). When the cap is hit, the higher priority wins:
  1. the opening;
  2. whoosh, impact and staged hits;
  3. soft whoosh, pop, chime, ding, glitch, error;
  4. click, tap, swipe;
  5. tick, riser_soft;
  6. typing, count.

  Two cues closer than the minimum gap (0.12 s in `bold`, 0.5 s in `measured`) are one gesture: the higher-priority one stays. Beds (`typing`, `count`) may overlap other sounds.
- **Master.** A gentle glue compressor (−16 dB, 2:1), −14 LUFS integrated, true peak ≤ −1 dBTP.

## 5. Levels

A level is the sound's peak relative to the voice's speech RMS, in dB. The `measured` column lists the starting class levels before bed-aware calibration and per-cue rescue. A quiet style stays near these levels; a style with a loud bed lifts the ordinary cues while keeping their relative dynamics.

| sound | bold | measured |
|---|---|---|
| open_riser (its energy sits in the lows, so the peak is above the voice RMS while its loudness is ≈4 LU under the voice) | +4 | −4 |
| hit on the riser's stop (`sub_hit`, no random spread) | +2 | +2 |
| open (sub swell) | −2 | −12 |
| punch, shatter | −3 | −20 |
| whoosh, whoosh_low | −4 | −24 |
| impact | −4 | −22 |
| pop, tap, send | −5 | −24 |
| click, chime, ding, error, toggle, shutter | −6 | −24 |
| reveal | −7 | −24 |
| whoosh_soft, glitch, swipe, blip | −8 | −26 |
| riser_soft | −9 | −26 |
| tick | −9 | −27 |
| count, typing | −10…−11 | −28 |
| typing with `dur` (a prompt typing on screen) | **+3**, music ducked ≈ 12 dB | −28 |
| music (mean, not peak) | −15 | ≈ −28 (from `style.json`) |

- Shift every SFX level at once with `meta.sfx_offset_db`, the music with `meta.music_rel_db`, the density cap with `meta.sfx_per_10s`.
- With `meta.era: "2025"`, `bold` uses music at −12 dB, 12 cues per 10 s and a 0.15 s minimum gap; `measured` takes the 2025 numbers from `style.json` (fallback: music −12 dB, ≈11 cues per 10 s).

## 6. How to check the sound without hearing it

1. **Check each cue separately.** `finish.py` renders a 60 ms isolated probe for every non-bed cue at its peak and compares it with voice, music and *the other effects* in four bands: 60–250 Hz, 250 Hz–1 kHz, 1–4 kHz, 4–12 kHz. A typing or count bed with `dur`, `hero`, `foreground: true`, or an explicit `db` is a foreground cue and receives the same check; an ambient bed remains `bed_not_scored`. For sustained foreground typing, its isolated stem covers the authored duration; the score is the median of active 60 ms click windows, with active-window share recorded. A single quiet gap between keystrokes cannot masquerade as a missing cue. Best-band SNR ≥ 0 dB is a useful audibility target, not a listening verdict. Masked foreground cues get up to +6 dB gain and, only when the music contributes to the masking, a short music dip of up to 9 dB. A soft whoosh may move up to 0.1 s toward a nearby speech gap. A different recording is kept only when its isolated score improves. Ordinary sustained cues are capped below speech RMS in `measured`; short pops and clicks may briefly peak above it. `work/sfx_used.json` records `foreground`, isolated SNR, rescue gain, music duck, timing shift and `audibility_status`; residual `review_required` cues need a listening decision before publishing.
2. **Loudness and density.** `qa.py` prints LUFS, true peak and cues per 10 s against the targets. It fails outside −14 ±1 LUFS or above −0.5 dBTP.
3. **A listening pass by an audio model.** Give the first 15 s of the master to an audio-capable model, for example Gemini 2.5 Pro via OpenRouter (`input_audio`; set `max_tokens` to at least 8000, or the answer gets cut) or an OpenAI audio model. Ask:
   - is there an opening sound;
   - which cues are audible, and when;
   - how cues and music balance against the voice, scored 1–10.

   This is a rough check. Models classify short one-shot sounds unreliably: Gemini Flash gives almost everything the same "quick, clean, digital" label. To check the kit itself, trust only objective features: duration, attack, spectral centre, low-band share.
4. **A person listening on a phone is the final judge.** Script and model scores are not approval.

## 7. The sound kit

`assets/sfx/<class>/<class>_<a..>.wav`, peak −3 dBFS, 48 kHz.

- **Synthesised** by `scripts/sfx_synth.py` (numpy, deterministic, free; shapes fitted to measured sounds):
  - `open/open_swell_{a,b,c}`: the opening swell, with the envelope described in §1;
  - `impact/sub_hit_{a,b}`: deep sub hits;
  - `sfx_synth.py` can also make plain procedural `typing`, `count` and `riser_soft` if you need them without ElevenLabs.
- **Generated** with ElevenLabs by `scripts/sfx_gen.py` (the prompts are in the script): `whoosh` (a, c–f; b was removed as a 0.04 s hit), `whoosh_low` (a–d), `whoosh_soft`, `pop`, `click`, `tick`, `glitch`, `swipe`, `chime`, `ding`, `error`, `punch`, `shatter`, `impact_a`.
- **Also generated** with ElevenLabs Sound Effects (prompts in `assets/sfx/PROMPTS.json`): `typing` (a fast phone keyboard), `count`, `riser_soft`, `tap`, `toggle`, `send`, `shutter`, `blip`, `reveal`. The bundled kit has no opening riser: profile `bold` opens on a riser only if your own kit has `open_riser/`, otherwise on the synthesised swell.
- A class missing from every kit borrows a related one: `tap`, `toggle`, `shutter` → `click`; `send` → `whoosh_soft`; `blip` → `tick`; `reveal` → `chime`; a missing `open_riser` falls back to the swell. Generate more variants into your own kit:
  ```
  python3 scripts/sfx_gen.py --list                                    # kinds, variants, seconds; generates nothing
  python3 scripts/sfx_gen.py --out <kit> tap toggle send shutter blip reveal
  ```
  This needs `ELEVENLABS_API_KEY` and costs about 40 credits per second of audio.
- **Kit lookup order** in `finish.py`: plan `meta.sfx_dir` → `$REELS_SFX_DIR` → the bundled kit. The first kit that has a class wins, so a class you generate overrides the bundled one.

**Checking a new file.** Duration, time to peak, spectral centre and the share of energy below 150 Hz must fit the class. An airy whoosh: 0.15–0.5 s, peak later than 40 ms, centre above 1 kHz. A low whoomp: centre 80–250 Hz. A click: shorter than 80 ms. Remove a file that fails: `whoosh_b` turned out to be a 0.04 s hit and was deleted.

### The opening riser (option)

`meta.open_sfx` picks the opening sound:
- `"riser"` (default in `bold`): the first file in the `open_riser/` class of your kit. Generate one with `python3 scripts/sfx_gen.py --out <kit> open_riser`, or put your own there. The bundled kit has none, so without your own riser `bold` falls back to the swell;
- `"swell"` (default in `measured`): the synthesised sub swell, from 0 s;
- a path to a riser file (wav; mp3 and m4a work too);
- `false`: no opening sound.

How the engine places a riser:
- It is sped up by `meta.open_rate` (1.2) like a sampler, so its pitch rises too.
- It is trimmed from the front so its hard stop lands on the first scene change (the first beat that starts at 0.7 s or later). If a hero reveal comes right after that change (up to 0.35 s later), the stop lands on the hero.
- A deep sub hit (`impact/sub_hit_*`) lands the cut. It replaces the hero's own riser and impact at that point.
- Until the stop the riser owns the sound: the scene whoosh and the small cues are dropped, and the music waits under it at −9 dB and opens on the cut.
- The riser's 0.5–4 kHz band is lowered 4 dB, so the hook's words stay on top.
- About 0.6 s of tail is kept after the stop and faded out.

The hard stop is found automatically as the steepest 30 ms drop of the envelope, so any riser with a hard stop works.

## 8. Music and voice

- **Bundled beds:** `tense_a` … `tense_d` (dark, tense electronic, 98–108 BPM), `ambient_tech_90` and `lofi_keys_84`. All are AI-generated; their prompts are in `assets/music/PROMPTS.json`. The style profile (`plan_defaults.music`) or `meta.music` chooses; the fallback is `tense_a`.
- **A tense bed for tech reels.** A dark, tense electronic bed around 100 BPM works well for tech reels, better than a lounge one; the `tense_*` beds are that kind. To make your own, generate one, for example with ElevenLabs Music (`force_instrumental: true`, length = the reel + 2 s):

  > dark tense electronic underscore, ~100 BPM, pulsing sub bass, ticking hi-hats, suspenseful minor pads, no melody hooks, no vocals, no drops

  Then set `meta.music: "<path>"` (mp3 or wav, relative to the project or absolute).
- **Level and shape.** The profile sets the level (`bold` −15 dB, `measured` ≈ −28 dB); `meta.music_rel_db` overrides it. The bed loops to the length of the reel and plays without gaps.
- **Voice.** `prep.py voice` writes `work/voice.wav`:
  - `--isolate`: ElevenLabs Audio Isolation, then the EQ/compression chain. Without `ELEVENLABS_API_KEY` only the chain runs;
  - `--chain`: the chain without isolation;
  - neither: a light clean-up (high-pass 80 Hz and a limiter).

  The chain: high-pass 85 Hz, −2.5 dB at 260 Hz, +2.5 dB at 3.2 kHz, +1.5 dB at 6.5 kHz, de-esser, compressor −19 dB 3:1 with 4 dB makeup, limiter 0.89.

## Staged hits (`punch`, `shatter`)

`finish.py` does not thin out these events from the plan's `sfx`: they ignore the minimum gap and survive the opening's takeover of the first moments (swell or riser). A punch, breaking glass and a sub hit at the same point play as layers. This is intended: that is how a staged fight sounds (a mascot punching a logo, for example). They also survive the opening swell's first 0.6 s, so a staged fight can start on frame 0 with any opening sound.

## 8. A prompt typing on screen

When a prompt or a command types out on screen for a second or more (an app input box, a terminal), give its `typing` cue the
typing time: `{"t": "+0.3", "kind": "typing", "dur": 3.3}`. Then `finish.py`:
- plays the keyboard for the whole `dur` (the clip loops if it is shorter), sped up 1.5× with the pitch kept, because on-screen
  typing is fast;
- sets it at +3 dB peak vs the voice RMS in profile `bold` (a `db` in the cue overrides it);
- ducks the music ≈ 12 dB with 0.15 s / 0.2 s ramps for exactly that time, so the keys are heard and the voice stays on top.

A typical result: music −30 dB → −44 dB under the typing, keyboard peaks −12…−13.5 dBFS. A short `typing` without `dur` stays a
0.9 s bed.
