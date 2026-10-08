#!/usr/bin/env python3
"""Collect reference reels for style analysis into <profile>/raw/NN_<id>.mp4 (with sound).

  python3 fetch_reels.py <profile_dir> <input> [<input> ...] [--limit N] [--no-apify] [--yt-dlp-args "<extra args>"]

An <input> is any of:
  https://www.instagram.com/reel/<code>/   Instagram reel or post: Apify (if APIFY_TOKEN is set) → yt-dlp fallback
  https://www.tiktok.com/@user/video/<id>  TikTok, YouTube Shorts or anything else yt-dlp supports
  /path/to/video.mp4                       a local file (mp4/mov/webm/mkv/m4v): copied or converted to mp4
  @handle                                  the latest --limit reels (default 5) of an Instagram account: needs APIFY_TOKEN

Writes <profile_dir>/raw/NN_<id>.mp4 in input order and <profile_dir>/sources.json (where each file came from).
Apify cost: about $0.01 per reel (the run is capped at $0.50). yt-dlp is free; install it with `brew install yt-dlp` or
`pipx install yt-dlp`. Instagram often refuses anonymous downloads: then pass your own cookies through yt-dlp, e.g.
--yt-dlp-args "--cookies-from-browser chrome" (on Windows: firefox), or use Apify, or download the reel yourself and give the local file.
The downloaded reels are for your private analysis: keep them local and do not republish them.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import glob, hashlib, json, os, re, shlex, shutil, subprocess, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import env_key  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
VIDEO_EXT = (".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi")


def apify(actor, payload, max_usd=0.5, timeout=900):
    T = env_key("APIFY_TOKEN"); a = actor.replace("/", "~"); auth = {"Authorization": f"Bearer {T}"}
    req = urllib.request.Request(f"https://api.apify.com/v2/acts/{a}/runs?maxTotalChargeUsd={max_usd}", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **auth})
    r = json.load(urllib.request.urlopen(req, timeout=60))["data"]; t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(5)
        st = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.apify.com/v2/actor-runs/{r['id']}", headers=auth), timeout=60))["data"]
        if st["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            print(f"apify {st['status']} in {int(time.time() - t0)} s, cost ${st.get('usageTotalUsd', 0) or 0:.3f}", flush=True); break
    req = urllib.request.Request(f"https://api.apify.com/v2/datasets/{r['defaultDatasetId']}/items?clean=true", headers=auth)
    return json.load(urllib.request.urlopen(req, timeout=120))


def download(url, path):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r, open(path, "wb") as f: f.write(r.read())


def has_audio(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", p], capture_output=True, text=True).stdout
    return bool(out.strip())


def to_mp4(src, dst):
    """copy an mp4 with H.264/AAC as is; convert anything else to H.264/AAC mp4"""
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name", "-of", "csv=p=0", src], capture_output=True, text=True).stdout.split()
    if src.lower().endswith(".mp4") and "h264" in pr and ("aac" in pr or not has_audio(src)): shutil.copy(src, dst); return
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(f"ffmpeg could not convert {src}: {r.stderr[-300:]}")


def ig_code(url):
    m = re.search(r"instagram\.com/(?:[\w.]+/)?(?:reel|reels|p|tv)/([\w-]+)", url)
    return m.group(1) if m else None


def slug_for(inp):
    if os.path.exists(inp): return re.sub(r"[^\w-]+", "_", os.path.splitext(os.path.basename(inp))[0])[:40] or "video"
    code = ig_code(inp)
    if code: return code
    m = re.search(r"tiktok\.com/.*/video/(\d+)", inp) or re.search(r"(?:shorts/|youtu\.be/|[?&]v=)([\w-]{6,})", inp)
    return m.group(1) if m else hashlib.md5(inp.encode()).hexdigest()[:10]


def ytdlp_cmd():
    exe = shutil.which("yt-dlp")
    if exe: return [exe]
    if subprocess.run([sys.executable, "-m", "yt_dlp", "--version"], capture_output=True).returncode == 0: return [sys.executable, "-m", "yt_dlp"]
    return None


def cookie_hint(platform=None):
    """what to try when Instagram refuses an anonymous download: a browser whose cookies yt-dlp can read on this OS
    (Chrome locks its cookies on Windows with app-bound encryption; Firefox does not)"""
    browser = "firefox" if (platform or sys.platform) == "win32" else "chrome"
    return (f"Instagram wants a login: log in to Instagram in {browser.capitalize()} and rerun with "
            f"--yt-dlp-args \"--cookies-from-browser {browser}\", or add an Apify token, or download the reels yourself and give the files")


def via_ytdlp(url, dst, extra):
    cmd = ytdlp_cmd()
    if not cmd: raise RuntimeError("yt-dlp is not installed (brew install yt-dlp, or pipx install yt-dlp)")
    tmpl = dst[:-4] + ".%(ext)s"
    r = subprocess.run(cmd + ["--no-playlist", "--quiet", "--no-warnings", "-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", tmpl] + extra + [url],
                       capture_output=True, text=True)
    got = [f for f in glob.glob(dst[:-4] + ".*") if f.lower().endswith(VIDEO_EXT)]
    if r.returncode or not got:
        hint = f"\n{cookie_hint()}" if "instagram.com" in url else ""
        raise RuntimeError(f"yt-dlp failed: {(r.stderr or r.stdout).strip()[-400:]}{hint}")
    if got[0] != dst: to_mp4(got[0], dst); os.remove(got[0])


def via_apify_items(items, out, start_k, meta):
    """download Apify reel items (videoUrl + optional separate audioUrl) → raw/NN_<shortCode>.mp4"""
    done = []
    for it in items:
        if not it.get("videoUrl"): continue
        k = start_k + len(done); p = f"{out}/raw/{k:02d}_{it.get('shortCode') or slug_for(it.get('url', str(k)))}.mp4"
        if not os.path.exists(p):
            download(it["videoUrl"], p)
            if not has_audio(p) and it.get("audioUrl"):   # some items come as video-only files: mux the separate audio in
                a = p[:-4] + "_audio.m4a"; download(it["audioUrl"], a); tmp = p[:-4] + "_av.mp4"
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", p, "-i", a, "-map", "0:v", "-map", "1:a", "-c", "copy", "-shortest", tmp], check=True)
                os.replace(tmp, p); os.remove(a)
        done.append(dict(file=os.path.basename(p), method="apify", url=it.get("url"), timestamp=it.get("timestamp"),
                         plays=it.get("videoPlayCount"), duration=it.get("videoDuration"), **meta))
    return done


def main(out, inputs, limit, use_apify, extra):
    os.makedirs(f"{out}/raw", exist_ok=True)
    have_token = use_apify and bool(env_key("APIFY_TOKEN", required=False))
    k = len(glob.glob(f"{out}/raw/*.mp4")) + 1; sources = []
    for inp in inputs:
        try:
            if inp.startswith("@"):
                if not have_token: raise RuntimeError("an account handle needs APIFY_TOKEN; without it paste reel links or local files")
                items = apify("apify/instagram-reel-scraper", {"username": [inp.lstrip("@")], "resultsLimit": limit})
                items = sorted(items, key=lambda i: i.get("timestamp", ""), reverse=True)[:limit]
                got = via_apify_items(items, out, k, dict(input=inp)); sources += got; k += len(got); continue
            p = f"{out}/raw/{k:02d}_{slug_for(inp)}.mp4"
            if os.path.exists(inp):
                if not inp.lower().endswith(VIDEO_EXT): raise RuntimeError("not a video file")
                to_mp4(inp, p); sources.append(dict(input=os.path.abspath(inp), file=os.path.basename(p), method="local"))
            elif ig_code(inp) and have_token:
                try:
                    items = apify("apify/instagram-scraper", {"directUrls": [inp], "resultsType": "posts", "resultsLimit": 1})
                    got = via_apify_items(items[:1], out, k, dict(input=inp))
                    if not got: raise RuntimeError("Apify returned no video for this link")
                    sources += got; k += 1; print(k - 1, "apify", got[0]["file"], flush=True); continue
                except Exception as e:
                    print(f"apify failed for {inp} ({e}); trying yt-dlp", flush=True)
                    via_ytdlp(inp, p, extra); sources.append(dict(input=inp, file=os.path.basename(p), method="yt-dlp"))
            elif inp.startswith("http"):
                via_ytdlp(inp, p, extra); sources.append(dict(input=inp, file=os.path.basename(p), method="yt-dlp"))
            else: raise RuntimeError("neither a link, an existing file nor an @handle")
            if not has_audio(p): print(f"warning: {os.path.basename(p)} has no sound; words and sound analysis will be empty for it")
            print(k, sources[-1]["method"], sources[-1]["file"], flush=True); k += 1
        except Exception as e:
            print(f"FAILED {inp}: {e}", flush=True)
    old = json.load(open(f"{out}/sources.json")) if os.path.exists(f"{out}/sources.json") else []
    json.dump(old + sources, open(f"{out}/sources.json", "w"), ensure_ascii=False, indent=1)
    n = len(glob.glob(f"{out}/raw/*.mp4"))
    print(f"{len(sources)} new reel(s), {n} in {out}/raw → next: python3 analyze_reference.py {out} all --lang <en|ru|…>")
    if not sources: sys.exit(1)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2 or a[0] in ("-h", "--help"): raise SystemExit(__doc__)
    extra = shlex.split(a[a.index("--yt-dlp-args") + 1]) if "--yt-dlp-args" in a else []
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 5
    skip = {i + 1 for i, x in enumerate(a) if x in ("--yt-dlp-args", "--limit")}
    inputs = [x for i, x in enumerate(a[1:], 1) if not x.startswith("--") and i not in skip]
    main(os.path.abspath(os.path.expanduser(a[0])), inputs, limit, "--no-apify" not in a, extra)
