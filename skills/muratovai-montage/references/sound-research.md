# Sound design for short vertical videos with motion graphics: research

Compiled in September 2026. Scope: vertical reels (talking head + animated UI, logos, counters, titles, transitions). The engine's own rules are in `sound-design.md`; this file holds the research behind them. Tags in [brackets] point to the sources in §1.

---

## 0. TL;DR: the 15 rules that matter most

1. **Audible beats "correct".** In tests, SFX at a quiet measured 24–30 dB under the voice read as "no sound"; the FHG skill reports a whoosh at −19 dB rejected as "nothing there". Targets vs the voice peak: transitions and graphic entrances ≈ −10 dB, hero hits −3 to −6 dB, small ticks ≈ −15 dB. Gate: the mix gains ≥ +4 dB RMS in a 0.3 s window at every story cue [OWN, FHG, YTE].
2. **Every sound belongs to a visible event and has a job.** Motion = whoosh, tension = riser, emphasis = impact/pop, snap = click/tap. Keep 3–4 sound families per video [YTE, CF, PV].
3. **Transients land on the contact/landing frame.** At most 0–1 frame early (never >45 ms), never >2 frames late [EBU, ITU, NH, CF]. A pop lands on its first visible frame, a slide or slam on the stop frame, a 10-frame spring-in +3 to +6 frames after its start [TV].
4. **Place pre-roll sounds by their PEAK.** File start = event − internal peak offset: a whoosh starts 3–6 frames before the cut so it peaks on it; a riser ENDS exactly on the reveal. Trim leading silence at −45 dB when generating [PIX, SMS, HF, OWN].
5. **The hero reveal is a fixed phrase.** Riser (1.5–3 s) → 1 beat of music stop (or a 3–8 frame dip) → layered impact (sub + 250–700 Hz body + transient) → sparkle ~0.8 s later. At most 2–3 layered heroes and ≤3 full-frame punches per video [SC, PV, CF, YTE].
6. **Whoosh on every layout change, silence on jump cuts.** Use a soft whoosh when only the graphic changes. A whoosh and a pop within 150 ms are one gesture. Pair whooshes with 0.1–0.2 s fades or blurs [OWN].
7. **Density: 4–6 SFX onsets per 10 s** for talking head plus graphics; 8–12 only in a genuinely dense "2025" edit. A 3–4 item click run is one gesture. Move a cue buried under continuous speech into a word gap, or cut it [OWN, VU, YTE, TV].
8. **No machine gun.** Rotate 3–4 variants per frequent class, never the same file twice in a row; vary pitch ±3–5 % and level ±2 dB. In runs, step the level down, speed up the intervals and collapse a blur into one swoosh. Count-ups rise in pitch and end on a louder "lock" [CF, SC, TV].
9. **Frequency slots.** Keep SFX out of the voice's 1–4 kHz where possible. Whooshes get low-mid body with some air, never a bright "ninja" swish. High-pass non-impact SFX at 90 Hz. Impacts need 250–700 Hz harmonics: phones drop everything under ~200 Hz. No glitch or static textures under speech [PV, FHG, OWN, YTE].
10. **Music is always there**, instrumental and continuous. For tech reels a dark, tense electronic bed around 100 BPM works; a lounge bed does not. Keep it ≈14 dB under the voice (12–16). Under continuous speech, prefer a static level plus a light 1–3 kHz carve to a pumping duck [OWN, HF].
11. **Shape the music.** Start on its strongest clean section. Fade in 0.25–0.3 s, out 1.2–1.3 s; no silent tail, never end mid-build. Ramp the bed out before the CTA sting. Put reveals and scene turns on bar starts (frames per beat = fps·60/BPM), but don't beat-cut every shot [PV, VU].
12. **Master at −14 LUFS integrated, ≤ −1 dBTP.** Meta publishes no official number; typical measured reels land at about −14.2 LUFS / −0.6 dBTP. Use `amix normalize=0`, then gain, then `alimiter ...:level=0` (or two-pass loudnorm). Verify with `ebur128=peak=true` and a phone speaker [OWN, VU, PV].
13. **Sync bookkeeping.** Do the SFX pass after picture lock. Pin a declarative cue table to shot and word anchors and re-pin it after any retime. Measure the pipeline's AAC priming offset once (~1 frame at 30 fps) and subtract it globally [SC, HF].
14. **Generated kit, library-first.** Write ElevenLabs prompts in six slots: source, action, material, space, envelope, modifiers + negatives. Use prompt_influence 0.45–0.6 for UI and transitions, an explicit duration and 3–4 variants. Post-process: trim, high-pass, normalize, fade; store peak offsets in a manifest. Don't synthesize "realistic" SFX in numpy or ffmpeg: two sources report it rejected (a deliberate 8-bit style is the exception) [DEAN, YTE, OWN, CF, FHG].
15. **Hook frame 0.** Speech and music start at frame 0. The video's most distinct cue goes on the first graphic landing, within ≤2 frames, without masking the first word: dip the bed 3–6 dB and keep the tail short. Hook → content: a low whoosh (≈80 ms pre-roll, peak on the cut, ≈180 ms tail) with a punch-in. No bright whoosh, white flash or glitch stamp [NH, FHG, OWN].

---

## 1. Sources

- [OWN] tests and measurements made while building this engine.
- [HF] HyperFrames docs and skills: https://github.com/heygen-com/hyperframes (audio carving and mixing, syncing a sound to an on-screen event).

