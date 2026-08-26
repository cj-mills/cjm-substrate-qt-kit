"""Layout roles for the application lane — the FastHTML-era framework's Qt
seed (design-system arc item 33b70d6f; ported from the platform-agnostic
layout-system.md registries, which anticipated this port by design).

Three orthogonal axes, as DATA: MODE (width — how much horizontal space),
SHAPE (aspect ratio — which way splits run), HEIGHT tier (absolute vertical
space). Roles, not pixels, are the contract: mode boundaries are the only
sanctioned layout shifts (DR5); within a mode only density may change.

Component response vocabulary (R1/R2/R3) and its Qt mapping:
  R1 grow  — content that benefits from more area: QSizePolicy.Expanding.
  R2 cap   — content with a maximum useful width (prose, forms, dialogs):
             setMaximumWidth at the useful max; margin absorbs the rest.
  R3 shift — same units, more revealed (toolbars gaining labels, tables
             gaining columns, hint overlays gaining columns): afford().
Container-vs-viewport (DR3) is Qt's native model — widgets lay out against
their PARENT's allocation, so component-level decisions take the container
width (afford), never the window's."""

from typing import Dict, Tuple

# Width roles (px lower bounds). M3 Standard is the primary design target.
MODES: Tuple[Tuple[str, str, int], ...] = (
    ("M1", "pocket", 0), ("M2", "compact", 640), ("M3", "standard", 1024),
    ("M4", "spacious", 1536), ("M5", "generous", 2560), ("M6", "vast", 3840))

# Aspect-ratio roles (width/height lower bounds). S4 is the default target.
SHAPES: Tuple[Tuple[str, str, float], ...] = (
    ("S1", "portrait", 0.0), ("S2", "squarish", 0.85),
    ("S3", "landscape-3-2", 1.20), ("S4", "landscape-16-9", 1.55),
    ("S5", "ultrawide", 2.00), ("S6", "super-ultrawide", 3.00))

# Absolute-height roles (px lower bounds).
HEIGHTS: Tuple[Tuple[str, str, int], ...] = (
    ("H1", "short", 0), ("H2", "standard", 700),
    ("H3", "tall", 1100), ("H4", "very-tall", 1700))

# The correction workbench's ratified real windows (cc55a7b5) — points in
# M/S/H space, kept here so per-app breakpoints stay anchored to the roles.
NAMED_WINDOWS: Dict[str, Tuple[int, int]] = {
    "half-landscape": (1280, 1440),
    "full-landscape": (2560, 1440),
    "portrait": (1080, 2560)}


def _role(table, value) -> str:
    role = table[0][0]
    for rid, _name, floor in table:
        if value >= floor:
            role = rid
    return role


def mode(width: int) -> str:
    """Width -> mode role id ("M1".."M6")."""
    return _role(MODES, width)


def shape(width: int, height: int) -> str:
    """Aspect ratio -> shape role id ("S1".."S6")."""
    return _role(SHAPES, width / max(1, height))


def height_tier(height: int) -> str:
    """Absolute height -> height-tier role id ("H1".."H4")."""
    return _role(HEIGHTS, height)


def classify(width: int, height: int) -> Dict[str, str]:
    """One geometry -> its three role ids: {"mode", "shape", "height"}.
    A 1080x2560 rotated monitor is M3 + S1 + H4 — designing on width
    alone is the classic mistake the three axes exist to prevent."""
    return {"mode": mode(width), "shape": shape(width, height),
            "height": height_tier(height)}


def afford(avail: int, unit: int, cap: int, floor: int = 1) -> int:
    """R3 container affordance: how many fixed-width units fit in the
    CONTAINER's width, clamped to [floor, cap]. The component-internal
    dual of mode(): mode governs the workspace, afford governs a
    component's own density inside whatever pane holds it (DR3)."""
    return max(floor, min(avail // max(1, unit), cap))
