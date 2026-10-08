#!/usr/bin/env python3
"""Gate before the render: one still per beat (at 70 % of it, after entrances settle) → labelled contact sheet work/snap_sheet.jpg. Seconds, not minutes.

  python3 snap.py <project>                 # middle of every beat from work/timeline.json (run build.py first)
  python3 snap.py <project> --at 0.1,4.2    # exact times
Look at the sheet: every beat shows what is being said, nothing empty, captions readable, no clipped text, head framing right.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import glob, json, os, re, shutil, subprocess, sys
try:
    from PIL import Image, ImageDraw, ImageFont, ImageStat
except ImportError:
    raise SystemExit("this script needs Pillow: python3 -m pip install -r requirements.txt (in the skill folder)")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import gpu_env, hf  # noqa: E402
from build import browser_preflight  # noqa: E402


def assert_subject_visible(path, beat, at):
    """Fallback when DOM preflight is unavailable: a speaker beat cannot be black."""
    if beat["layout"] not in ("face", "split"): return
    im = Image.open(path).convert("RGB")
    w, h = im.size
    top, bottom = (.15, .70) if beat["layout"] == "face" else (.58, .96)
    region = im.crop((int(w * .18), int(h * top), int(w * .82), int(h * bottom))).resize((96, 96))
    stat = ImageStat.Stat(region)
    if max(stat.mean) < 18 and max(stat.stddev) < 5:
        raise SystemExit(f"snapshot beat #{beat['i']} at {at:.2f}s: speaker region is black; browser timeline or video layer failed. Fix the named browser/caption error, rebuild and rerender")


def main(P, at=None):
    tl = json.load(open(f"{P}/work/timeline.json")); beats = tl["beats"]
    browser_preflight(P)
    if at: times = [float(x) for x in at.split(",")]; labels = [f"{t:.2f}s" for t in times]
    else:
        times = [round(max(b["t0"] + 0.3, b["t1"] - 0.12), 2) for b in beats]   # the settled end state of each beat, just before the next transition
        labels = [f"#{b['i']} {b['t0']:.1f}s {b['layout'][0].upper()} {b['gfx']}" for b in beats]
    out = f"{P}/work/snaps"; shutil.rmtree(out, ignore_errors=True)
    r = subprocess.run(hf("snapshot", f"{P}/hf", "--at", ",".join(map(str, times)), "--no-end", "-o", out, "--describe", "false"),
                       capture_output=True, text=True, env=gpu_env())
    files = sorted(glob.glob(f"{out}/frame-*.png"), key=lambda f: int(re.search(r"frame-(\d+)", f).group(1)))
    if r.returncode or len(files) != len(times): raise SystemExit("snapshot failed or returned incomplete frames:\n" + r.stdout[-800:] + r.stderr[-800:])
    for k, file in enumerate(files):
        beat = next((b for b in beats if b["t0"] <= times[k] < b["t1"]), beats[-1])
        assert_subject_visible(file, beat, times[k])
    tw, th, cols = 270, 480, 8; rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 28)), "white"); d = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for f in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"):
        try: font = ImageFont.truetype(f, 18); break
        except OSError: continue
    for k, f in enumerate(files):
        x, y = (k % cols) * tw, (k // cols) * (th + 28)
        sheet.paste(Image.open(f).convert("RGB").resize((tw, th)), (x, y + 28)); d.text((x + 6, y + 5), labels[k] if k < len(labels) else "", fill="black", font=font)
    sheet.save(f"{P}/work/snap_sheet.jpg", quality=85)
    print(f"{len(files)} stills → {P}/work/snap_sheet.jpg")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): raise SystemExit(__doc__)
    main(os.path.abspath(a[0]), a[a.index("--at") + 1] if "--at" in a else None)
