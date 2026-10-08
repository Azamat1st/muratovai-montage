#!/usr/bin/env python3
"""Installs the muratovai-montage kit into Claude Code and proves it works.

  python3 install.py                   install / update everything, then render a 5-second test reel (up to 15 min the first time)
  python3 install.py --check           only report what is installed and what is missing (tools, keys, skills)
Options: --dest <skills dir> (default ~/.claude/skills) · --skip-selftest · --no-venv · --replace-hyperframes
On Windows call Python as `python` (or `py`): `python install.py`.

What it does:
  1. checks Python 3.9+, ffmpeg (x264 + VP9), Node 22+ and npx, and prints the install command for anything missing; on Windows
     it also notices a tool that winget installed but this window cannot see yet (then Claude Code must be restarted);
  2. copies skills/* into ~/.claude/skills: muratovai-montage (an older copy goes to ~/.claude/skills-backup) and the HyperFrames
     engine skills (kept as they are if you already have them); the user's montage-* style skills are never touched;
  3. creates the kit's own Python environment (~/.local/share/muratovai-montage/venv; Windows %LOCALAPPDATA%\\muratovai-montage\\venv):
     numpy, Pillow, yt-dlp, Demucs + soundfile, Playwright with its headless Chromium for site screenshots; OpenCV off macOS;
  4. creates ~/.config/muratovai-montage/keys.env for the API keys and reports which keys are found (never their values);
  5. downloads the pinned HyperFrames CLI and its Chrome, then runs the engine self-test.
  On macOS it also clears the download quarantine flag on the skill folder, so the bundled Apple Vision helpers can run.
Exit codes: 0 ready · 2 the engine works but the ElevenLabs key is missing · 1 something is broken.
Nothing is sent anywhere except package downloads (pip, npm, browsers).
"""
import datetime, glob, os, platform, re, shutil, subprocess, sys

KIT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(KIT, "skills")
NAME = "muratovai-montage"
MAC, WIN = sys.platform == "darwin", sys.platform == "win32"
OK, NO, WARN = "✓", "✗", "!"
PY = "python" if WIN else "python3"
KEYS_HINT = "~/.config/muratovai-montage/keys.env"
NEXT = ("NEXT (tell the user, in their language): 1) «Разбери монтаж @ник» with the Instagram @handle of a creator whose editing "
        "they like (or links to 2–5 reels, or the files)  2) /model → Opus  3) «Смонтируй в стиле @ник» + their video. "
        "Restart Claude Code if the new skills are not listed yet.")
KEYS_TEMPLATE = (
    "# API keys for the muratovai-montage kit. Paste each key right after '=' (no spaces, no quotes), then save the file.\n"
    "# Never share this file and never paste keys into a chat.\n"
    "# Required: ElevenLabs (speech-to-text of your videos and of the reels you analyse)\n"
    "ELEVENLABS_API_KEY=\n"
    "# Recommended: Apify (downloads the latest reels of an Instagram @handle; without it, give reel links or files)\n"
    "APIFY_TOKEN=\n")


def utf8_stdio():
    """✓/✗ and Cyrillic must survive a Windows pipe, whose default is the ANSI code page"""
    for s in (sys.stdout, sys.stderr):
        try:
            if (s.encoding or "").replace("-", "").lower() != "utf8": s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError): pass


def say(mark, msg): print(f"  {mark} {msg}", flush=True)


def head(msg): print(f"\n== {msg}", flush=True)


def home(path): return path.replace(os.path.expanduser("~"), "~")


def run(argv, **kw):
    try: return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    except (OSError, subprocess.SubprocessError) as e: return subprocess.CompletedProcess(argv, 127, "", str(e))


def version_of(path):
    try:
        with open(path, encoding="utf-8") as f: return f.read().strip()
    except OSError: return ""


def hint(tool, plat=sys.platform):
    table = {
        "darwin": {"ffmpeg": "brew install ffmpeg", "node": "brew install node", "python": "brew install python"},
        "win32": {"ffmpeg": "winget install -e --id Gyan.FFmpeg", "node": "winget install -e --id OpenJS.NodeJS.LTS",
                  "python": "winget install -e --id Python.Python.3.12"},
    }.get(plat, {"ffmpeg": "sudo apt install ffmpeg  (or your distro's package)", "node": "install Node 22+ from nodejs.org or with nvm",
                 "python": "sudo apt install python3 python3-venv"})
    return table.get(tool, "")