Web skills:
- [SC] https://github.com/Vincentwei1021/video-shotcraft: sound-design.md, aesthetic rules S1–S5 + R4, music-beat-sync.md. The best overall.
- [YTE] https://github.com/hassancs91/claude-youtube-editor and its faceless-shorts variant: suggest-sfx, brand.md, palette.json. The best on levels and QA.
- [PV] https://github.com/maplefukku/pv-skills: pv-sound, pv-music (a HyperFrames PV suite).
- [NH] https://github.com/nateherkai/hyperframes-student-kit: short-form-edit.
- [VU] https://github.com/browser-use/video-use: "Music and sound effects".
- [CF] https://github.com/Razee4315/coldframe: sound-design.
- [TV] https://github.com/Tanguyvans/claude-config: sound-design (French).
- [SMS] https://github.com/SkillMedev/skills: sound-and-music-sync.
- [CAL] https://github.com/calesthio/generative-media-skills: audio-mixing-mastering, sound-design-foley, elevenlabs-sound-effects.
- [FHG] https://github.com/fhgomes/my-awesome-agents-skills: video-editing.
- [VAR] https://github.com/Varnan-Tech/opendirectory: vid-product-launch.
- [GIL] Gilloutmode, repo immo9-novia-com: sound-integration (French).
- [WD] https://github.com/curiositech/windags-skills: app-sound-design, sound-design-and-audio.
- [VIB] https://github.com/Momenta-App/vibeedit-sdk: vibeedit-sound-design, tonal-sfx-lessons.md.
- [DEAN] https://github.com/matthewharwood/dean-stack: docs/sound-design/CONSOLIDATED.md.
- [OK] https://github.com/yonatangross/orchestkit (mirror: NeverSight/skills_feed): music-sfx-selection, audio-mixing-patterns. Medium quality.
- [HAI] https://github.com/haidrrrry/claude-remotion-skill: design-rules.md.
- [EL] https://github.com/elevenlabs/skills: sound-effects, music; plus the ElevenLabs API docs.
- [TOPO] https://github.com/topo-ai/ai-video-skills: sound-fx-for-video (synth recipes, only for a deliberate synth style).

Articles and standards:
- [EBU] EBU R37, audio/video timing: https://tech.ebu.ch/docs/r/r037.pdf
- [ITU] ITU-R BT.1359, audio/video timing: detectable at +45 ms lead / −125 ms lag, acceptable at +90 / −185 ms.
- [PIX] Pixflow, cinematic whoosh guide: https://pixflow.net/blog/cinematic-whoosh-sound-effects/
- [SON] Sonilo, whoosh guide: https://sonilo.com/ai-music/whoosh-sound-effect-guide
- [VIO] violetrecording.com/sound-design-for-trailers and [BOOM] boomlibrary.com/blog/top-tips-for-trailer-sound-design: trailer impacts and risers.
- [CLL] criticallisteninglab.com: social loudness. [APU] apu.software: −16 LUFS as a conservative, unofficial convention.
- [PAI] pureaudioinsight.com: music ≈18–20 dB below speech. W3C/WCAG: background ≥20 dB below speech.
- [SFXE] sfxengine.com: layering in bands.

---

## 2. Rulebook

### 2.0 Conventions (read first)

- **Frames.** At 30 fps 1 f = 33.3 ms; at 24 fps 1 f = 41.7 ms. Keep times as float seconds and round to frames only at the last step [SC].
- **Event frame `t_event`:**
  - scale-in pop: the first frame the element reads, about tween start + 1 f;
  - slide, drop, slam or spring: the contact/stop frame;
  - cut: the first frame of the new shot;
  - stroke or draw: the sound spans the stroke, and "lock" sounds go on its completion.
- **Level convention A (used in the tables).** SFX peak vs the voice's phrase peaks, measured on stems before mastering (`volumedetect max_volume` or `astats` on SFX-only vs voice-only). Gain to apply = (voice_peak + target_rel) − file_peak.
- **Level convention B (YTE).** Kit clips are loudness-normalized to ~−20 LUFS with a −1.5 dBFS ceiling. The voice sits at ~−17 LUFS. Per-cue `gain_db` is relative to the clip. Pick ONE convention per library.
- **The engine's convention.** `finish.py` measures a cue's peak against the voice's speech RMS, not its peaks, so its numbers (`sound-design.md` §5) are not directly comparable with these tables.

### 2.1 Event → sound class table

