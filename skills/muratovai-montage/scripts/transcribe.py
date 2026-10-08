"""Speech to text with ElevenLabs Scribe (replaces OpenAI whisper-1 in this fork of the kit).

scribe(audio, lang, vocab) returns the whisper-shaped dict the rest of the kit reads:
  {"text": full text, "language": scribe code, "words": [{"word", "start", "end"}, ...]}
Scribe word tokens already carry their punctuation; spacing and audio-event tokens are dropped. Uzbek comes back in Cyrillic
and is written in Latin (the standard spelling with '), product names in Latin stay as they are.
Key: ELEVENLABS_API_KEY (passed to curl on stdin, never on the command line).
"""
import json, re

from common import curl, env_key

API_URL = "https://api.elevenlabs.io/v1/speech-to-text"
MODEL_ID = "scribe_v2"
TIMEOUT_S = 600
MAX_KEYTERMS = 100      # Scribe's limit on bias terms
MAX_KEYTERM_LEN = 50    # longer terms are rejected by the API
LANGS = {"en": "eng", "ru": "rus", "uz": "uzb", "kk": "kaz", "de": "deu", "es": "spa", "fr": "fra", "it": "ita", "pt": "por",
         "tr": "tur", "uk": "ukr", "pl": "pol", "nl": "nld", "ar": "ara", "hi": "hin", "ja": "jpn", "ko": "kor", "zh": "zho"}

CYR2LAT = {"а": "a", "б": "b", "в": "v", "г": "g", "ғ": "g'", "д": "d", "ё": "yo", "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k",
           "қ": "q", "л": "l", "м": "m", "н": "n", "о": "o", "ў": "o'", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
           "х": "x", "ҳ": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'", "ь": "", "ы": "i", "э": "e", "ю": "yu", "я": "ya"}
CYR_VOWELS = set("аеёиоуўэюяaeiou")


def scribe_lang(lang):
    """ISO 639-1 (en) or 639-3 (eng) → the code Scribe expects; exits on an unknown code"""
    code = (lang or "").strip().lower()
    if len(code) == 3: return code
    if code in LANGS: return LANGS[code]
    raise SystemExit(f"unknown language code {lang!r}: use a two-letter code ({', '.join(sorted(LANGS))}) or a three-letter ISO 639-3 code")


def keyterms(vocab):
    """comma-separated vocabulary → unique terms in order, within Scribe's limits"""
    out = []
    for t in (x.strip() for x in (vocab or "").split(",")):
        if t and len(t) <= MAX_KEYTERM_LEN and t not in out: out.append(t)
    return out[:MAX_KEYTERMS]


def to_latin(word):
    """one Uzbek word from Cyrillic to Latin; "е" is "ye" at the start and after a vowel or ъ/ь; case is kept (Ч → Ch, ЧАТ → CHAT)"""
    out, caps = [], len(word) > 1 and word.isupper()
    for i, ch in enumerate(word):
        low, prev = ch.lower(), word[i - 1].lower() if i else ""
        lat = ("ye" if (i == 0 or prev in CYR_VOWELS or prev in "ъь") else "e") if low == "е" else CYR2LAT.get(low)
        if lat is None: out.append(ch); continue
        if ch != low and lat:
            nxt = word[i + 1] if i + 1 < len(word) else ""
            lat = lat.upper() if caps or nxt.isupper() else lat[0].upper() + lat[1:]
        out.append(lat)
    return "".join(out)


def _latin_text(text):
    return re.sub(r"[^\W\d_]+", lambda m: to_latin(m.group(0)), text)


def to_whisper(data, lang):
    """Scribe JSON → {"text", "language", "words": [{"word", "start", "end"}]}"""
    uz = scribe_lang(lang) == "uzb"
    fix = _latin_text if uz else (lambda s: s)
    words = []
    for w in data.get("words", []):
        if w.get("type", "word") != "word": continue
        text = fix(str(w.get("text", "")).strip())
        if text: words.append({"word": text, "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)})
    return {"text": fix(data.get("text", "")), "language": data.get("language_code", scribe_lang(lang)), "words": words}


def scribe(audio, lang, vocab=""):
    """transcribe an audio file with word timings; exits with the API's message on failure"""
    args = ["-F", f"file=@{audio}", "--form-string", f"model_id={MODEL_ID}", "--form-string", f"language_code={scribe_lang(lang)}",
            "--form-string", "timestamps_granularity=word", "--form-string", "tag_audio_events=false"]
    for t in keyterms(vocab): args += ["--form-string", f"keyterms={t}"]
    out = curl(API_URL, f"xi-api-key: {env_key('ELEVENLABS_API_KEY')}", *args, timeout=TIMEOUT_S)
    try: r = json.loads(out)
    except ValueError: raise SystemExit(f"ElevenLabs Scribe: unexpected response: {out[:300]}")
    if "words" not in r:
        det = r.get("detail", r)
        raise SystemExit(f"ElevenLabs Scribe error: {(det.get('message') or det) if isinstance(det, dict) else det}"[:400])
    return to_whisper(r, lang)
