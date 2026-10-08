#!/usr/bin/env python3
"""SFX timing vs visual changes in a style profile folder: transients in the background stem (voice removed, needs
`analyze_reference.py <dir> stems`) matched against visual beats (scene score > 0.1).

  python3 sfx_probe.py <dir>      → prints per-reel onsets per 10 s and how many visual beats carry a sound; writes work/<id>/sfx_probe.json
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import json, glob, os, sys, wave, statistics as st
try:
    import numpy as np
except ImportError:
    raise SystemExit("this script needs numpy and Pillow: python3 -m pip install -r requirements.txt (in the skill folder)")
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): raise SystemExit(__doc__)
D = os.path.abspath(os.path.expanduser(sys.argv[1]))
def load(f):
    with wave.open(f) as wf:
        n, ch, sr = wf.getnframes(), wf.getnchannels(), wf.getframerate(); a = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    return a.reshape(-1, ch).mean(axis=1), sr
rows = []
for d in sorted(glob.glob(f"{D}/work/*/stems/no_vocals.wav")):
    rid = d.split(os.sep)[-3]; bg, sr = load(d); voc, _ = load(d.replace("no_vocals", "vocals"))
    hop = int(sr * 0.01); nwin = len(bg) // hop
    # high band energy via first difference (cheap high-pass)
    hp = np.diff(bg, prepend=0.0)
    e_hp = np.array([np.sqrt(np.mean(hp[i*hop:(i+1)*hop] ** 2)) + 1e-9 for i in range(nwin)]); db_hp = 20 * np.log10(e_hp)
    e = np.array([np.sqrt(np.mean(bg[i*hop:(i+1)*hop] ** 2)) + 1e-9 for i in range(nwin)]); db = 20 * np.log10(e)
    ev = np.array([np.sqrt(np.mean(voc[i*hop:(i+1)*hop] ** 2)) + 1e-9 for i in range(nwin)]); dbv = 20 * np.log10(ev)
    on = []
    for i in range(10, nwin - 2):
        base = np.median(db_hp[i-10:i])
        if db_hp[i] - base > 10 and db_hp[i] > -55 and db_hp[i] >= db_hp[i-1] and db_hp[i] >= db_hp[i+1]:
            if not on or i*0.01 - on[-1] > 0.12: on.append(round(i*0.01, 2))
    sc = json.load(open(f"{D}/work/{rid}/scenes.json"))
    beats = [t for t, s in zip(sc["t"], sc["score"]) if s > 0.1]; m = []
    for t in beats:
        if not m or t - m[-1] > 0.2: m.append(t)
    beats = m
    near = lambda t, L, tol: any(abs(t - x) <= tol for x in L)
    b_with = sum(1 for b in beats if near(b, on, 0.1)); o_with = sum(1 for o in on if near(o, beats, 0.1))
    dur = len(bg) / sr
    rows.append((rid, len(on), round(len(on) / dur * 10, 1), len(beats), round(b_with / max(len(beats), 1), 2), round(o_with / max(len(on), 1), 2)))
    json.dump(dict(onsets=on, beats=beats), open(f"{D}/work/{rid}/sfx_probe.json", "w"))
if not rows: raise SystemExit(f"no stems in {D}/work/*/stems — run analyze_reference.py {D} stems first (needs Demucs)")
print(f"{'reel':18} onsets per10s beats beats_w_sfx sfx_on_beats")
for r in rows: print(f"{r[0]:18} {r[1]:6} {r[2]:6} {r[3]:5} {r[4]:11} {r[5]:12}")
print("median beats_with_sfx", st.median(r[4] for r in rows), " median sfx_on_beats", st.median(r[5] for r in rows), " median onsets/10s", st.median(r[2] for r in rows))
