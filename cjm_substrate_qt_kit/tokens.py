"""Token schema v1 — a design system as DATA, resolved headlessly (ruling
a439c226: one canonical tokens file per system, shared by the web and Qt
projections; DEC 0b1cfd81 fixed the shape).

A tokens file holds: `name`, `schema` (= 1), `fonts` (heading / body, the
optional mono and ui slots, the `files` globs registered at apply time),
`space`, `radius`, `type` (role -> [px, weight]), `ramps` (100..900 steps for
neutral and accent), `modes` (one semantic block per mode — a system's OWN
modes: Classical light / dark, Netrunner red / yellow / green / blue / white —
every block carrying the base semantics, the SIX STATE ROLES danger / warn /
ok / info / meta / note, and any system-specific keys that pass straight
through), the optional `scheme` map (OS light / dark -> a mode; absent = the
system does not follow the OS), the optional `reading` block (measure,
line_height — the reading-quality tokens), and the optional `icons`
declaration (set + stroke_width; Lucide at 1.5 by default). `@ramp.step`
references resolve against the ramps.

Nothing here imports Qt: `check` and `resolve` run in tests, in the build
CLI and on the web side. `resolve` emits ONE flat vocabulary — the QSS hole
names ($bg $text $surface $accent $muted …) plus the state roles, the
typography slots and the scale — and every kit widget reads that vocabulary
(fork 1 of the design: no second vocabulary, no aliases)."""

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCHEMA_VERSION = 1
STATE_ROLES: Tuple[str, ...] = ("danger", "warn", "ok", "info", "meta", "note")
MODE_KEYS: Tuple[str, ...] = ("bg", "surface", "text", "accent", "accent_pressed", "accent_text",
                              "tag_bg", "tag_fg", "tag_neutral_bg", "tag_neutral_fg", "shadow")
TYPE_ROLES: Tuple[str, ...] = ("h1", "h2", "h3", "h4", "h5", "title", "kicker", "caption")
RAMPS: Tuple[str, ...] = ("neutral", "accent")
READING_DEFAULTS = {"measure": 68, "line_height": 1.45}
ICONS_DEFAULTS = {"set": "lucide", "stroke_width": 1.5}

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_REF = re.compile(r"^@([a-z_]+)\.([1-9]00)$")


class SchemaError(ValueError):
    """A tokens file that violates schema v1 — every problem listed, so one
    read of the message fixes the file (the loud refusal the ruling asks for)."""

    def __init__(self, source: str, problems: List[str]):
        self.source = source
        self.problems = list(problems)
        super().__init__("%s: %d schema problem(s):\n  - %s"
                         % (source, len(problems), "\n  - ".join(problems)))


# ---- color arithmetic (the CSS color-mix() equivalents) ---------------------

def _rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def to_hex(rgb: Iterable[float]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c))) for c in rgb)


def rgba(h: str, a: float) -> str:
    """QSS rgba() with a 0-255 alpha (the form every Qt 6 version parses)."""
    r, g, b = _rgb(h)
    return f"rgba({r}, {g}, {b}, {round(max(0.0, min(1.0, a)) * 255)})"


def mix(fg: str, bg: str, t: float) -> str:
    """Flatten `fg` at opacity `t` over `bg` -> a solid hex (QPalette, painters,
    rich-text HTML — anything that cannot take an rgba string)."""
    f, b = _rgb(fg), _rgb(bg)
    return to_hex(tuple(b[i] + (f[i] - b[i]) * t for i in range(3)))


# ---- load / check -----------------------------------------------------------

def load(path) -> Dict[str, Any]:
    """Read a tokens file (JSON). `check` it before resolving anything."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def slug(tokens: Dict[str, Any]) -> str:
    """The system's file-system / preference slug: lower-case, spaces -> dashes."""
    return str(tokens.get("slug") or tokens.get("name", "system")).lower().replace(" ", "-")


def modes(tokens: Dict[str, Any]) -> List[str]:
    return list((tokens.get("modes") or {}).keys())


def mode_for_scheme(tokens: Dict[str, Any], scheme: str) -> Optional[str]:
    """The mode the system maps an OS scheme ("light" / "dark") onto — None
    when the system declares no `scheme` map (it does not follow the OS)."""
    m = tokens.get("scheme") or {}
    mode = m.get(scheme)
    return str(mode) if mode in (tokens.get("modes") or {}) else None


