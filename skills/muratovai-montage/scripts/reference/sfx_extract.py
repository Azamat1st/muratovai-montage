#!/usr/bin/env python3
"""Pull every sound effect out of the reference reels of a style profile folder.

  python3 sfx_extract.py <dir>
Input: <dir>/work/<id>/stems/no_vocals.wav (Demucs: music bed + SFX, voice removed), stems/vocals.wav, scenes.json
(from analyze_reference.py <dir> prep + stems). Output: <dir>/sfx/clips/<id>_<t>.wav (each event, bed included) and
<dir>/sfx/events.json (features + timing vs cuts). The clips are for your private analysis only; do not ship them.
An event = the background rises ≥ 5 dB above its own 3-second running median (broadband) or ≥ 8 dB in the >2 kHz band."""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import glob, json, os, sys, wave
try:
    import numpy as np
except ImportError:
    raise SystemExit("this script needs numpy and Pillow: python3 -m pip install -r requirements.txt (in the skill folder)")
from numpy.lib.stride_tricks import sliding_window_view as swv

HERE = None; OUT = None
HOP, WIN = 441, 1024   # 10 ms hop at 44.1 kHz


def load(f):
    with wave.open(f) as w:
        n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate(); a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    return a.reshape(-1, ch).mean(axis=1), sr


def save(path, a, sr):
    a = np.clip(a, -1, 1); b = (a * 32767).astype(np.int16)
    with wave.open(path, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(b.tobytes())


def frames_db(x, sr):
    n = (len(x) - WIN) // HOP; idx = np.arange(WIN)[None, :] + HOP * np.arange(n)[:, None]
    fr = x[idx] * np.hanning(WIN)[None, :]; S = np.abs(np.fft.rfft(fr, axis=1)) ** 2; f = np.fft.rfftfreq(WIN, 1 / sr)
    tot = 10 * np.log10(S.sum(1) / WIN + 1e-12); hi = 10 * np.log10(S[:, f > 2000].sum(1) / WIN + 1e-12)
    lo = 10 * np.log10(S[:, f < 150].sum(1) / WIN + 1e-12)
    cen = (S * f[None, :]).sum(1) / (S.sum(1) + 1e-12)
    flat = np.exp(np.mean(np.log(S[:, 1:] + 1e-12), 1)) / (np.mean(S[:, 1:], 1) + 1e-12)
    return tot, hi, lo, cen, flat


def running_median(v, half=150):
    p = np.pad(v, (half, half), mode="edge"); return np.median(swv(p, 2 * half + 1), axis=1)


def main():
    allev = []
    for d in sorted(glob.glob(f"{HERE}/work/*/stems/no_vocals.wav")):
        rid = d.split(os.sep)[-3]; bg, sr = load(d); vo, _ = load(d.replace("no_vocals", "vocals"))
        tot, hi, lo, cen, flat = frames_db(bg, sr); vtot = frames_db(vo, sr)[0]
        speech = np.median(vtot[vtot > np.percentile(vtot, 40)])
        bt, bh = running_median(tot), running_median(hi)
        on = ((tot - bt > 5) & (tot > -58)) | ((hi - bh > 8) & (hi > -62))
        ev, i, n = [], 0, len(on)
        while i < n:
            if not on[i]: i += 1; continue
            j = i
            while j + 1 < n and (on[j + 1] or (j + 6 < n and on[j + 1:j + 7].any())): j += 1   # bridge gaps < 60 ms
            ev.append((i, j)); i = j + 1
        scenes = json.load(open(f"{HERE}/work/{rid}/scenes.json")) if os.path.exists(f"{HERE}/work/{rid}/scenes.json") else []
        pairs = list(zip(scenes.get("t", []), scenes.get("score", []))) if isinstance(scenes, dict) else [(s["t"], s["score"]) for s in scenes]
        cuts = [t for t, sc in pairs if sc > 0.3]; changes = [t for t, sc in pairs if sc > 0.1]
        for (i, j) in ev:
            t0, t1 = i * HOP / sr, (j + 1) * HOP / sr + WIN / sr
            if t1 - t0 < 0.03: continue
            seg = slice(i, j + 1); pk = int(np.argmax(tot[seg])) + i
            a0, a1 = max(0, int((t0 - 0.06) * sr)), min(len(bg), int(min(t1 + 0.25, t0 + 2.5) * sr))
            clip = bg[a0:a1]; name = f"{rid}_{t0:07.3f}.wav"; save(f"{OUT}/{name}", clip, sr)
            peak = 20 * np.log10(np.max(np.abs(bg[int(t0 * sr):int(t1 * sr) + 1])) + 1e-9)
            vo_act = float(np.mean(vtot[seg] > speech - 12))   # share of the event where the voice is talking
            cen_seg = cen[seg]; slope = float(np.polyfit(np.arange(len(cen_seg)), cen_seg, 1)[0] * 100) if len(cen_seg) > 3 else 0.0
            nc = min(cuts, key=lambda c: abs(c - t0)) if cuts else None; nv = min(changes, key=lambda c: abs(c - t0)) if changes else None
            allev.append(dict(file=name, reel=rid, t0=round(t0, 3), t1=round(t1, 3), dur=round(t1 - t0, 3), t_peak=round(pk * HOP / sr, 3),
                              peak_rel_voice=round(peak - speech, 1), rise_db=round(float(np.max(tot[seg] - bt[seg])), 1),
                              hi_rise_db=round(float(np.max(hi[seg] - bh[seg])), 1), low_share_db=round(float(np.max(lo[seg]) - np.max(tot[seg])), 1),
                              centroid=int(np.mean(cen_seg)), centroid_slope_hz_s=int(slope), flatness=round(float(np.mean(flat[seg])), 3),
                              voice_overlap=round(vo_act, 2), cut_off_ms=int((t0 - nc) * 1000) if nc is not None else None,
                              change_off_ms=int((t0 - nv) * 1000) if nv is not None else None))
        print(rid, len([e for e in allev if e["reel"] == rid]), "events", flush=True)
    json.dump(allev, open(f"{HERE}/sfx/events.json", "w"), indent=0)
    print("total", len(allev))


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): raise SystemExit(__doc__)
    HERE = os.path.abspath(os.path.expanduser(sys.argv[1])); OUT = f"{HERE}/sfx/clips"; os.makedirs(OUT, exist_ok=True)
    if not glob.glob(f"{HERE}/work/*/stems/no_vocals.wav"): raise SystemExit(f"no stems in {HERE}/work/*/stems — run analyze_reference.py {HERE} stems first (needs Demucs)")
    main()
