"""Build the static projections of a design system, no QApplication needed:
one rendered QSS per mode (for Qt Designer or a plain setStyleSheet), the
recolored indicator SVGs, and the CSS custom-properties layer (the web
consumer, 8079ae0f).

    python -m cjm_substrate_qt_kit.tools.build netrunner -o build/
    python -m cjm_substrate_qt_kit.tools.build path/to/mysystem/tokens.json -o build/ --check
"""

import argparse
from pathlib import Path

from .. import systems, tokens as T
from ..icons import IconSet


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cjm_substrate_qt_kit.tools.build")
    ap.add_argument("system", help="a vendored slug or a tokens.json path")
    ap.add_argument("-o", "--out", default="build")
    ap.add_argument("--check", action="store_true", help="validate only; write nothing")
    a = ap.parse_args(argv)
    root = systems.locate(a.system)
    tok = T.load(root / "tokens.json")
    T.check(tok, str(root / "tokens.json"))
    if a.check:
        print(f"{T.slug(tok)}: schema v{T.SCHEMA_VERSION} OK — modes {T.modes(tok)}")
        return 0
    from ..theme import render_qss  # Qt-free at import; render_qss itself is headless
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    qss_dir = root / "qss" if (root / "qss").is_dir() else systems.BASE_QSS
    icons = IconSet([root / "icons"] if (root / "icons").is_dir() else [],
                    stroke_width=float((tok.get("icons") or {}).get("stroke_width", 1.5)))
    s = T.slug(tok)
    for mode in T.modes(tok):
        qss = render_qss(tok, mode, icons, out / "icons" / mode, qss_dir)
        (out / f"{s}-{mode}.qss").write_text(qss, encoding="utf-8")
        print(f"wrote {out / f'{s}-{mode}.qss'}")
    (out / f"{s}.css").write_text(T.to_css(tok), encoding="utf-8")
    print(f"wrote {out / f'{s}.css'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
