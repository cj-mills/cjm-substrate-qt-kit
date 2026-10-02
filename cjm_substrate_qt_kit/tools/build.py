"""Build the static Qt projections of a design system, no QApplication
needed: one rendered QSS per mode (for Qt Designer or a plain setStyleSheet)
and the recolored indicator SVGs. The web projections build from
cjm-design-system (`python -m cjm_design_system.tools.build`, design 0858bbd0).

    python -m cjm_substrate_qt_kit.tools.build netrunner -o build/
    python -m cjm_substrate_qt_kit.tools.build path/to/mysystem/tokens.json -o build/ --check
"""

import argparse
from pathlib import Path

from cjm_design_system import systems as design_systems, tokens as T

from .. import systems
from ..icons import IconSet


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cjm_substrate_qt_kit.tools.build")
    ap.add_argument("system", help="a vendored slug or a tokens.json path")
    ap.add_argument("-o", "--out", default="build")
    ap.add_argument("--check", action="store_true", help="validate only; write nothing")
    a = ap.parse_args(argv)
    root = design_systems.locate(a.system)
    tok = T.load(root / "tokens.json")
    T.check(tok, str(root / "tokens.json"))
    if a.check:
        print(f"{T.slug(tok)}: schema v{T.SCHEMA_VERSION} OK — modes {T.modes(tok)}")
        return 0
    from ..theme import render_qss  # Qt-free at import; render_qss itself is headless
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = T.slug(tok)
    icons = IconSet([root / "icons"] if (root / "icons").is_dir() else [],
                    stroke_width=float((tok.get("icons") or {}).get("stroke_width", 1.5)))
    for mode in T.modes(tok):
        qss = render_qss(tok, mode, icons, out / "icons" / mode, systems.qss_dir(s, root))
        (out / f"{s}-{mode}.qss").write_text(qss, encoding="utf-8")
        print(f"wrote {out / f'{s}-{mode}.qss'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
