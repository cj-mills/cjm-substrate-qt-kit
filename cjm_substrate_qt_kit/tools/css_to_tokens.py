"""Import a web-first design system's CSS into a schema-v1 tokens file.

    python -m cjm_substrate_qt_kit.tools.css_to_tokens styles.css -o mysystem/tokens.json [--name "My System"]

Reads the `:root { --color-*; --font-*; --space-*; --radius-* }` block (the
shape a Claude Design handoff uses) and writes light-mode tokens straight
from it; dark mode is DERIVED from the 100-900 ramps and the six state roles
are seeded from the kit's reading-tuned set — review both by eye in the
gallery (a derivation is a starting point, never a verdict; ruling a439c226:
the CSS is an import source, the tokens file is the source of truth). The
output passes `tokens.check` or the tool refuses to write it."""

import argparse
import json
import re
from pathlib import Path

from .. import tokens as T

VAR = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")
HEX = re.compile(r"#[0-9a-fA-F]{6}")

STATE_LIGHT = {"danger": "#a4382a", "warn": "#8c5e14", "ok": "#3a7a3a",
               "info": "#4a5f96", "meta": "#2a6f7c", "note": "#7a4a8a"}
STATE_DARK = {"danger": "#dc8070", "warn": "#d0a552", "ok": "#7dbb7d",
              "info": "#8fa6d6", "meta": "#67b2bf", "note": "#bb93c9"}


def parse_root(css: str) -> dict:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    m = re.search(r":root\s*{(.*?)}", css, flags=re.S)
    if not m:
        raise SystemExit("no :root block found")
    return {k: v.strip() for k, v in VAR.findall(m.group(1))}


def family(v: str) -> str:
    return v.split(",")[0].strip().strip("'\"")


def px(v: str) -> float:
    return float(re.sub(r"[^\d.]", "", v) or 0)


def ramp(vars_: dict, role: str):
    steps = [vars_.get(f"color-{role}-{s}") for s in range(100, 1000, 100)]
    return steps if all(steps) else None


def darker(h: str, k: float) -> str:
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(c * k) for c in (r, g, b))


def convert(css: str, name: str) -> dict:
    v = parse_root(css)
    col = lambda k: (HEX.findall(v.get(f"color-{k}", "")) or [None])[0]  # noqa: E731
    neutral, accent = ramp(v, "neutral"), ramp(v, "accent")
    if not (neutral and accent):
        raise SystemExit("need --color-neutral-100..900 and --color-accent-100..900 ramps")
    hw = int(px(v.get("font-heading-weight", "600")))
    heading, body = family(v["font-heading"]), family(v["font-body"])
    mono = family(v["font-mono"]) if v.get("font-mono") else ""
    light_ground = int(col("bg")[1:3], 16) > 128
    light = {
        "bg": col("bg"), "surface": col("surface"), "text": col("text"), "accent": col("accent"),
        "accent_pressed": "@accent.600", "accent_text": "@accent.700",
        "tag_bg": "@accent.100", "tag_fg": "@accent.800",
        "tag_neutral_bg": "@neutral.100", "tag_neutral_fg": "@neutral.800",
        "shadow": "@neutral.900", "shadow_strength": 1.0, **STATE_LIGHT,
    }
    dark = {
        "bg": darker(neutral[8], .68), "surface": darker(neutral[8], .86), "text": neutral[0],
        "accent": accent[4] if light_ground else col("accent"),
        "accent_pressed": "@accent.400", "accent_text": "@accent.300",
        "tag_bg": "@accent.900", "tag_fg": "@accent.200",
        "tag_neutral_bg": "@neutral.900", "tag_neutral_fg": "@neutral.200",
        "shadow": "#000000", "shadow_strength": 2.2, **STATE_DARK,
    }
    modes = {"light": light, "dark": dark} if light_ground else {"dark": light}
    out = {
        "schema": T.SCHEMA_VERSION,
        "name": name,
        "fonts": {
            "heading": {"family": heading, "weight": hw},
            "body": {"family": body, "size": 15},
            "mono": {"family": mono, "size": 13},
            "files": [heading.replace(" ", "") + "*.ttf", body.replace(" ", "") + "*.ttf"],
        },
        "space": {k.split("-")[1]: px(x) for k, x in v.items() if re.fullmatch(r"space-\d+", k)},
        "radius": {k.split("-")[1]: px(x) for k, x in v.items() if re.fullmatch(r"radius-\w+", k)},
        "type": {"h1": [42, 400], "h2": [32, 400], "h3": [25, hw], "h4": [20, hw], "h5": [16, hw],
                 "title": [17, hw], "kicker": [10, 400], "caption": [11, 400]},
        "ramps": {"neutral": neutral, "accent": accent},
        "scheme": {"light": "light", "dark": "dark"} if light_ground else {"dark": "dark"},
        "reading": dict(T.READING_DEFAULTS),
        "icons": dict(T.ICONS_DEFAULTS),
        "modes": modes,
    }
    if not out["space"]:
        out["space"] = {"1": 4, "2": 8, "3": 12, "4": 16, "6": 24, "8": 32}
    if not out["radius"]:
        out["radius"] = {"sm": 2, "md": 4, "lg": 8}
    T.check(out, f"<converted from CSS: {name}>")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cjm_substrate_qt_kit.tools.css_to_tokens")
    ap.add_argument("css")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--name")
    a = ap.parse_args(argv)
    name = a.name or Path(a.out).parent.name.title()
    out = convert(Path(a.css).read_text(encoding="utf-8"), name)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {a.out}  modes={list(out['modes'])}  heading={out['fonts']['heading']['family']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
