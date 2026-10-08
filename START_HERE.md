# START HERE — instructions for Claude Code

You have been given the **muratovai-montage kit**. It edits a talking-head video into a fast, graphics-driven reel (cuts,
captions, company logos, site screenshots, mini-interfaces on the words, music, sound design) in the editing style **the user
chooses**. The kit has no style of its own: the user names an Instagram creator they like (`@handle`) or gives 2–5 of their
reels, the skill measures them and saves the style as a new skill `montage-<handle>`, then edits the user's videos in it. The
engine is HyperFrames (HTML + GSAP → mp4).

Talk to the user in their language (usually Russian or Uzbek), briefly, without technical detail unless they ask. Never print
or echo API keys and never ask the user to paste them into the chat.

The flow, as users type it:
1. «Установи скилл» / «Skillni oʻrnat» + the link https://github.com/Azamat1st/muratovai-montage (or a zip archive of the kit) → **1. Install**.
2. «Разбери монтаж @ник» / «@nik montajini tahlil qil» (or links to 2–5 reels, or the files) → part A of
   `muratovai-montage/SKILL.md`.
3. Model: `/model` → Opus.
4. «Смонтируй в стиле @ник» / «@nik uslubida montaj qil» + a video → part B of `muratovai-montage/SKILL.md`.
5. «Обнови скилл» / «Skillni yangila» → **3. Update**.

## 0. Python first

On Windows, Claude Code runs commands in Git Bash: call Python as `python` (or `py`), never `python3`, everywhere in this kit.
If `python --version` fails or opens the Microsoft Store, run `winget install -e --id Python.Python.3.12`, then ask the user
to restart Claude Code (close it and open it again) and go on. On macOS use `python3`; if macOS offers to install the command
line developer tools, the user clicks Install.

## 1. Install

1. Download the kit into a permanent folder, not a temp one (`curl` and `unzip` are there on macOS and in Git Bash on Windows):
   `mkdir -p ~/muratovai-montage-kit && curl -fsSL https://github.com/Azamat1st/muratovai-montage/archive/refs/heads/main.zip -o ~/muratovai-montage-kit/kit.zip && unzip -oq ~/muratovai-montage-kit/kit.zip -d ~/muratovai-montage-kit && rm ~/muratovai-montage-kit/kit.zip`.
   The kit is then in `~/muratovai-montage-kit/muratovai-montage-main/`. If the user gave a zip archive instead of the link,
   unpack that one: `unzip -o <archive>.zip -d ~/muratovai-montage-kit` (on Windows without `unzip`:
   `powershell -Command "Expand-Archive -Force '<archive>.zip' \"$HOME/muratovai-montage-kit\""`) and use the folder it
   creates in the commands below.
2. Run `python3 ~/muratovai-montage-kit/muratovai-montage-main/install.py` (Windows: `python …`) with the Bash timeout set to
   600000 ms and wait for its last line; do not start a second copy while it runs. The first run takes up to 15 minutes: it
   copies the skills into `~/.claude/skills`, sets up its own Python environment (Demucs, a headless browser for site
   screenshots), downloads the pinned HyperFrames renderer and its Chrome (≈200 MB) and renders a 5-second test reel. If the
   timeout ends first, run it again: finished steps are quick the second time.
   Last line: `READY` (exit 0) · `ENGINE OK · NOT READY` (exit 2: only the ElevenLabs key is missing, normal on a first run) ·
   `NOT READY` (exit 1: read the errors).
3. Fix what it reports, then run `install.py --check`:
   - **ffmpeg / Node 22 missing**: macOS `brew install ffmpeg node`; if Homebrew itself is missing, ask the user to paste the
     one-line command from https://brew.sh into the Terminal app themselves (it needs their Mac password), then go on.
     Windows: `winget install -e --id Gyan.FFmpeg` and `winget install -e --id OpenJS.NodeJS.LTS`.
   - **"installed but this window does not see it yet"** (Windows): ask the user to restart Claude Code, then run
     `install.py` again.
   - **Keys**: the installer creates `~/.config/muratovai-montage/keys.env`. Open it for the user (macOS `open -e <file>`,
     Windows `notepad <file>`), ask them to paste the ElevenLabs key (required) and the Apify token (recommended: it downloads
     reels by @handle) after the `=` signs, save and tell you. `README.md` says where to get both. Then `install.py --check`.
   - **Render fails because Chrome exits at once**: the shell is sandboxed; run the self-test with the sandbox off, or ask the
     user to run `python3 ~/.claude/skills/muratovai-montage/scripts/selftest.py --out ~/reels/_selftest` in their terminal.
4. When the engine is OK, tell the user in 3–4 lines: installed, the test reel rendered (offer to open
   `~/reels/_selftest/out/selftest_light.mp4`), and the next prompt: «Разбери монтаж @ник» with the Instagram handle of a
   creator whose editing they like. Suggest `/model` → Opus.

If the new skills do not show up in this session, read `~/.claude/skills/muratovai-montage/SKILL.md` directly and follow it;
after a restart of Claude Code they are listed.

## 2. Before each step, ask for what is missing

`muratovai-montage/SKILL.md` → "Ask first" lists it. Ask in one short message, then work without further questions. If the
user asks to edit before they have a style, explain in one line that the style comes from a creator they like and ask for
the @handle (or links) first.

## 3. Update

The user says «обнови скилл». Download the kit again with the same command (step 1.1 overwrites the old copy; or unpack
the newer archive the user gave), run `install.py` again (step 1.2) and report the version from its first line. It replaces the engine (the previous copy goes to
`~/.claude/skills-backup`) and keeps the keys, the user's `montage-*` style skills and their projects in `~/reels`.

## What is in this folder

```
START_HERE.md    this file (for Claude)          README.md    for the person (Russian and Uzbek)
install.py       installer and checker           VERSION      the kit version
skills/          muratovai-montage (the engine) · HyperFrames engine skills (Apache-2.0)
```