| Event | Sound (layers) | Sync | Level vs voice peak | Notes | Src |
|---|---|---|---|---|---|
| **Hard cut, same layout** (jump cut in the talking head) | none | — | — | In a typical measured edit only about 8 % of cuts carry SFX. Give voice edits 30 ms fades. | OWN, VU, PV, NH, YTE |
| **Cut / layout change / section change** (face↔graphic↔split, new scene) | `whoosh` on a layout change; `whoosh_soft` when only the graphic changes inside the layout. Visual: 0.1–0.2 s fade or blur. | Whoosh PEAK on the first frame of the new layout: start = t_cut − peak_offset (typically 3–6 f before; for a lead-trimmed short whoosh, t_cut − 40 ms). | −8…−12 (soft −14…−18) | Rotate 3–4 variants. A pop landing ≤150 ms after is one gesture (pull the whoosh down 3 dB). | OWN, SMS, PIX, SC |
| **Graphic entrance** (card, window, chip, label, screenshot panel) | `pop` for small items; `tap`/soft drop for panels landing; big travel = `whoosh_soft` → `pop` on landing | Pop on the first visible frame; slides and springs on the stop frame (a 10-f spring → +3…+6 f after start) | −10…−12 (panel land −8…−10) | 4 pop variants, ±2 dB, ±3–5 % pitch. Exit: blip-out or reverse whoosh 3 dB quieter at exit_end − 0.2 s. | OWN, TV, CF, GIL |
| **Logo pop** (tool or brand logo, logo wall) | `pop` with body ("thock"); hero logo = whoosh→pop gesture or `impact_soft`; own brand at the end = sonic logo, 3–5 notes, ≤1.5 s | The logo's first visible frame. Show the logo 0.1–0.3 s **before** the brand word. | −8…−10 (hero −6) | Walls: alternate 2 samples, step the level 0.40→0.25 (≈−4 dB over 6), accelerate the intervals. More than 3 logos per second = one swoosh + one final pop. | OWN, SC S2, PV |
| **Text type-on** (prompt, terminal, search, chat) | `typing` loop trimmed to the exact type duration (fade in 40 ms, out 80 ms); Enter or `send` accent on submit | Starts on the first character (+50 ms), stops on the last | loop −18…−22; Enter/send −10…−12 | Diegetic typing only; decorative typing under speech gets cut. Slow typing = one key per 1–3 characters, with variants. | OWN, SC S4, YTE, CF, OK |
| **Number count-up** (stat, counter, odometer) | `count_roll` ticks for the count's duration + `count_lock` (pop/ding; add `impact_soft` for a key stat) on the final value. Stepped 1·2·3 counters: one pop per step, pitch rising. | Roll starts with the count (+0.15 s); lock on the frame the final digit settles | roll −16…−20; lock −8…−10 (key stat −6) | Rolls over 1.5 s duck under speech. Decrescendo steps (0.32→0.26→0.20) or a crescendo into the lock, by design. | OWN, TV, VAR, HAI |
| **Highlight / marker / underline / circle / glint** | `marker_draw` spanning the stroke; a ring or box closing = soft `tick`; glint or light sweep = `whoosh_soft` | Stroke = draw span; tick on the closing frame; whoosh peak mid-sweep | −14…−18 (key-word highlight −10) | At most one sweep per shot. The highlight lands with its word (≤2 f). Don't chime highlights. | OWN, YTE, SC Q4, NH |
| **Strike / error / red cross** | `error_buzz` (short, low, descending) or `strike_scratch`. A narrative payoff strike on a key word = `impact_deep_soft`. | First contact of the strike, or the cross completing | buzz −10…−12; payoff −5…−6 | Under speech: one clean snap. **Never glitch, static or hum textures under speech**; they read as noise at any gain. Glitch only in speech gaps. | OWN, YTE §10, OK, WD |
| **Success / check / result ready** | `success_chime` (2 notes rising, the ONE reward sound); result appears = `shimmer_reveal` | Check completion frame (not the draw start) | −10…−12 | List checkmarks get ticks, not chimes. Key-match tonal sounds to the bed. | CF, WD, OK, OWN, VIB |
| **Title reveal** (headline, "It's called X") | `whoosh_soft` with the blur/scale-in; a slammed heavy title gets `impact_soft`; "It's called X" = whoosh_soft + optional shimmer | Whoosh peak on the first sharp frame; impact on the stop frame | −10…−12 (impact −8) | The same title-card sound across the video (a motif). | OWN, SC, SMS |
| **Hook, first frame (0–3 s)** | Speech + music from f0 (fade ≤0.3 s). The first graphic landing gets the video's most distinct cue (low impact or whoosh→pop). Hook → content = low whoosh + permanent punch-in (~10 % in 9:16). | Impact within ≤2 f of the visual. Low whoosh starts ~80 ms before the cut, peaks on the cut, ~180 ms tail. | −8…−10 | The first word must stay intelligible: dip the bed 3–6 dB for ~0.5 s, keep the tail short. Must also work muted. Avoid bright whoosh, white flash, glitch, zoom >15 %, riser or bass-drop stamps. Vary the hook device between reels. | NH, OWN, FHG |
| **Section change / chapter card** | As "layout change", plus a music energy change on a bar start (add or drop a stem, open a filter) | Bar start | as above | One recurring "section whoosh" as a motif. | SC, PV |
| **CTA / end card** | `cta_sting` (3-note rising arpeggio) or a soft hit + the music's resolving phrase; `pop` on the CTA keyword | Sting on the CTA card landing; the bed fades 1.2–1.3 s into the last frame | −8…−10 | No SFX after the CTA except the sting; no silent tail. | OWN, CF, VU |
| **Big reveal** (product, result, money shot, logo lockup) | `riser` (1.5–3 s) → **1 beat of music stop** (≈0.5–0.6 s at 100–120 BPM) or a 3–8 f dip → layered `impact_hero` (sub + 250–700 Hz body + transient) → `shimmer` tail about 0.8 s later → music returns ON the hit | Riser END = reveal frame (start = t − length). All impact layers aligned to the same sample. Sparkle +25 f at 30 fps. | impact −3…−6 (the loudest SFX, still ≤ the voice peak); riser end −8…−10 | 1–2 per reel. Full-frame punches ≤3 per video, ≥16 beats apart. | SC 4.3+R4, PV, CF, VIO, BOOM, VAR, HF |
| Click / tap / toggle in UI | `tap`; `toggle_on` ≠ `toggle_off` | Press frame (or 1 f early) | −10…−14 | Hover gets nothing. | CF, SMS, OWN |
| Notification / mail / message arrives | `ding` | Toast entry frame | −10…−12 | — | OWN |
| Send / submit | `send_swoosh` (rising whoosh + soft pop) | On the send action | −10 | — | OWN |
| Screenshot / photo | `shutter` | Flash frame | −8…−10 | A real shutter can be the loudest UI sound. | SC, OWN |
| Zoom punch-in without a layout change | `whoosh_low` or nothing | Peak on the zoom's fastest frame | −10…−12 | Never a pulse-zoom plus whoosh on every beat (rejected). | FHG, dikshant shorts-factory |
| Meme gag | One loud meme SFX | Hard snap on the punchline word | loud by design | ≤1–2 per video, only on a playful line. Rarely fits tech reels. | YTE §10 |

