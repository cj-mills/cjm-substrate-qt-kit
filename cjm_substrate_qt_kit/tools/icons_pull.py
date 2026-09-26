"""Pull named Lucide icons into the kit's vendored subset (or a system's own
`icons/` dir) — from a local clone first, upstream second.

    python -m cjm_substrate_qt_kit.tools.icons_pull search settings file-text
    python -m cjm_substrate_qt_kit.tools.icons_pull --from /path/to/lucide --into systems/mysystem/icons <names>
    python -m cjm_substrate_qt_kit.tools.icons_pull --list

The clone location is `--from`, else `$LUCIDE_CLONE`, else the sibling
checkout `../../lucide-icons/lucide` of the workspace; upstream is unpkg's
lucide-static. The kit never fetches at runtime (aa00d43c)."""

import argparse
import os
import urllib.request
from pathlib import Path

from ..icons import IconSet, KIT_ICONS

UPSTREAM = "https://unpkg.com/lucide-static@latest/icons/{}.svg"


def local_clone(explicit: str | None) -> Path | None:
    for cand in (explicit, os.environ.get("LUCIDE_CLONE")):
        if cand and (Path(cand) / "icons").is_dir():
            return Path(cand)
    here = Path(__file__).resolve()
    for parent in here.parents:
        sibling = parent.parent / "lucide-icons" / "lucide"
        if (sibling / "icons").is_dir():
            return sibling
    return None


def pull(names, into: Path, clone: Path | None, allow_upstream: bool = True) -> list:
    into.mkdir(parents=True, exist_ok=True)
    report = []
    for n in names:
        dest = into / f"{n}.svg"
        if dest.exists():
            report.append((n, "present"))
            continue
        src = clone / "icons" / f"{n}.svg" if clone else None
        if src is not None and src.exists():
            dest.write_bytes(src.read_bytes())
            report.append((n, f"clone {clone}"))
            continue
        if not allow_upstream:
            report.append((n, "MISSING (not in the clone; upstream disabled)"))
            continue
        try:
            with urllib.request.urlopen(UPSTREAM.format(n), timeout=30) as r:
                dest.write_bytes(r.read())
            report.append((n, "upstream"))
        except Exception as e:  # noqa: BLE001
            report.append((n, f"MISSING ({e})"))
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cjm_substrate_qt_kit.tools.icons_pull")
    ap.add_argument("names", nargs="*", help="Lucide icon names")
    ap.add_argument("--from", dest="clone", default=None, help="a local Lucide clone")
    ap.add_argument("--into", default=None, help="target dir (default: the kit's icons/)")
    ap.add_argument("--no-upstream", action="store_true", help="never fetch; the clone only")
    ap.add_argument("--list", action="store_true", help="list the vendored subset and exit")
    a = ap.parse_args(argv)
    if a.list:
        print("\n".join(IconSet().names()))
        return 0
    if not a.names:
        ap.error("name at least one icon (or --list)")
    clone = local_clone(a.clone)
    into = Path(a.into) if a.into else KIT_ICONS
    for name, how in pull(a.names, into, clone, not a.no_upstream):
        print(f"  {name:<24} {how}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
