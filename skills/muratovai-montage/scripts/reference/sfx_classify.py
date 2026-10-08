#!/usr/bin/env python3
"""Classify the SFX events pulled out by sfx_extract.py with an audio model.

  python3 sfx_classify.py <dir> [--min-peak -30]     → <dir>/sfx/labels.json (one label per clip file)
Uses Gemini 2.5 Flash via OpenRouter when OPENROUTER_API_KEY is set (≈ $0.00005 per clip), otherwise an OpenAI audio model
(REELS_AUDIO_MODEL, default gpt-audio-1.5; OPENAI_API_KEY; about $0.001–0.003 per clip). Short one-shot sounds are classified
unreliably by any model: trust duration, attack, spectral centre and low-band share (events.json) over the label.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import base64, concurrent.futures as cf, json, os, subprocess, sys, tempfile, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import env_key  # noqa: E402

CLASSES = ["whoosh", "swoosh_tonal", "riser", "reverse_swell", "impact", "sub_drop", "pop", "click", "tick", "typing", "ding", "chime_sparkle",
           "glitch", "shutter", "swipe_slide", "cash_coin", "error_buzz", "notification", "boom_braam", "record_scratch", "crowd_laugh",
           "music_drum_hit", "music_element", "voice_residue", "other"]
PROMPT = ("You hear a short clip cut from the BACKGROUND track of a vertical social video (the voice was removed by source separation, "
          "so a faint music bed may be underneath). Classify the most prominent sound event in it.\n"
          f"Answer ONLY a JSON object: {{\"class\": one of {CLASSES}, \"is_sfx\": true if it is an added sound effect (not part of the music bed, not voice residue), "
          "\"character\": 3-6 words about timbre (e.g. 'soft airy high whoosh', 'deep sub thump', 'bright glassy UI pop'), "
          "\"confidence\": 0-1}")
D = None


def ask(e):
    src = f"{D}/sfx/clips/{e['file']}"; fd, tmp = tempfile.mkstemp(suffix=".mp3"); os.close(fd)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "22050", "-b:a", "64k", tmp], check=True)
    b = base64.b64encode(open(tmp, "rb").read()).decode(); os.remove(tmp)
    content = [{"type": "text", "text": PROMPT}, {"type": "input_audio", "input_audio": {"data": b, "format": "mp3"}}]
    ork = env_key("OPENROUTER_API_KEY", required=False)
    if ork:
        url, key = "https://openrouter.ai/api/v1/chat/completions", ork
        body = {"model": "google/gemini-2.5-flash", "temperature": 0, "max_tokens": 200, "response_format": {"type": "json_object"}, "messages": [{"role": "user", "content": content}]}
    else:
        url, key = "https://api.openai.com/v1/chat/completions", env_key("OPENAI_API_KEY")
        body = {"model": os.environ.get("REELS_AUDIO_MODEL", "gpt-audio-1.5"), "modalities": ["text"], "messages": [{"role": "user", "content": content}]}
    err = ""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=120)); txt = r["choices"][0]["message"]["content"].strip().strip("`")
            if txt.startswith("json"): txt = txt[4:]
            d = json.loads(txt[txt.find("{"):txt.rfind("}") + 1]); d["cost"] = r.get("usage", {}).get("cost", 0); return e["file"], d
        except Exception as ex:
            err = str(ex)
    return e["file"], {"class": "error", "error": err}


def main():
    a = sys.argv[1:]; th = float(a[a.index("--min-peak") + 1]) if "--min-peak" in a else -30
    E = [e for e in json.load(open(f"{D}/sfx/events.json")) if e["peak_rel_voice"] >= th]
    out_p = f"{D}/sfx/labels.json"; done = json.load(open(out_p)) if os.path.exists(out_p) else {}
    todo = [e for e in E if e["file"] not in done or done[e["file"]].get("class") == "error"]
    print(f"{len(E)} clips ≥ {th} dB, {len(todo)} to label with {'OpenRouter Gemini' if env_key('OPENROUTER_API_KEY', required=False) else 'OpenAI'}", flush=True)
    with cf.ThreadPoolExecutor(8) as ex:
        for k, (f, d) in enumerate(ex.map(ask, todo)):
            done[f] = d
            if k % 50 == 0: json.dump(done, open(out_p, "w"), indent=0); print(k, flush=True)
    json.dump(done, open(out_p, "w"), indent=0)
    print("cost $", round(sum(v.get("cost", 0) or 0 for v in done.values()), 4), "(OpenRouter reports cost; OpenAI does not)")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): raise SystemExit(__doc__)
    D = os.path.abspath(os.path.expanduser(sys.argv[1]))
    if not os.path.exists(f"{D}/sfx/events.json"): raise SystemExit(f"run sfx_extract.py {D} first")
    main()
