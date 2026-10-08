#!/usr/bin/env python3
"""Procedural sounds (numpy only, deterministic, free): the signature opening swell and sub hits shaped to measurements of the
measurements of popular talking-head reels, plus simple stand-ins for the bed-like classes the engine needs (typing, count, riser_soft).

  python3 sfx_synth.py [--out <kit folder>]     → <out>/open/open_swell_{a,b,c}.wav, impact/sub_hit_{a,b}.wav,
                                                  typing/typing_{a,b}.wav, count/count_{a,b}.wav, riser_soft/riser_soft_{a,b}.wav
Default output: the bundled assets/sfx of this skill.

open_swell — the "fade" every reference reel starts with (a sub swell in most of them, a reverse swell in the rest). Measured
(references/sound-design.md): energy in 45–90 Hz +8 dB over the music bed, smooth rise of ~25 dB over 0.24 s, peak 0.24 s,
hold to 0.36 s, −7 dB drop, tail −10 dB to 0.6 s. Harmonics from soft saturation keep it audible on phone speakers.
sub_hit — a shorter thump for big reveals (numbers, "it's called", strikes): fast attack, 0.35 s decay.
typing / count / riser_soft — plain procedural stand-ins so the kit works out of the box; generate recorded-sounding ones with
sfx_gen.py (ElevenLabs) if you want richer texture.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import os, sys, wave
try:
    import numpy as np
except ImportError:
    raise SystemExit("this script needs numpy and Pillow: python3 -m pip install -r requirements.txt (in the skill folder)")

SR = 48000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sfx")


def save(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True); x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (-3 / 20)   # peak −3 dBFS like the rest of the kit
    st = np.stack([x, x], 1); b = (np.clip(st, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(b.tobytes())


def env_from(points, n):
    """piecewise-linear envelope in dB through (time_s, dB) points, converted to amplitude"""
    t = np.arange(n) / SR; ts, ds = zip(*points); return 10 ** (np.interp(t, ts, ds) / 20)


def noise_band(n, lo, hi, seed):
    rng = np.random.default_rng(seed); x = rng.standard_normal(n); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0; y = np.fft.irfft(X, n); return y / (np.max(np.abs(y)) + 1e-9)


def open_swell(f0=66, f1=52, dur=0.95, peak=0.24, seed=1, air=0.03):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.35)                      # the pitch settles downward a little, like a sub drop
    ph = 2 * np.pi * np.cumsum(f) / SR; sub = np.sin(ph) + 0.35 * np.sin(2 * ph + 0.3)
    k = peak / 0.24
    shape = [(0, -34), (0.02 * k, -20), (0.10 * k, -12), (0.18 * k, -6), (peak, 0), (peak + 0.10, -2), (peak + 0.14, -12), (0.62, -14), (0.72, -20), (0.85, -30), (dur, -60)]
    body = np.tanh(1.4 * sub * env_from(shape, n)) / np.tanh(1.4)   # gentle saturation → 2nd/3rd harmonics for small speakers, dynamics kept
    rumble = noise_band(n, 40, 260, seed) * env_from([(0, -40), (peak, -14), (peak + 0.14, -26), (dur, -60)], n)
    hiss = noise_band(n, 2500, 7000, seed + 7) * env_from([(0, -60), (peak * 0.9, -26), (peak + 0.05, -40), (dur, -70)], n)   # a breath of air on the rise
    # phones cannot play 50 Hz: a 250–700 Hz body with the same shape keeps the swell audible on a phone speaker
    mid = noise_band(n, 250, 700, seed + 3) * env_from(shape, n) + 0.6 * np.sin(4 * ph) * env_from(shape, n)
    return body + 0.5 * rumble + air * hiss + 0.28 * mid


def sub_hit(f0=70, f1=44, dur=0.6, seed=3):
    n = int(dur * SR); t = np.arange(n) / SR; f = f1 + (f0 - f1) * np.exp(-t / 0.08)
    ph = 2 * np.pi * np.cumsum(f) / SR; x = np.sin(ph) * env_from([(0, -30), (0.012, 0), (0.12, -6), (0.35, -20), (dur, -60)], n)
    click = noise_band(n, 1500, 5000, seed) * env_from([(0, -12), (0.01, -18), (0.03, -60), (dur, -80)], n)
    mid = noise_band(n, 250, 700, seed + 1) * env_from([(0, -30), (0.012, 0), (0.1, -8), (0.3, -24), (dur, -60)], n)   # the body a phone can play
    return np.tanh(2.0 * x) / np.tanh(2.0) + 0.25 * click + 0.3 * mid


def key_click(rng, n_len, bright=1.0):
    """one key press: a short filtered-noise click plus a small low 'thock' body"""
    n = int(n_len * SR); t = np.arange(n) / SR
    click = noise_band(n, 1800, 7000 * bright, int(rng.integers(1e6))) * np.exp(-t / 0.004)
    thock = np.sin(2 * np.pi * rng.uniform(160, 240) * t) * np.exp(-t / 0.018)
    return 0.8 * click + 0.5 * thock


def typing(dur=2.5, seed=11, bright=1.0):
    """continuous soft typing: key presses 55–120 ms apart with small level changes and an occasional pause"""
    rng = np.random.default_rng(seed); n = int(dur * SR); x = np.zeros(n); t = 0.02
    while t < dur - 0.06:
        k = key_click(rng, 0.05, bright) * rng.uniform(0.55, 1.0); i = int(t * SR); x[i:i + len(k)] += k[:max(0, n - i)]
        t += rng.uniform(0.055, 0.12) + (0.18 if rng.random() < 0.06 else 0)
    return x


def count(dur=0.9, ticks=16, seed=21, f=2700):
    """odometer roll: fast even ticks that slow a little towards the end, pitch rising slightly"""
    rng = np.random.default_rng(seed); n = int(dur * SR); x = np.zeros(n)
    times = dur * 0.92 * (np.linspace(0, 1, ticks) ** 1.25)
    for k, t0 in enumerate(times):
        m = int(0.03 * SR); tt = np.arange(m) / SR
        tick = (np.sin(2 * np.pi * f * (1 + 0.15 * k / ticks) * tt) * np.exp(-tt / 0.006) + 0.4 * noise_band(m, 2000, 8000, int(rng.integers(1e6))) * np.exp(-tt / 0.002))
        i = int(t0 * SR); x[i:i + m] += tick[:max(0, n - i)] * (0.7 + 0.3 * k / ticks)
    return x


def riser_soft(dur=1.2, seed=31, f0=300, f1=4200):
    """airy riser: band-passed noise whose centre sweeps up with a soft tone under it, loudest at the very end (placed to end on the reveal)"""
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n); seg = 2400
    for i in range(0, n, seg):   # sweep a narrow noise band upwards block by block
        c = f0 * (f1 / f0) ** (i / n); m = min(seg, n - i)
        x[i:i + m] = noise_band(seg, c * 0.7, c * 1.4, seed + i // seg)[:m]
    ph = 2 * np.pi * np.cumsum(220 * (4 ** (t / dur))) / SR
    y = 0.8 * x + 0.35 * np.sin(ph)
    y *= env_from([(0, -38), (dur * 0.5, -20), (dur * 0.85, -8), (dur - 0.01, 0), (dur, -40)], n)
    return y


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] in ("-h", "--help"): raise SystemExit(__doc__)
    if "--out" in a: OUT = os.path.abspath(os.path.expanduser(a[a.index("--out") + 1]))
    save(f"{OUT}/open/open_swell_a.wav", open_swell())
    save(f"{OUT}/open/open_swell_b.wav", open_swell(f0=62, f1=48, peak=0.22, seed=2, air=0.05))
    save(f"{OUT}/open/open_swell_c.wav", open_swell(f0=72, f1=55, peak=0.26, seed=4, air=0.02))
    save(f"{OUT}/impact/sub_hit_a.wav", sub_hit())
    save(f"{OUT}/impact/sub_hit_b.wav", sub_hit(f0=64, f1=40, seed=5))
    save(f"{OUT}/typing/typing_a.wav", typing())
    save(f"{OUT}/typing/typing_b.wav", typing(seed=12, bright=0.8))
    save(f"{OUT}/count/count_a.wav", count())
    save(f"{OUT}/count/count_b.wav", count(ticks=14, seed=22, f=2400))
    save(f"{OUT}/riser_soft/riser_soft_a.wav", riser_soft())
    save(f"{OUT}/riser_soft/riser_soft_b.wav", riser_soft(dur=1.5, seed=32, f0=250, f1=3600))
    print("written:", ", ".join(f"{d}/{f}" for d in ("open", "impact", "typing", "count", "riser_soft") for f in sorted(os.listdir(f"{OUT}/{d}")) if f.endswith(".wav")))
