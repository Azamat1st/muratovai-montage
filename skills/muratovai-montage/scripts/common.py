"""Shared helpers for the muratovai-montage scripts: skill paths, API keys, the pinned HyperFrames CLI, style profiles.

API keys are never printed and never written anywhere by the scripts. Lookup order for a key NAME:
  1. the environment variable NAME;
  2. ~/.config/muratovai-montage/keys.env (NAME=value lines; install.py creates it, the user pastes the key);
  3. an `export NAME=...` line in ~/.zshrc, ~/.zprofile, ~/.bashrc, ~/.bash_profile or ~/.profile (a key added there after
     the agent's shell started is still found);
  4. ~/.env/<service>.key (one key per file, e.g. ~/.env/openai.key).
HTTP calls that need a key pass it to curl on stdin (`-H @-`), so the key does not show up in the process list either.
"""
import json, os, re, shutil, subprocess, sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(SCRIPTS, ".."))
DEFAULT_STYLE = "_defaults"   # engine fallback numbers, not a style: every edit should name a style profile

KEYS = {
    "OPENAI_API_KEY": "OpenAI: only the optional audio classifier in reference/sfx_classify.py (this fork does not need it)",
    "ELEVENLABS_API_KEY": "ElevenLabs: Scribe transcription (prep.py, analyze_reference.py words), voice isolation and SFX generation",
    "APIFY_TOKEN": "Apify: Instagram downloads in reference/fetch_reels.py (yt-dlp is used when it is not set)",
    "OPENROUTER_API_KEY": "OpenRouter: optional Gemini classifier in reference/sfx_classify.py",
}


KEYS_FILE = os.path.expanduser("~/.config/muratovai-montage/keys.env")
RC_FILES = ("~/.zshrc", "~/.zprofile", "~/.bashrc", "~/.bash_profile", "~/.profile")
KEY_FILES = {"OPENAI_API_KEY": "openai", "ELEVENLABS_API_KEY": "elevenlabs", "APIFY_TOKEN": "apify", "OPENROUTER_API_KEY": "openrouter"}


def _clean(v):
    v = v.strip().strip('"').strip("'").strip()
    return "" if (not v or "$" in v or "`" in v or v.startswith("<") or v.endswith("...")) else v   # skip templates and shell expansions


def find_key(name):
    """(value, source) of an API key, or (None, None); the value is never printed"""
    v = _clean(os.environ.get(name) or "")
    if v: return v, "environment"
    pat = re.compile(rf"^\s*(?:export\s+)?{re.escape(name)}\s*=\s*(.+?)\s*$")
    for f in (KEYS_FILE,) + tuple(os.path.expanduser(x) for x in RC_FILES):
        try: lines = open(f, encoding="utf-8", errors="ignore").read().splitlines()
        except OSError: continue
        for line in reversed(lines):   # the last assignment wins, as in a shell
            m = pat.match(line)
            if m and not line.lstrip().startswith("#"):
                v = _clean(m.group(1).split(" #")[0])
                if v: return v, f.replace(os.path.expanduser("~"), "~")
    svc = KEY_FILES.get(name)
    if svc:
        f = os.path.expanduser(f"~/.env/{svc}.key")
        try:
            v = _clean(open(f).read())
            if v: return v, f"~/.env/{svc}.key"
        except OSError: pass
    return None, None


def env_key(name, required=True):
    """the value of an API key (see the lookup order above); exits with a readable message when a required key is missing"""
    v, _ = find_key(name)
    if v: return v
    if not required: return None
    raise SystemExit(f"{name} is not set. It is needed for {KEYS.get(name, name)}.\n"
                     f"Paste it after {name}= in {KEYS_FILE.replace(os.path.expanduser('~'), '~')} (install.py creates the file), "
                     f"or export {name}=... in your shell, then run the command again.")


# ---------------------------------------------------------------- HyperFrames CLI, pinned to the tested line
HF = os.environ.get("REELS_HYPERFRAMES", "hyperframes@0.8.78")   # the exact version the kit was tested with


def hf(*args):
    """argv for the pinned HyperFrames CLI through npx (npx.cmd on Windows)"""
    return [shutil.which("npx") or "npx", "--yes", HF, *[str(a) for a in args]]


