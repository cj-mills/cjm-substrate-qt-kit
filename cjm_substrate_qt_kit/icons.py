"""Icons recolored at runtime from the vendored Lucide subset (ISC; the
kit's default icon set per the charter 8b7351e4 — a design system may declare
another set in its tokens' `icons` block and ship its own `icons/` dir).

Lookup order: a system's own icon dir (when it has one), then the kit's
`icons/`. A few glyphs the stylesheets need for indicators are built in so a
theme renders before any icon is vendored. `tools/icons_pull.py` adds named
icons from the user's local Lucide clone or upstream."""

import hashlib
from pathlib import Path
from typing import List, Optional, Sequence, Union

KIT_ICONS = Path(__file__).parent / "icons"

_HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
         'fill="none" stroke="currentColor" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">')

BUILTIN = {
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-up": '<path d="m18 15-6-6-6 6"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "minus": '<path d="M5 12h14"/>',
    "dot": '<circle cx="12" cy="12" r="5" fill="currentColor" stroke="none"/>',
}


class IconSet:
    """Named SVG icons -> recolored SVG text, files (for QSS url()), QIcons."""

    def __init__(self, dirs: Sequence[Union[str, Path]] = (), stroke_width: float = 1.5):
        self.dirs: List[Path] = [Path(d) for d in dirs] + [KIT_ICONS]
        self.stroke_width = stroke_width  # Lucide ships 2; 1.5 sits better beside a serif

    def names(self) -> List[str]:
        """Every icon name resolvable from the dirs + the built-ins."""
        found = set(BUILTIN)
        for d in self.dirs:
            if d.is_dir():
                found |= {p.stem for p in d.glob("*.svg")}
        return sorted(found)

    def svg(self, name: str) -> str:
        for d in self.dirs:
            p = d / f"{name}.svg"
            if p.exists():
                s = p.read_text(encoding="utf-8")
                return s.replace('stroke-width="2"', f'stroke-width="{self.stroke_width}"')
        if name in BUILTIN:
            return _HEAD.format(sw=self.stroke_width) + BUILTIN[name] + "</svg>"
        raise KeyError(f"icon '{name}' not found in {self.dirs} "
                       "(python -m cjm_substrate_qt_kit.tools.icons_pull <name> adds it)")

    def colored(self, name: str, color: str) -> str:
        return self.svg(name).replace("currentColor", _svg_color(color))

    def write(self, name: str, color: str, out_dir: Union[str, Path]) -> str:
        """Write a recolored SVG file; returns a forward-slash path for QSS url()."""
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        data = self.colored(name, color)
        p = out / f"{name}-{hashlib.md5(data.encode()).hexdigest()[:8]}.svg"
        if not p.exists():
            p.write_text(data, encoding="utf-8")
        return p.resolve().as_posix()

    # -- Qt side (imported lazily so the module stays headless-safe) --
    def icon(self, name: str, color: str, size: int = 18, disabled_color: Optional[str] = None):
        from PySide6.QtGui import QIcon
        ic = QIcon()
        ic.addPixmap(self.pixmap(name, color, size), QIcon.Mode.Normal)
        if disabled_color:
            ic.addPixmap(self.pixmap(name, disabled_color, size), QIcon.Mode.Disabled)
        return ic

    def pixmap(self, name: str, color: str, size: int = 18, dpr: float = 2.0):
        from PySide6.QtCore import QByteArray, Qt
        from PySide6.QtGui import QPainter, QPixmap
        from PySide6.QtSvg import QSvgRenderer
        r = QSvgRenderer(QByteArray(self.colored(name, color).encode()))
        pm = QPixmap(int(size * dpr), int(size * dpr))
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        r.render(p)
        p.end()
        pm.setDevicePixelRatio(dpr)
        return pm


def _svg_color(c: str) -> str:
    """QSS rgba(r,g,b,0-255) -> SVG rgb() plus opacity attributes (spliced into the attr)."""
    if c.startswith("rgba("):
        r, g, b, a = [int(x) for x in c[5:-1].split(",")]
        return f"rgb({r},{g},{b})\" stroke-opacity=\"{a / 255:.3f}\" fill-opacity=\"{a / 255:.3f}"
    return c