### 2.2 Timing: placement formulas

- **Perception window.** Audio may lead picture by ≤40–45 ms and lag by ≤60 ms (up to 125 ms before detection) [EBU, ITU]. Transients therefore go 0–1 f early at 30 fps, never ≥2 f early, and lag at most 1–2 f [NH, CF; SC: 2–3 f is audibly off-beat in a beat-cut edit].
- **Place by the audible peak, not the file start.** `start = t_event − peak_offset(file)`. Trim leading silence at generation (`silenceremove=start_threshold=-45dB`) so transients sit near 0 s, and store `peak_offset` for whooshes and risers. VU measures the attack as the first sample above −30 dB of the peak [HF, VU, SC 4.6, OWN].
- **Whoosh.** Peak on the cut or on the fastest frame of the move. Length ≈ the move (a 0.5 s move takes a 0.4–0.5 s whoosh). It usually starts 3–6 f before [PIX, SMS, SON]. Placed after the motion it sounds like an echo [SMS].
- **Riser.** Ends exactly on the reveal frame (a peak that lands early "deflates"). Length 1.5–3 s in reels (PV: 2–4 s; UI: 10–20 f). Cut the tail at the hit [PV, SMS, VIO].
- **Pre-hit stop.** One beat (60/BPM s) of music silence, or a 3–8 f dip, right before the hit. "The sudden stop is the impact" [PV, CF, BOOM].
- **After the hit.** Sparkle or afterglow at +0.8 s (+25 f at 30 fps). An optional downlifter settles the energy [SC, PV].
- **Words.** Impacts and captions within 2 f of the word onset, with at most 0.15 s of deliberate anticipation. Logos appear before the brand word [NH, OWN].
- **Render offset.** AAC encoder priming is 1024–2112 samples (≈21–44 ms ≈ 0.6–1.3 f at 30 fps). SC measured 2032–2066 samples in a Remotion MP4. Measure once per pipeline: cross-correlate 2–3 sharp SFX files against the rendered audio track, subtract globally, and aim for a residual ≤0.5 f [SC S5].
- **Bookkeeping.** Pin cues to `shot.start + offset` or to word times, never bare absolute frames. Re-pin after any retime [SC 4.5, HF].
- **Beat sync.** Frames per beat = fps·60/BPM. Scene turns and reveals go on bar starts; don't beat-cut everything. Place the strongest hits on measured strong kicks, not half-beats [HAI, PV, SC].

### 2.3 Levels

| Class | Convention A: SFX peak vs voice peak | Convention B: gain on a −20 LUFS clip, **short-form** | Sources |
|---|---|---|---|
| Hero impact / big reveal / logo lockup | −3…−6 dB (the loudest SFX of the video, never above the voice peak) | 0…+3 (stamps/snaps 0…+7) | OWN (dense 2025-style edits ≈6 dB under the voice), YTE, PV, CF |
| Transitions (layout whoosh), graphic entrances (pop), logo pop, ding, send, shutter | −8…−12 (target −10) | whoosh −3; pops 0…+3 | OWN (loud onsets in measured reels 9–12 dB under), FHG (accepted ≈12 under) |
| UI taps, toggles, success chime, error buzz | −10…−14 | ≈ −3…0 | OWN (tap −14 on a −3 dBFS file ≈ −13 vs the voice) |
| Small ticks, count rolls, typing, soft whoosh, marker | −15…−20 (tick target −15) | long-form table −9…−11 | OWN (average measured onset 19 dB under the voice) |
| Riser | builds to −8…−10 at its end | hero risers 0…+2 | YTE |
| Music bed (mean vs voice mean) | ≈ −14 dB (12–16), continuous | — | OWN (bed −27 dBFS vs voice −13 dBFS) |

- **Rejected as too quiet** in tests: SFX at −24…−30 dB vs the voice (a quiet measured level) and FHG's whoosh at −19 dB. **Accepted:** 13 dB under a −16 LUFS voice, about 12–13 dB under the voice peaks [OWN]. A soft 2026-style mix averages 19 dB under.
- **Audibility gate** [YTE]:
  - Render the mix with and without SFX. At each cue, RMS(with) − RMS(without) over [t−0.05, t+0.25] s must be ≥ +4 dB for story cues and +1…+3 dB for texture. Measure a riser over its last third.
  - Short percussive clips need 3–5 dB more gain than sustained ones to be heard (they hit the ceiling before they reach the loudness target).
  - A cue fully under continuous speech measures +0 at any gain. Move it into a gap or cut it.
  - A noisy texture can't be fixed with gain; change the sound.
  - The engine runs a per-band version of this gate on every key cue (`sound-design.md` §6).
- The voice leads the mix. Nothing goes above the voice peaks except a deliberate meme gag [YTE].

### 2.4 Layering recipes

