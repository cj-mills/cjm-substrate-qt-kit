"""The Qt half of each design system (ruling a439c226, design 0858bbd0): a
system's DATA — its tokens.json and the fonts it names — lives in
cjm-design-system (`cjm_design_system.systems`: available / locate /
tokens_path); the kit keeps what only Qt reads, one directory per system slug
under this package — `qss/` (the system's stylesheet templates; a system
without one renders under Classical's) and an optional `widgets.py` (painted
widgets QSS cannot draw — Netrunner's chamfered headers).

    qss_dir("netrunner", root)  -> the kit's netrunner/qss
    qss_dir("mysystem", root)   -> root/qss when a trial system carries its own, else Classical's"""

from pathlib import Path

SYSTEMS_DIR = Path(__file__).parent
BASE_QSS = SYSTEMS_DIR / "classical" / "qss"   # the shared templates a system may replace


def qss_dir(
    slug: str,   # The system's slug (tokens.slug)
    root: Path,  # The system's data directory (cjm_design_system.systems.locate)
) -> Path:  # The directory of QSS templates the system renders under
    """A trial system's own `qss/` beside its tokens.json first, else the
    kit's templates for that slug, else Classical's (the base every system
    may replace)."""
    for d in (Path(root) / "qss", SYSTEMS_DIR / slug / "qss"):
        if d.is_dir():
            return d
    return BASE_QSS
