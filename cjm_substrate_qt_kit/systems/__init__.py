"""The design systems the kit ships as DATA (ruling a439c226): one directory
per system under this package — `tokens.json` (schema v1), `qss/` (the
system's stylesheet templates; a system without one renders under
Classical's), `fonts/` (the OFL files its tokens name), an optional
`widgets.py` (painted widgets QSS cannot draw — Netrunner's chamfered
headers) and an optional `icons/` dir when the system declares its own set.

    available()          -> ["classical", "netrunner"]
    locate("netrunner")  -> the system's directory
    locate("/path/to/mysystem/tokens.json") -> that file's directory

Custom systems come AFTER the gallery (abb6360d); a path-valued system is
how one is tried before it is vendored."""

from pathlib import Path
from typing import List, Union

SYSTEMS_DIR = Path(__file__).parent
BASE_QSS = SYSTEMS_DIR / "classical" / "qss"   # the shared templates a system may replace


def available() -> List[str]:
    """Every vendored system slug (a directory carrying a tokens.json)."""
    return sorted(p.parent.name for p in SYSTEMS_DIR.glob("*/tokens.json"))


def locate(system: Union[str, Path]) -> Path:
    """The directory of a system: a vendored slug, a directory holding a
    tokens.json, or a tokens.json path. Raises KeyError naming the slugs
    available when nothing matches."""
    p = Path(system)
    if p.suffix == ".json" and p.is_file():
        return p.parent
    if p.is_dir() and (p / "tokens.json").is_file():
        return p
    if (SYSTEMS_DIR / str(system) / "tokens.json").is_file():
        return SYSTEMS_DIR / str(system)
    raise KeyError(f"no design system {system!r} — vendored: {available()}; "
                   "or pass a directory holding tokens.json")


def tokens_path(system: Union[str, Path]) -> Path:
    return locate(system) / "tokens.json"