| Recipe | Layers and timing | Src |
|---|---|---|
| **Hero reveal** | riser (ends at t) → 1-beat music stop → at t: sub boom 40–80 Hz (5–10 ms fade-in) + body thud 80–500 Hz with 250–700 Hz harmonics + transient 4–12 kHz, all aligned to the same sample → sparkle at t+0.8 s → optional downlifter | SC, PV, VIO, BOOM, VIB |
| **Transition that must stand out** | whoosh (peak on the cut) → pop on the first landed element (≤150 ms later). Pull the whoosh down 3 dB. | YTE, OWN |
| **Hero popup (Reels style)** | click transient (0 dB) + subtle whoosh (−6 dB) + tiny sparkle (−10 dB). Only for hero popups; standard popups get a single pop. | GIL |
| **Stat payoff** | count_roll → lock pop/ding at the final value (+ impact_soft for the key number) | OWN, TV, VAR |
| **Hook punch / zoom** | low whoosh + a short low thump on the cut; no bright air | GIL, FHG |
| **Logo stamp / wordmark** | impact_deep (loudest) + sparkle at +25 f | SC |
| Rules | Each layer has one job and its own band (three rumbles = mud). Max 3–4 layers. Tuck the sub tail before the next word. Layer only the 2–3 hero moments; everything else is single. | SFXE, VIO, YTE |

### 2.5 Frequency and EQ slots

- **Voice.** Fundamentals 85–255 Hz, presence and intelligibility 1–4 kHz (peak 2–5 kHz), sibilance 5–9 kHz. Protect 1–4 kHz [HF, CAL].
- **Bed.** Carve instead of a pure duck. The HyperFrames carve at strength 0.8 cuts 250 Hz–2.5 kHz by ≈7 dB and 1.6 kHz by ≈15 dB; 0.25–0.5 is enough under a static bed. Or cut 2–4 kHz by 3–6 dB. "A duck alone leaves voice and bed fighting in 1–3 kHz" [HF, PAI].
- **SFX high-pass.** 90 Hz on everything except impact and sub layers [OWN].
- **Whooshes.** Low-mid body plus a little air. Not bright, not metallic ("ninja sword"), no bass boom unless it's a hit [FHG, YTE].
- **Repeated ticks and typing.** Short and low in level. Avoid resonant 2–5 kHz peaks (the fatigue band) and zero-ms attacks (a 5 ms ramp keeps the punch without the startle) [WD].
- **Impacts.** Phones roll off below ~200 Hz, so a sub-only hit disappears. Put the "heard" weight at 250–700 Hz (saturate a copy, high-pass it at ~150 Hz, blend it in) [PV, MusicTech/NI].
- **Designed-hit band map.** Sub 20–80 / body 80–500 / character 500–4 k / transient 4–12 k / air 10 k+ [PV].
- **Reverb.** Keep tails short under speech; a tail occupies the voice's room [HF].
- **Tonal SFX** (chimes, risers, arpeggios): match the bed's key, or stay non-tonal. Tell ElevenLabs the key, e.g. "in A minor" [VIB, DEAN].
- **Stereo.** UI sounds and impacts stay mono-centred. Pan only real lateral motion, and gently [SON, DEAN].

### 2.6 Variation (anti machine-gun)

- Rotate 3–4 variants of whoosh, pop, tap and tick. Per hit: rate 0.96–1.04 and gain ±2 dB; stacked same-class layers ±1–3 semitones [CF, WD, DEAN].
- **Runs** (lists, logo walls, pops): alternate 2 different samples (not byte-identical duplicates; md5-check the library), step the level down (0.40→0.37→…→0.25) and accelerate the intervals (8→3 f). When the run blurs (<3 f apart), replace it with one swoosh [SC S2 + 3.2].
- Counter steps rise in pitch; in a series of tease hits, the last one is louder [TV, VAR].
- A click run of 3–4 related items is one gesture. Clicks are earned only when the narration enumerates the items and each click lands on its word [YTE].
- Motifs are good (a signature toggle, a section whoosh), but they evolve by pitch, space, offset or layer count [YTE, VIB].
- One timbre family per video [CF, PV].

### 2.7 Density limits

- **Default for talking head + graphics:** 4–6 onsets per 10 s. Measured 2026-style reels show 3.5–5.3 with a high-band detector and ≈9 with two detectors (soft ones included). A real 43-s YTE short had 19 cues (4.4 per 10 s). VU: ~8 per 18 s reads as designed, ~20 as generic.
- **Dense or energetic mode:** 8–12 per 10 s, only when the graphic events really are that dense (dense 2025-style edits: 11–15).
- **Per-video caps for 30–45 s shorts:** lite ≤6, normal 10–14, dense 16–20 [TV].
- **Minimum spacing between separate cues:** ~150 ms. Anything closer becomes one layered gesture.
- **Hero limits:** 2–3 layered heroes per video [YTE]; ≤3 full-frame punches, ≥16 beats apart [SC R4]; the loudest impact is reserved for the logo or the reveal [PV]; 12 hits in a 30-s spot is the fatiguing maximum [CAL].
- Density should vary, keeping quiet conviction beats [NH, VIB].
- **The engine.** `bold` allows up to 12 cues per 10 s (`qa.py` expects 8–12) with a 0.12 s minimum gap; `measured` follows the style profile's density (fallback 3.5–5.3) with 0.5 s.

### 2.8 Music bed