def hidden_tool(tool, environ=None, plat=sys.platform):
    """Windows: the path of a tool winget installed that this window cannot see yet (PATH is read when a window opens)"""
    if plat != "win32": return None
    env = os.environ if environ is None else environ
    local, prog = env.get("LOCALAPPDATA", ""), env.get("ProgramFiles", "")
    places = {"node": [(prog, ("nodejs", "node.exe")), (local, ("Programs", "nodejs", "node.exe"))],
              "ffmpeg": [(local, ("Microsoft", "WinGet", "Links", "ffmpeg.exe"))]}.get(tool, [])
    cands = [os.path.join(base, *parts) for base, parts in places if base]
    if tool == "ffmpeg" and local:
        cands += sorted(glob.glob(os.path.join(local, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "*", "bin", "ffmpeg.exe")))
    return next((c for c in cands if os.path.isfile(c)), None)


def missing(tool, label):
    """report a missing tool; 'restart' when Windows has it but this window cannot see it yet"""
    seen = hidden_tool(tool)
    if seen:
        say(NO, f"{label} is installed ({seen}) but this window does not see it yet → restart Claude Code, then run install.py again")
        return "restart"
    say(NO, f"{label} is missing → {hint(tool)}")
    return tool


def check_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"): return [missing("ffmpeg", "ffmpeg")]
    enc = run(["ffmpeg", "-hide_banner", "-encoders"]).stdout
    v = (run(["ffmpeg", "-version"]).stdout.split("\n") or [""])[0]
    lack = [e for e in ("libx264", "libvpx-vp9") if e not in enc]
    if lack: say(NO, f"{v[:40]}: no {', '.join(lack)} encoder → {hint('ffmpeg')} (a full build)"); return ["ffmpeg"]
    say(OK, v[:60]); return []


def check_node():
    node = shutil.which("node")
    if not node: return [missing("node", "Node.js")]
    v = run([node, "--version"]).stdout.strip(); major = int(re.sub(r"\D", "", v.split(".")[0]) or 0)
    if major < 22: say(NO, f"Node {v}: HyperFrames needs 22+ → {hint('node')}"); return ["node"]
    say(OK, f"Node {v}")
    if not shutil.which("npx"): say(NO, "npx is missing (it comes with Node.js)"); return ["npx"]
    return []


def check_tools():
    head("Tools")
    bad = []
    if sys.version_info < (3, 9): say(NO, f"Python {platform.python_version()}: 3.9+ is needed → {hint('python')}"); bad.append("python")
    else: say(OK, f"Python {platform.python_version()}")
    bad += check_ffmpeg() + check_node()
    if MAC and not shutil.which("swiftc"):
        say(WARN, "swiftc not found: only needed if the bundled Apple Vision helpers do not run (xcode-select --install)")
    if not MAC: say(WARN, "not macOS: the cut-out uses HyperFrames' local model and the face track uses OpenCV (check the head framing)")
    return sorted(set(bad))


def skills_dest(a):
    return os.path.abspath(os.path.expanduser(a[a.index("--dest") + 1])) if "--dest" in a else os.path.expanduser("~/.claude/skills")


def copy_skill(src, dst):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", ".venv"))


def install_one(src, dst, replace):
    """install one skill folder; an existing copy is kept, or (replace) moved to skills-backup next to the skills folder"""
    name = os.path.basename(dst)
    if not os.path.lexists(dst): copy_skill(src, dst); say(OK, f"{name}: installed"); return
    if not replace: say(OK, f"{name}: already installed, kept"); return
    if os.path.islink(dst): say(WARN, f"{name}: is a link to your own copy, left as is"); return
    backups = os.path.join(os.path.dirname(os.path.dirname(dst)), "skills-backup")
    os.makedirs(backups, exist_ok=True)
    bak = os.path.join(backups, f"{name}-{datetime.datetime.now():%Y%m%d-%H%M%S-%f}")
    shutil.move(dst, bak); copy_skill(src, dst); say(OK, f"{name}: updated (previous copy → {home(bak)})")


