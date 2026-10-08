#!/usr/bin/env python3
"""Fetch visual assets for a reel into <project>/assets/.

  python3 fetch_assets.py <project> logo anthropic claude google github            # Simple Icons SVG in the brand colour (cdn.simpleicons.org)
  python3 fetch_assets.py <project> logo github:000000                             # force a colour
  python3 fetch_assets.py <project> favicon openrouter.ai example.com              # 256 px site icon (Google s2) for brands missing in Simple Icons
  python3 fetch_assets.py <project> emoji "Rocket" "E-mail" "Star" "Stopwatch"      # Microsoft Fluent Emoji 3D PNG (MIT licence)
  python3 fetch_assets.py <project> github owner/repo                              # GitHub social card 1200x600 (name, description, stars)
  python3 fetch_assets.py <project> shot https://site.com [name] [--mobile] [--dark] [--scroll-to="Heading text"] [--full]
                                                                                   # Playwright screenshot (desktop 1440x900 @2x, or mobile 430x932 @3x)
                                                                                   # needs: pip install playwright && playwright install chromium
Rights: brand logos and screenshots are third-party marks and content; use them the way news/commentary reels do and check the
rules of your platform and country. A real person named in the script is shown only on a real photo you may use (for example
their public profile photo); never generate or stock-photo a named person.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import _env  # noqa: E402,F401  (runs the script in the kit's Python env, see _env.py)
import os, re, sys, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"}


def get(url, path):
    data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
    open(path, "wb").write(data); return len(data)


def main():
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): raise SystemExit(__doc__)
    P, kind, *items = sys.argv[1:]; A = os.path.join(os.path.abspath(P), "assets"); os.makedirs(A, exist_ok=True)
    flags = [x for x in items if x.startswith("--")]; items = [x for x in items if not x.startswith("--")]
    if kind == "logo":
        for it in items:
            slug, _, color = it.partition(":"); url = f"https://cdn.simpleicons.org/{slug}" + (f"/{color}" if color else "")
            try: n = get(url, f"{A}/logo_{slug}.svg"); print("logo", slug, n, "bytes")
            except Exception as e: print("logo", slug, "FAILED", e, "→ try: favicon <domain>")
    elif kind == "favicon":
        for d in items:
            n = get(f"https://www.google.com/s2/favicons?domain={d}&sz=256", f"{A}/icon_{d.replace('.', '_')}.png"); print("favicon", d, n)
    elif kind == "emoji":
        for name in items:
            fn = name.lower().replace(" ", "_")
            url = f"https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/{urllib.parse.quote(name)}/3D/{urllib.parse.quote(fn)}_3d.png"
            try: n = get(url, f"{A}/emoji_{fn}.png"); print("emoji", name, n)
            except Exception as e: print("emoji", name, "FAILED", e, "(names follow github.com/microsoft/fluentui-emoji/tree/main/assets)")
    elif kind == "github":
        for repo in items:
            n = get(f"https://opengraph.githubassets.com/1/{repo}", f"{A}/gh_{repo.replace('/', '_')}.png"); print("github", repo, n)
    elif kind == "shot":
        from playwright.sync_api import sync_playwright
        url = items[0]; name = items[1] if len(items) > 1 else re.sub(r"\W+", "_", urllib.parse.urlparse(url).netloc)
        mobile = "--mobile" in flags; vp = dict(width=430, height=932) if mobile else dict(width=1440, height=900)
        with sync_playwright() as pw:
            b = pw.chromium.launch(); pg = b.new_page(viewport=vp, device_scale_factor=3 if mobile else 2, color_scheme="dark" if "--dark" in flags else "light")
            pg.goto(url, timeout=45000, wait_until="domcontentloaded"); pg.wait_for_timeout(3500)
            to = next((x.split("=", 1)[1] for x in flags if x.startswith("--scroll-to=")), None)
            if to:   # bring a heading or table into view, a little below the top edge
                el = pg.get_by_text(to, exact=False).first; el.scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0, -120)"); pg.wait_for_timeout(800)
            pg.screenshot(path=f"{A}/shot_{name}.png", full_page="--full" in flags); b.close()
        print("shot", url, "→", f"assets/shot_{name}.png")


if __name__ == "__main__":
    main()
