"""Runs the calling script in the kit's own Python environment when install.py has created one, and in UTF-8 everywhere.

The environment holds numpy, Pillow, yt-dlp (and OpenCV off macOS), so the scripts never depend on, or change, the system
Python. Without it (REELS_NO_VENV=1, or no install.py run) the scripts use whatever `python3` started them.
Location: $REELS_VENV, else ~/.local/share/muratovai-montage/venv (Windows: %LOCALAPPDATA%\\muratovai-montage\\venv).
On Windows a script is re-run in Python's UTF-8 mode (PYTHONUTF8=1): files and pipes then default to UTF-8 instead of the
ANSI code page, so Cyrillic and Uzbek (oʻ, gʻ) text survives. The output streams are switched to UTF-8 on every OS.
"""
import os
import subprocess
import sys


def venv_dir():
    d = os.environ.get("REELS_VENV")
    if d: return os.path.abspath(os.path.expanduser(d))
    if sys.platform == "win32": base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
    else: base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "muratovai-montage", "venv")


def venv_python():
    v = venv_dir()
    return os.path.join(v, "Scripts", "python.exe") if sys.platform == "win32" else os.path.join(v, "bin", "python")


def _inside(v):
    try: return os.path.samefile(sys.prefix, v)
    except OSError: return False


def reexec_target(venv_py, venv_ok, inside, platform, utf8_mode, current):
    """the Python that must re-run this script: the kit's environment, or (Windows) the same Python in UTF-8 mode; None to go on"""
    if venv_ok and not inside: return venv_py
    if platform == "win32" and not utf8_mode: return current
    return None


def child_env(base=None, platform=None):
    """environment of the re-run: it never re-enters ensure(); on Windows it starts in Python's UTF-8 mode"""
    env = dict(os.environ if base is None else base)
    env["REELS_NO_VENV"] = "1"
    if (platform or sys.platform) == "win32": env["PYTHONUTF8"] = "1"
    return env


def utf8_stdio():
    """print Cyrillic, Uzbek and ✓ through any pipe: a Windows pipe defaults to the ANSI code page"""
    for s in (sys.stdout, sys.stderr):
        try:
            if (s.encoding or "").replace("-", "").lower() != "utf8": s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError): pass


def ensure():
    if os.environ.get("REELS_NO_VENV") == "1": return
    py, v = venv_python(), venv_dir()
    target = reexec_target(py, os.path.exists(py), _inside(v), sys.platform, sys.flags.utf8_mode, sys.executable)
    if not target: return
    argv = [target, os.path.abspath(sys.argv[0])] + sys.argv[1:]
    env = child_env()
    if sys.platform == "win32": raise SystemExit(subprocess.call(argv, env=env))
    os.execve(target, argv, env)


utf8_stdio()
ensure()