def install_skills(dest, replace_hf):
    head(f"Skills → {dest}")
    os.makedirs(dest, exist_ok=True)
    for name in sorted(os.listdir(SRC)):
        src = os.path.join(SRC, name)
        if os.path.isfile(os.path.join(src, "SKILL.md")): install_one(src, os.path.join(dest, name), name == NAME or replace_hf)
    rm = os.path.join(dest, NAME)
    if MAC: run(["xattr", "-dr", "com.apple.quarantine", rm])   # a downloaded archive marks every file; the Vision helpers must run
    for b in ("face_track", "person_mask"):
        p = os.path.join(rm, "scripts", b)
        if os.path.exists(p): os.chmod(p, 0o755)
    return rm


def venv_packages(plat=sys.platform):
    return ["numpy>=1.24", "Pillow>=10", "yt-dlp", "demucs", "soundfile", "playwright"] + ([] if plat == "darwin" else ["opencv-python-headless<5"])


def engine_env(rm):
    """the engine's own _env module: one definition of where the kit's environment lives, for the installer and the scripts"""
    sys.path.insert(0, os.path.join(rm, "scripts"))
    os.environ["REELS_NO_VENV"] = "1"
    import _env   # noqa: E402
    return _env


def screenshot_browser(py):
    """Playwright's headless Chromium for site screenshots (fetch_assets.py shot): optional, so a failure is only a warning"""
    r = run([py, "-m", "playwright", "install", "--only-shell", "chromium"], timeout=1200)
    if r.returncode: say(WARN, "site screenshots are unavailable (Playwright browser): " + (r.stderr or r.stdout).strip()[-300:]); return False
    say(OK, "browser for site screenshots is ready"); return True


def make_venv(rm):
    head("Python environment")
    env = engine_env(rm)
    v, py = env.venv_dir(), env.venv_python()
    if not os.path.exists(py):
        os.makedirs(os.path.dirname(v), exist_ok=True)
        r = run([sys.executable, "-m", "venv", v])
        if r.returncode:
            say(NO, "could not create a virtual environment: " + (r.stderr or r.stdout).strip()[-300:]
                + ("" if MAC or WIN else "\n      (Debian/Ubuntu: sudo apt install python3-venv)")); return None
    pkgs = venv_packages()
    run([py, "-m", "pip", "install", "-q", "--upgrade", "pip"], timeout=900)
    r = run([py, "-m", "pip", "install", "-q", "--upgrade", *pkgs], timeout=1800)
    if r.returncode: say(NO, "pip install failed: " + (r.stderr or r.stdout).strip()[-600:]); return None
    say(OK, f"{', '.join(re.split('[<>=]', p)[0] for p in pkgs)} → {home(v)}")
    screenshot_browser(py)
    return py


def key_opener(path, plat=sys.platform):
    return f"open -e '{path}'" if plat == "darwin" else (f'notepad "{path}"' if plat == "win32" else f"nano '{path}'")


def keys(rm):
    head("API keys (values are never printed)")
    sys.path.insert(0, os.path.join(rm, "scripts"))
    import common   # noqa: E402
    f = common.KEYS_FILE
    if not os.path.exists(f):
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "w", encoding="utf-8", newline="\n") as h: h.write(KEYS_TEMPLATE)
        try: os.chmod(f, 0o600)
        except OSError: pass
        say(OK, f"created {home(f)}")
    miss = []
    for name, need in (("ELEVENLABS_API_KEY", "required"), ("APIFY_TOKEN", "recommended: Instagram @handle downloads")):
        v, src = common.find_key(name)
        if v: say(OK, f"{name}: found ({src})"); continue
        say(NO if need == "required" else WARN, f"{name}: not set ({need})")
        if need == "required": miss.append(name)
    if miss: print(f"      → the user pastes the key into {home(f)} ({key_opener(f)}), then: {PY} install.py --check")
    return miss


def check_screenshots(rm):
    py = engine_env(rm).venv_python()
    if not os.path.exists(py): say(WARN, f"the kit's Python environment is missing: run {PY} install.py"); return
    ok = run([py, "-c", "import playwright"]).returncode == 0
    say(OK if ok else WARN, "Playwright (site screenshots)" + ("" if ok else f": missing, run {PY} install.py again"))