def _ref(tokens: Dict[str, Any], v):
    """Resolve '@accent.600' -> the ramp step (100..900); pass anything else."""
    if isinstance(v, str) and v.startswith("@"):
        ramp, step = v[1:].split(".")
        return tokens["ramps"][ramp][int(step) // 100 - 1]
    return v


def check(tokens: Dict[str, Any], source: str = "<tokens>") -> None:
    """Refuse a malformed system loudly: every missing / mistyped field named
    in one SchemaError. A tokens file that passes here resolves for every
    mode it declares."""
    p: List[str] = []
    if not isinstance(tokens, dict):
        raise SchemaError(source, ["the tokens file must be a JSON object"])
    if tokens.get("schema") != SCHEMA_VERSION:
        p.append("schema: expected %d, got %r" % (SCHEMA_VERSION, tokens.get("schema")))
    if not isinstance(tokens.get("name"), str) or not tokens.get("name"):
        p.append("name: a non-empty string is required")
    fonts = tokens.get("fonts")
    if not isinstance(fonts, dict):
        p.append("fonts: an object with heading and body slots is required")
        fonts = {}
    for slot in ("heading", "body"):
        f = fonts.get(slot)
        if not isinstance(f, dict) or not isinstance(f.get("family"), str):
            p.append("fonts.%s.family: a string is required" % slot)
    if isinstance(fonts.get("heading"), dict) and not isinstance(fonts["heading"].get("weight"), int):
        p.append("fonts.heading.weight: an integer is required")
    if isinstance(fonts.get("body"), dict) and not isinstance(fonts["body"].get("size"), (int, float)):
        p.append("fonts.body.size: a pixel size is required")
    for slot in ("mono", "ui"):
        f = fonts.get(slot)
        if f is not None and (not isinstance(f, dict) or not isinstance(f.get("family", ""), str)):
            p.append("fonts.%s: an object with a family string when present" % slot)
    if fonts.get("files") is not None and not (isinstance(fonts["files"], list)
                                                and all(isinstance(x, str) for x in fonts["files"])):
        p.append("fonts.files: a list of glob strings when present")
    for scale in ("space", "radius"):
        d = tokens.get(scale)
        if not isinstance(d, dict) or not d or not all(isinstance(v, (int, float)) for v in d.values()):
            p.append("%s: a non-empty object of pixel numbers is required" % scale)
    typ = tokens.get("type")
    if not isinstance(typ, dict):
        p.append("type: an object of role -> [px, weight] is required")
        typ = {}
    for role in TYPE_ROLES:
        if role not in typ:
            p.append("type.%s: required" % role)
    for role, val in typ.items():
        if not (isinstance(val, list) and len(val) == 2
                and all(isinstance(x, (int, float)) for x in val)):
            p.append("type.%s: expected [px, weight]" % role)
    ramps = tokens.get("ramps")
    if not isinstance(ramps, dict):
        p.append("ramps: an object with neutral and accent 9-step ramps is required")
        ramps = {}
    for name in RAMPS:
        r = ramps.get(name)
        if not (isinstance(r, list) and len(r) == 9 and all(isinstance(x, str) and _HEX.match(x) for x in r)):
            p.append("ramps.%s: exactly nine #rrggbb steps (100..900) are required" % name)
    mode_map = tokens.get("modes")
    if not isinstance(mode_map, dict) or not mode_map:
        p.append("modes: at least one mode block is required")
        mode_map = {}
    for mode, block in mode_map.items():
        if not isinstance(block, dict):
            p.append("modes.%s: expected an object" % mode)
            continue
        for key in MODE_KEYS + STATE_ROLES:
            val = block.get(key)
            if val is None:
                p.append("modes.%s.%s: required%s" % (mode, key,
                         " (a state role — every mode carries all six)" if key in STATE_ROLES else ""))
            elif not isinstance(val, str) or not (_HEX.match(val) or _REF.match(val)):
                p.append("modes.%s.%s: expected #rrggbb or @ramp.step, got %r" % (mode, key, val))
            elif _REF.match(val):
                ramp = _REF.match(val).group(1)
                if ramp not in ramps or not isinstance(ramps.get(ramp), list) or len(ramps[ramp]) != 9:
                    p.append("modes.%s.%s: %s references a ramp that does not exist" % (mode, key, val))
        ss = block.get("shadow_strength", 1.0)
        if not isinstance(ss, (int, float)):
            p.append("modes.%s.shadow_strength: expected a number" % mode)
    scheme = tokens.get("scheme")
    if scheme is not None:
        if not isinstance(scheme, dict) or set(scheme) - {"light", "dark"}:
            p.append("scheme: an object with light and/or dark keys naming modes")
        else:
            for k, v in scheme.items():
                if v not in mode_map:
                    p.append("scheme.%s: %r is not a declared mode" % (k, v))
    reading = tokens.get("reading")
    if reading is not None:
        if not isinstance(reading, dict):
            p.append("reading: an object with measure / line_height")
        else:
            if "measure" in reading and not isinstance(reading["measure"], int):
                p.append("reading.measure: an integer (characters)")
            if "line_height" in reading and not isinstance(reading["line_height"], (int, float)):
                p.append("reading.line_height: a number (ratio)")
    icons = tokens.get("icons")
    if icons is not None:
        if not isinstance(icons, dict) or not isinstance(icons.get("set", "lucide"), str):
            p.append("icons: an object with a set name (and an optional stroke_width)")
        elif "stroke_width" in icons and not isinstance(icons["stroke_width"], (int, float)):
            p.append("icons.stroke_width: a number")
    chrome = tokens.get("chrome")
    if chrome is not None:
        if not isinstance(chrome, dict):
            p.append("chrome: an object naming the shell chrome's ink (titlebar_ink: a mode key)")
        else:
            ink = chrome.get("titlebar_ink", "text")
            if not isinstance(ink, str) or any(ink not in (block or {}) and ink not in ("text", "accent")
                                               for block in mode_map.values() if isinstance(block, dict)):
                p.append("chrome.titlebar_ink: must name a key every mode carries (e.g. fill_text)")
    if p:
        raise SchemaError(source, p)


# ---- resolve ----------------------------------------------------------------

def resolve(tokens: Dict[str, Any], mode: Optional[str] = None) -> Dict[str, str]:
    """tokens + mode -> the flat vocabulary every projection reads: the QSS
    holes (colors, tints, solids, radii, spacing, type scale), the six state
    roles + `dim`, the four font slots with pixel sizes, and the reading
    tokens. `mode` None = the system's first mode."""
    mode = mode or modes(tokens)[0]
    m = {k: _ref(tokens, v) for k, v in tokens["modes"][mode].items()}
    bg, text, acc = m["bg"], m["text"], m["accent"]
    f = tokens["fonts"]
    body = f["body"]
    mono = f.get("mono") or {}
    ui = f.get("ui") or {}
    reading = {**READING_DEFAULTS, **(tokens.get("reading") or {})}
    icons = {**ICONS_DEFAULTS, **(tokens.get("icons") or {})}
    v: Dict[str, str] = {
        "system": slug(tokens), "name": str(tokens["name"]), "mode": mode,
        "bg": bg, "surface": m["surface"], "text": text,
        "accent": acc, "accent_pressed": m["accent_pressed"], "accent_text": m["accent_text"],
        "tag_bg": m["tag_bg"], "tag_fg": m["tag_fg"],
        "tag_neutral_bg": m["tag_neutral_bg"], "tag_neutral_fg": m["tag_neutral_fg"],
        # ink tints (color-mix(text N%, transparent) in the CSS)
        "divider": rgba(text, .16), "divider_strong": rgba(text, .30), "line": rgba(text, .55),
        "border_hover": rgba(text, .45), "muted": rgba(text, .55),
        "label": rgba(text, .70), "header_text": rgba(text, .60),
        "text_hover": rgba(text, .07), "text_pressed": rgba(text, .14),
        "row_hover": rgba(text, .04), "row_alt": rgba(text, .025),
        "disabled_text": rgba(text, .35), "disabled_border": rgba(text, .10),
        "scroll_handle": rgba(text, .18), "scroll_handle_hover": rgba(text, .34),
        # accent tints
        "accent_hover": rgba(acc, .12), "accent_press_tint": rgba(acc, .22),
        "ghost_hover": rgba(acc, .10), "ghost_press": rgba(acc, .18),
        "selection": rgba(acc, .30),
        # solid equivalents for QPalette / painting / rich-text HTML
        "divider_solid": mix(text, bg, .16), "divider_strong_solid": mix(text, bg, .30),
        "line_solid": mix(text, bg, .55),
        "muted_solid": mix(text, bg, .55), "label_solid": mix(text, bg, .70),
        "selection_solid": mix(acc, bg, .30), "row_alt_solid": mix(text, bg, .025),
        "disabled_solid": mix(text, bg, .35),
        "backdrop": rgba(tokens["ramps"]["neutral"][8], .5),
        "shadow": m["shadow"], "shadow_strength": str(m.get("shadow_strength", 1.0)),
        # the state channel: six roles + dim (muted text, the seventh word the spines use)
        **{role: m[role] for role in STATE_ROLES},
        "dim": mix(text, bg, .55),
        # typography slots (pixel sizes — Qt setPixelSize, CSS px)
        "font_heading": f["heading"]["family"], "heading_weight": str(f["heading"]["weight"]),
        "font_body": body["family"], "fs_body": str(body["size"]),
        "body_weight": str(body.get("weight", 400)),
        "font_mono": str(mono.get("family", "")), "fs_mono": str(mono.get("size", max(1, body["size"] - 1))),
        "font_ui": str(ui.get("family") or body["family"]), "fs_ui": str(ui.get("size", body["size"])),
        # reading
        "measure": str(reading["measure"]), "line_height": str(reading["line_height"]),
        # icons
        "icon_set": str(icons["set"]), "icon_stroke": str(icons["stroke_width"]),
    }
    for k, val in m.items():  # system-specific mode keys (e.g. fill, secondary) pass through
        v.setdefault(k, str(val))
        if isinstance(val, str) and val.startswith("#"):
            v.setdefault(f"{k}_hover", rgba(val, .14))
    # the shell chrome's ink (ruling d1e3043e): the title bar's glyphs are
    # painted pixmaps, so the system names which mode key inks them — the
    # text by default, a bar's own contrast key (Netrunner: fill_text) else
    chrome = tokens.get("chrome") or {}
    v["titlebar_ink"] = v.get(str(chrome.get("titlebar_ink", "text")), text)
    for k, px in tokens["radius"].items():
        v[f"radius_{k}"] = str(round(px))
    for k, px in tokens["space"].items():
        v[f"space_{k}"] = str(round(px))
    for k, (size, weight) in tokens["type"].items():
        v[f"fs_{k}"], v[f"fw_{k}"] = str(size), str(weight)
    return v


# ---- the web projection -----------------------------------------------------

def to_css(tokens: Dict[str, Any], selector: str = ":root") -> str:
    """The CSS custom-properties layer for a system — the ruling's second
    consumer (the Quarto site 8079ae0f derives its theme from this, never from
    Bootswatch). The first mode lands on `selector`; every other mode lands on
    `selector[data-mode="<mode>"]`, so a page switches modes by one attribute.
    Ramps, spacing, radii and the type scale are mode-independent and emitted
    once. Variable names mirror the resolved vocabulary with dashes."""
    out: List[str] = []
    first = modes(tokens)[0]
    static: List[str] = []
    for ramp, steps in tokens["ramps"].items():
        static += [f"  --{ramp}-{(i + 1) * 100}: {c};" for i, c in enumerate(steps)]
    static += [f"  --space-{k}: {v}px;" for k, v in tokens["space"].items()]
    static += [f"  --radius-{k}: {v}px;" for k, v in tokens["radius"].items()]
    static += [f"  --fs-{k}: {s}px;\n  --fw-{k}: {w};" for k, (s, w) in tokens["type"].items()]
    f = tokens["fonts"]
    static += [f'  --font-heading: "{f["heading"]["family"]}";',
               f'  --heading-weight: {f["heading"]["weight"]};',
               f'  --font-body: "{f["body"]["family"]}";',
               f'  --fs-body: {f["body"]["size"]}px;']
    if f.get("mono", {}).get("family"):
        static.append(f'  --font-mono: "{f["mono"]["family"]}";')
    reading = {**READING_DEFAULTS, **(tokens.get("reading") or {})}
    static += [f"  --measure: {reading['measure']}ch;", f"  --line-height: {reading['line_height']};"]
    per_mode = tuple(MODE_KEYS) + STATE_ROLES + ("dim", "muted", "divider", "divider_strong", "line",
                                                  "label", "selection", "accent_hover", "row_hover")
    for mode in modes(tokens):
        v = resolve(tokens, mode)
        keys = list(per_mode) + [k for k in tokens["modes"][mode] if k not in per_mode and k in v]
        body = [f"  --{k.replace('_', '-')}: {v[k]};" for k in keys if k != "shadow_strength"]
        body.append(f"  --shadow-strength: {v['shadow_strength']};")
        sel = selector if mode == first else f'{selector}[data-mode="{mode}"]'
        block = body if mode != first else static + body
        out.append("%s {\n%s\n}" % (sel, "\n".join(block)))
    return "/* %s — design tokens, projected by cjm-substrate-qt-kit (schema v%d) */\n%s\n" % (
        tokens["name"], SCHEMA_VERSION, "\n\n".join(out))