- **Always music**, instrumental. For tech reels a dark, tense electronic underscore around 100 BPM works well; chill, warm or lounge beds do not (prompt in §3.5; the bundled `tense_a` … `tense_d` are such beds) [OWN]. Quieter, measured edits often use ambient electronic or lo-fi at 85–100 BPM [OWN]; PV suggests 110–128 BPM [PV].
- **Edit point.** Don't open on a quiet build. Compare 5-s sections and start on the strongest clean entrance. Fade in 0.25–0.3 s, fade out 1.2–1.3 s. The bed covers the whole cut with no silent tail, and is audible in ≈93 % of seconds [OWN].
- **Level.** ≈14 dB under the voice mean.
- **Ducking.** In continuous-speech reels (4 words/s, few gaps), a sidechain duck just becomes a permanent offset and pumps in the micro-gaps. Prefer a static level plus a light carve. If you do duck: 6–10 dB, attack 15–150 ms, release 400–450 ms, bridge gaps <0.6 s [YTE mix_music (thr 0.03, ratio 3, 15/450 ms), CAL].
- **Stops and drops** (use automation; the bed itself is prompted with "no drops"):
  - Before the ONE big reveal, stop the bed for 1 beat or dip it for 3–8 f. Optionally sweep a low-pass during the riser and open it on the hit.
  - The music comes back ON the reveal frame [PV, CF, VIB, HF].
  - In HyperFrames this is a `volume` lane plus an `fx.<lowpass>.frequency` lane (a BiquadFilter AudioParam, so it can be automated) [HF].
- **Structure.** An energy arc through stems or sections (pads → +drums → full at the reveal) [PV]. ElevenLabs Music `composition_plan` can shape chunks of 3–120 s [EL].
- **Ending.** A resolving phrase or a 1.2–1.3 s fade into the last frame. Never end mid-build. Measured reels typically end about 0.24 s after the last word, with the CTA held to the last frame [PV, CF, OWN].

### 2.9 Loudness and delivery

- **Target.** −14 LUFS integrated, true peak ≤ −1 dBTP. It matches typical measured reels (about −14.2 LUFS / −0.6 dBTP) and is recommended by VU, PV and CLL. Meta publishes no official number; −16 is a conservative alternative [APU, NH].
- **Recipe:**
  - Build the mix PCM with `amix=inputs=N:normalize=0` (the default `normalize=1` silently divides levels) and `adelay=<ms>:all=1`.
  - Measure I with `ebur128`, apply `volume=(−14 − I)dB`, then `alimiter=limit=0.84:level=0:attack=3:release=60`. `level=0` is mandatory, or alimiter auto-raises the gain. A limit of 0.89 can still measure ≈ −0.6 dBTP.
  - Alternative: two-pass `loudnorm=I=-14:TP=-1:LRA=11:...:linear=true` [OWN, PV, OK].
- **Voice processing before mixing** [OWN]: optional ElevenLabs Audio Isolation (`prep.py voice --isolate`; `--chain` skips it) → HPF 85 Hz, −2.5 dB at 260 Hz, +2.5 dB at 3.2 kHz, +1.5 dB at 6.5 kHz, de-esser, `acompressor` −19 dB 3:1 with makeup 4, `alimiter` 0.89.
- **Encode.** AAC 192–256 kbps, 48 kHz, `+faststart`.
- **Listen.** On a phone speaker at medium volume, not just headphones. Check the first word after the hook impact and the last syllable [CLL, NH, SMS].
- **SFX clips.** Don't loudnorm clips of 0.1–3 s; measure `max_volume` and apply direct gain [FHG].

### 2.10 Workflow and QA gates