def hyperframes():
    head("HyperFrames renderer")
    if not shutil.which("npx"): say(NO, "npx is missing"); return False
    import common   # noqa: E402  (keys() put the engine's scripts folder on sys.path)
    r = run(common.hf("--version"), timeout=600)
    if r.returncode: say(NO, "npx could not start HyperFrames: " + (r.stderr or r.stdout).strip()[-400:]); return False
    say(OK, f"{common.HF} → {r.stdout.strip().splitlines()[-1] if r.stdout.strip() else 'ok'}")
    r = run(common.hf("browser", "ensure"), timeout=900)
    if r.returncode: say(NO, "Chrome for rendering could not be installed: " + (r.stderr or r.stdout).strip()[-400:]); return False
    say(OK, "Chrome for rendering is ready"); return True


def selftest(py, rm):
    head("Engine self-test (a 5-second synthetic reel, no keys, 1–3 minutes)")
    out = os.path.join(os.path.expanduser("~"), "reels", "_selftest")
    env = dict(os.environ); env.pop("REELS_NO_VENV", None)
    if WIN: env["PYTHONUTF8"] = "1"
    r = subprocess.run([py or sys.executable, os.path.join(rm, "scripts", "selftest.py"), "--out", out], env=env)
    if r.returncode: say(NO, "self-test failed: read the error above"); return False
    say(OK, f"test reel → {home(os.path.join(out, 'out', 'selftest_light.mp4'))}"); return True


def installed(dest):
    head(f"Installed skills in {dest}")
    others = sorted(x for x in os.listdir(SRC) if x != NAME) if os.path.isdir(SRC) else []
    for n in [NAME] + others:
        ver = version_of(os.path.join(dest, n, "VERSION"))
        say(OK if os.path.exists(os.path.join(dest, n, "SKILL.md")) else NO, n + (f" {ver}" if ver else ""))
    made = sorted(x for x in (os.listdir(dest) if os.path.isdir(dest) else []) if x.startswith("montage-"))
    if made: say(OK, "your style skills: " + ", ".join(made))


def check_only(dest, bad):
    installed(dest)
    rm = os.path.join(dest, NAME)
    miss = keys(rm) if os.path.isdir(rm) else [f"{NAME} is not installed"]
    if os.path.isdir(rm): check_screenshots(rm)
    todo = [x for x in bad if x != "restart"] + miss + (["restart Claude Code"] if "restart" in bad else [])
    print("\nREADY" if not todo else "\nNOT READY: " + ", ".join(todo))
    raise SystemExit(0 if not todo else 1)


def finish_not_ready(bad):
    if "restart" in bad: print(f"\nNOT READY: restart Claude Code (close it and open it again), then run {PY} install.py again.")
    else: print(f"\nNOT READY: install {', '.join(bad)} (commands above), then run {PY} install.py again.")
    raise SystemExit(1)


def main():
    utf8_stdio()
    a = sys.argv[1:]
    if a and a[0] in ("-h", "--help"): raise SystemExit(__doc__)
    dest = skills_dest(a)
    print(f"{NAME} kit {version_of(os.path.join(KIT, 'VERSION')) or '?'} · {platform.system()} {platform.machine()} · skills → {dest}")
    bad = check_tools()
    if "--check" in a: check_only(dest, bad)
    rm = install_skills(dest, "--replace-hyperframes" in a)
    py = None if "--no-venv" in a else make_venv(rm)
    miss = keys(rm)
    if bad: finish_not_ready(bad)
    hf_ok = hyperframes()
    test_ok = selftest(py, rm) if hf_ok and "--skip-selftest" not in a else None
    installed(dest)
    engine = hf_ok and test_ok is not False and (py is not None or "--no-venv" in a)
    if engine and not miss: print("\nREADY: engine tested, keys found")
    elif engine: print(f"\nENGINE OK · NOT READY: the user adds {', '.join(miss)} to {KEYS_HINT} (open it for them), then run: {PY} install.py --check")
    else: print(f"\nNOT READY: fix the errors above and run {PY} install.py again")
    print(NEXT)
    raise SystemExit(0 if engine and not miss else 2 if engine else 1)


if __name__ == "__main__":
    main()