def sh(*a, check=True, **k):
    r = subprocess.run(list(a), capture_output=True, text=True, **k)
    if check and r.returncode: raise SystemExit(f"FAILED {' '.join(str(x) for x in a[:4])} …\n{(r.stderr or r.stdout)[-1500:]}")
    return r


def curl(url, header, *args, timeout=240):
    """curl with one secret header passed on stdin (never on the command line); returns stdout"""
    r = subprocess.run(["curl", "-s", "--max-time", str(timeout), url, "-H", "@-", *args], input=header + "\n", capture_output=True, text=True)
    if r.returncode: raise SystemExit(f"curl failed ({r.returncode}) for {url}: {r.stderr[-400:]}")
    return r.stdout


def gpu_env():
    """HyperFrames renders with the hardware GPU on macOS (software rendering can time out on laptops); elsewhere it auto-detects"""
    env = dict(os.environ)
    if sys.platform == "darwin": env.setdefault("PRODUCER_BROWSER_GPU_MODE", "hardware")
    return env


# ---------------------------------------------------------------- style profiles
def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def style_dir(spec=None, project=None):
    """resolve a style profile: a name in styles/ (_defaults) or a folder path (absolute, ~, relative to the project or cwd)"""
    spec = str(spec or os.environ.get("REELS_STYLE") or DEFAULT_STYLE)
    p = os.path.expanduser(spec); cands = []
    if os.path.isabs(p): cands.append(p)
    else:
        if project: cands.append(os.path.join(project, p))
        cands += [os.path.abspath(p), os.path.join(SKILL, "styles", p)]
    for c in cands:
        if os.path.isfile(os.path.join(c, "style.json")) or os.path.isfile(os.path.join(c, "style-bible.md")): return os.path.abspath(c)
    raise SystemExit(f"style profile '{spec}' not found (looked for style.json or style-bible.md in: {', '.join(cands)})")


def styles_roots():
    """skill roots to search for packaged montage-<handle> style skills: $REELS_STYLES, a list of paths separated by ':'
    (~ expanded, empty entries dropped). Agent-neutral (R26): unset, this falls back to wherever Claude Code keeps
    skills, so existing installs keep working; under Codex it is set to $CODEX_HOME/skills instead."""
    raw = os.environ.get("REELS_STYLES") or os.path.join("~", ".claude", "skills")
    return [os.path.expanduser(p) for p in raw.split(":") if p]


def user_styles():
    """style profiles the user has made: montage-* skills under the style roots (styles_roots()), and folders in
    ~/reels/styles (and $REELS_PROJECTS/styles), which are not skill roots and so are not filtered by name"""
    roots = [(r, True) for r in styles_roots()] + [(os.path.expanduser("~/reels/styles"), False)]
    if os.environ.get("REELS_PROJECTS"): roots.append((os.path.join(os.path.expanduser(os.environ["REELS_PROJECTS"]), "styles"), False))
    out = []
    for r, is_skill_root in roots:
        if not os.path.isdir(r): continue
        for n in sorted(os.listdir(r)):
            d = os.path.join(r, n)
            if (is_skill_root and not n.startswith("montage-")) or not os.path.isfile(os.path.join(d, "style.json")): continue
            out.append(d)
    return out


def load_style(spec=None, project=None):
    """style.json of a profile merged over the engine defaults, so a partial profile still has every target"""
    base = json.load(open(os.path.join(SKILL, "styles", DEFAULT_STYLE, "style.json")))
    d = style_dir(spec, project); f = os.path.join(d, "style.json")
    s = _merge(base, json.load(open(f))) if os.path.isfile(f) and os.path.realpath(d) != os.path.realpath(os.path.join(SKILL, "styles", DEFAULT_STYLE)) else base
    if not os.path.isfile(f): s = dict(s, name=os.path.basename(d))
    s["_dir"] = d
    return s


def era_view(style, era):
    """targets for an era variant of the style (e.g. meta.era = "2025"), falling back to the main targets"""
    ov = (style.get("eras") or {}).get(str(era))
    return _merge(style, ov) if ov else style