1. Lock the picture first, since every retime means re-pinning [SC S3].
2. Build the event map: graphic events (from the composition timeline), layout changes, word anchors (alignment JSON).
3. Choose sounds by function and apply the density caps.
4. Write the cue table (JSON): `{t, kind, gain_db, anchor: "shot:X+0.12 | word:N", comment: "what lands on screen"}` [SC S2, YTE].
5. Resolve sounds library-first; generate the misses (§3); record `peak_offset`.
6. Mix (ffmpeg, or a HyperFrames root `<audio>` per cue).
7. Run the checks: audibility gate; peak table vs §2.3; sync (cross-correlation residual ≤0.5 f; cuts ≤3 f, ideally ≤1.5 f, in beat edits); loudness and true peak; a phone listen; the first word and the last syllable [YTE, SC, NH].
8. The human gate: show the person the reel is for the cue sheet and an audition mix before the final render (YTE's hard audit gate follows the same idea). They are the final judge; script and model scores are not approval.

In this skill `build.py` and `finish.py` automate steps 2–7, except the listening.

Useful commands:
```
ffmpeg -hide_banner -i f.wav -af volumedetect -f null - 2>&1 | grep -E "max_volume|mean_volume"
ffmpeg -hide_banner -i out.mp4 -af ebur128=peak=true -f null - 2>&1 | tail -14      # I, LRA, true peak
ffmpeg -i out.mp4 -vn -acodec pcm_s16le render.wav   # then numpy correlate against sfx sources
```

### 2.11 Conflicts between sources and the resolution chosen

| Conflict | Resolution |
|---|---|
| "Place SFX 2–3 f early" [HAI] vs "on the frame, ≤1 f" [SMS, CF, NH, VIB] | Transients 0–1 f early (EBU/ITU windows). Only pre-roll sounds (whoosh, riser, reverse) start early, aligned by their peak. |
| "Felt, not heard" [YTE brand; quiet 2026-style levels, −24…−30] vs "no sound" in tests [OWN] and "nothing there" [FHG] | Default to audible (§2.3, the engine's `bold` profile) and express taste through choice and density, not inaudibility. `measured` keeps the quiet levels for when you want them. |
| "No whoosh on every cut" [PV, NH, VU, dikshant] vs "a whoosh on layout changes plus fades are the basics" [OWN] | Whoosh on layout changes only, not on same-layout jump cuts. Rotate variants; use the soft version for minor changes. |
| Bed −26 dB (quiet 2026-style) vs 12–16 dB (tests) | ≈14 dB by default (the engine's `bold`: −15 dB); `measured` keeps ≈ −28 dB in the mix. |
| Synth SFX (numpy, ffmpeg) vs recorded or AI | Recorded or ElevenLabs. Synth was rejected in CF and FHG; a deliberate 8-bit style is the only exception. The bundled swell and sub hits are low-end shapes fitted to measurements, not imitations. |
| −14 vs −16 LUFS | −14 LUFS / ≤ −1 dBTP (the engine's master). |

---

## 3. ElevenLabs Sound Effects kit spec

### 3.1 API and limits

- `POST https://api.elevenlabs.io/v1/sound-generation`, header `xi-api-key` (the key comes from `ELEVENLABS_API_KEY`).
- Body: `{"text", "duration_seconds": 0.5–30, "prompt_influence": 0–1 (default 0.3), "loop": bool (v2 only), "model_id": "eleven_text_to_sound_v2"}`.
- Output: mp3 44.1 kHz by default; WAV 48 kHz is available for non-looping sounds. Try `?output_format=pcm_48000`; if the plan returns 403, use `mp3_44100_192` [EL, CAL].
- Cost ≈ 40 credits per second when the duration is set explicitly [EL].
- **At most 3 parallel requests** (the 4th gets a 429). The Music API allows at most 2 [OWN].
- Generation is non-deterministic. Keep a prompt log, generate 3–4 variants, and save rejects as possible layers [DEAN, CAL].

### 3.2 Prompt formula (six slots)

`[source/object] + [action] + [material/timbre] + [space: "dry, close-mic, no reverb"] + [envelope: "fast attack, peaks early, short decay" / "builds and stops at its loudest point"] + [modifier: "modern, clean, premium, readable on phone speakers"] + negatives ("no music, no voice, no melody, no metallic ring")`.

- 10–60 words, one event per prompt; multi-event prompts produce mush.
- Use the learned tokens: whoosh, impact, one-shot, loop, riser, braam, glitch, drone.
- prompt_influence 0.45–0.6 for UI and transitions, 0.3–0.4 for organic textures. Drop it to 0.2–0.25 and add "naturalistic, Foley" if the output sounds synthetic.
- Always set `duration_seconds` for sync assets; auto duration runs long for UI.
- Tonal sounds get a key and BPM: "in A minor, 100 BPM" [DEAN, CAL, EL].

### 3.3 Post-processing (every clip) and manifest

- `silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.005` (transient at ~0 s).
- `highpass=f=90` (skip for `impact_*` and `sub_drop`).
- Normalize to peak −3 dBFS (convention A; the bundled kit), or to −20 LUFS with a −1.5 dBFS ceiling (convention B). Pick one per library.
- `afade=t=out:d=0.12` (0.08 for clicks). 48 kHz stereo WAV.
- Manifest per file: `{id, class, variant, file, duration_s, peak_dbfs, lufs, peak_offset_s, prompt, influence, seed_note, used_in}`.
- md5 de-duplication, so "variants" aren't byte-identical [OWN, YTE, SC].
- `scripts/sfx_gen.py` already does the trim, the high-pass, the −3 dBFS peak and the fade.

### 3.4 Kit table

Durations are ≥0.5 s because that is the API minimum; trim afterwards.

| id | Prompt (short) | dur s | infl | var | Use |
|---|---|---|---|---|---|
| whoosh | Fast clean whoosh for a vertical video scene transition, a swish of air sweeping past the camera, smooth body in the low-mids with a little air on top, quick swell that peaks early and fades out, dry, no metallic ring, no bass boom, no music | 0.7 | 0.55 | 4 | layout change |
| whoosh_soft | Soft short airy whoosh, gentle movement of air for a subtle on-screen change, smooth and quiet, low-mid body, no hiss, no metallic ring, dry, no music | 0.5 | 0.5 | 3 | graphic swap, glint |
| whoosh_low | Deep muffled low-end whoosh, a short push of air with a soft low thump at the end, dark and warm, not bright, no hiss, dry, no music | 0.5 | 0.55 | 2 | hook punch-in, zoom |
| whoosh_reverse | Soft reversed air whoosh that swells up and cuts off cleanly at its loudest point, like a quick suck-back before a cut, low-mids, no metallic ring, no music | 0.8 | 0.5 | 2 | pre-lap, exits |
| riser_short / riser_long | Tension riser for a reveal, airy filtered noise and a synth tone rising steadily in pitch and volume and getting brighter, ends abruptly at its loudest point, no hit at the end, no cymbal, no music | 1.5 / 3.0 | 0.5 | 2+2 | big reveal |
| impact_hero | Cinematic impact hit for a logo or product reveal, sharp punchy transient, warm solid low-mid thud that stays audible on phone speakers, short deep sub boom with a smooth one-second decay, clean and powerful, no metallic clang, no distortion, no music | 1.4 | 0.5 | 3 | reveal, logo lockup |
| impact_soft | Soft warm low impact marking a key moment, rounded thud with a short natural tail, punchy but restrained, readable on small speakers, no big boom, no music | 0.8 | 0.5 | 3 | slammed title, key stat, payoff strike |
| sub_drop | Deep sub-bass drop, a clean falling low sine boom with a fast attack and a smooth one-second fade, no click, no distortion, no music | 1.2 | 0.5 | 1 | layer under impact_hero only |
| pop | Single short soft UI pop for an element appearing on screen, rounded bubble pop with a crisp clean attack, modern app, dry, no reverb, no music | 0.5 | 0.6 | 4 | graphic entrance, logo |
| tap | Single soft tap on a smartphone touch screen, short dry UI click with a tiny bit of body, modern and clean, no reverb, no music | 0.5 | 0.6 | 3 | cursor or finger press |
| toggle_on / toggle_off | UI switch toggle flipping on (off), crisp short mechanical click with a tiny upward (downward) tail, dry, no music | 0.5 | 0.6 | 1+1 | switches |
| typing_loop | Fast even typing on a quiet laptop keyboard, soft rapid key clicks, continuous with no pauses, dry close-mic, no voices, no music (loop=true) | 3.0 | 0.45 | 2 | type-on |
| key_enter | Single firm press of the Enter key on a laptop keyboard, one short dry click, close-mic, no music | 0.5 | 0.6 | 1 | submit |
| count_roll | Fast soft digital counter ticking, numbers rolling up quickly like a small odometer, even rapid ticks, dry, no music (loop=true) | 1.5 | 0.5 | 2 | count-up |
| count_lock | Short satisfying digital lock-in click with a soft bright ping as a number stops on its final value, dry, no music | 0.5 | 0.6 | 2 | count-up end |
| marker_draw | Felt-tip marker drawing one quick highlight stroke across paper, short squeaky marker swipe, dry close-mic, no music | 0.6 | 0.5 | 3 | highlight, underline |
| tick | Tiny soft digital tick, minimal clock tick in an app, dry, very short, no music | 0.5 | 0.6 | 3 | list rows, ring close |
| shimmer_reveal | Short bright shimmer sparkle rising, tiny glassy bell-like particles for a text or result reveal, clean and positive, short tail, no music | 1.0 | 0.5 | 2 | result appears, post-hit sparkle |
| success_chime | Soft positive success chime, two warm bell notes rising, modern app confirmation, clean, short tail, no music (add "in <bed key>") | 0.8 | 0.6 | 2 | done, check |
| error_buzz | Short low error buzz, access-denied UI sound, two quick descending muted tones, dry, not harsh, no music | 0.5 | 0.6 | 2 | red cross, fail |
| strike_scratch | Quick pen strike-through scratch across paper, one fast dry stroke, close-mic, no music | 0.5 | 0.5 | 2 | strike-through |
| ding | Short pleasant notification ding, new message received, single soft bell tone, clean, short tail, no music | 0.8 | 0.6 | 2 | mail or message arrives |
| send_swoosh | Message sent sound, short rising whoosh ending in a soft pop, clean modern app, no music | 0.7 | 0.6 | 1 | send |
| shutter | Smartphone camera shutter click, single, crisp and clean, dry, no music | 0.5 | 0.6 | 1 | screenshot, photo |
| cta_sting | Short bright three-note ascending synth arpeggio sting in <bed key>, positive and confident, clean pluck, ends cleanly with a short tail, no drums, no vocals | 1.0 | 0.5 | 2 | CTA |
| downlifter | Short downlifter, airy noise sweep falling in pitch and fading out smoothly, settling after a big hit, no music | 1.2 | 0.5 | 1 | after the reveal |
| glitch_gap | Short digital glitch stutter, quick electronic zap with a small pitch drop, dark and restrained, clean, not screechy, no music | 0.5 | 0.5 | 2 | speech gaps only |

- **Budget.** ≈ 25 ids × variants ≈ 55 s of audio ≈ 2,200 ElevenLabs credits per pass. Budget about 2× for rerolls.
- **Reuse.** The bundled kit (`assets/sfx`, see `sound-design.md` §7) already covers whoosh, whoosh_low, whoosh_soft, pop, click, tick, glitch, swipe, chime, ding, error, punch, shatter, impact, the sub hits, the opening swell, typing, count, riser_soft, tap, toggle, send, shutter, blip and reveal; it has no opening riser. `scripts/sfx_gen.py` has prompts for the engine's other classes. From this table, generate only what you miss (impact_hero, impact_soft, sub_drop, whoosh_reverse, riser_short/long, count_lock, marker_draw, success_chime, strike_scratch, cta_sting, downlifter), plus 2–3 extra variants for whoosh, pop and tap.
- **New sounds in the engine.** `finish.py` knows only its own classes (`sound-design.md` §5) and plays an unknown kind as a click. Put a new sound into the folder of the class it should play as, e.g. `impact_hero` variants into `<kit>/impact/`.

### 3.5 Music bed prompt (ElevenLabs Music)

`POST /v1/music` with `force_instrumental: true` and `music_length_ms` = the video length + 2 s. Prompt: "dark tense electronic underscore, ~100 BPM, pulsing sub bass, ticking hi-hats, suspenseful minor pads, no melody hooks, no vocals, no drops" [OWN]. Save the track and set `meta.music: "<path>"`.

- For an energy arc, use a `composition_plan` (music_v2), e.g. chunks of 8 s "tense pulse, sub + hats", 12 s "+ drums, building", the rest "full groove". Each chunk is 3–120 s.
- Do the pre-reveal stop with volume automation, not in the prompt.
- Option: `video_to_music` (music_v2) with the cut plus tags like "tense, electronic, minimal" [EL].
