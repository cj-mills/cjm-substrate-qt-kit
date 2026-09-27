"""The switch-equals-launch check (finding b7e68f56): a design-system or mode
switch must land exactly what a fresh launch under the target lands, and a
round trip must restore the start pixel-for-pixel. A surface that bakes a
theme value at build or parse time and never re-derives it on the change
signal fails one leg or the other — the reading pane's parse-time link color
failed the round trip, the two-channel fonts failed switch-vs-launch.

Offscreen-drivable: build a window under A and grab every page; switch to B
and grab; build a FRESH window under B and grab; switch back to A and grab.
The gallery's test drives it over every kit surface; an app's test drives it
over its own window (the defect sweep, eb2e7c9b)."""

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QTabWidget, QTextEdit, QWidget

from .theme import apply_theme

# a window -> its pages as (name, show-this-page) pairs; None = the window as one page
Pages = Callable[[QWidget], Iterable[Tuple[str, Callable[[], None]]]]


@dataclass
class Diff:
    leg: str                                  # "round-trip" | "switch-vs-launch"
    page: str
    pixels: int                               # -1 when the grabs differ in size
    bbox: Optional[Tuple[int, int, int, int]]  # (x0, y0, x1, y1) of the differing pixels

    def __str__(self) -> str:
        where = "size differs" if self.pixels < 0 else f"{self.pixels} px, bbox {self.bbox}"
        return f"{self.leg} · {self.page}: {where}"


def tabs_of(tabs: QTabWidget) -> Iterable[Tuple[str, Callable[[], None]]]:
    """Every tab of `tabs` as a page (the gallery's shape:
    `pages=lambda w: tabs_of(w.tabs)`)."""
    for i in range(tabs.count()):
        yield tabs.tabText(i), (lambda i=i: tabs.setCurrentIndex(i))


def settle(root: Optional[QWidget] = None, rounds: int = 5) -> None:
    """Let polish, layout and deferred restores (seat restores ride the next
    event-loop pass) land before a grab. Text documents lay out
    INCREMENTALLY on a timer — a grab mid-layout reads a short scroll range —
    so every text pane under `root` is run to the end first (pageCount
    finishes the layout)."""
    app = QApplication.instance()
    for _ in range(rounds):
        app.processEvents()
    if root is not None:
        for pane in root.findChildren(QTextEdit):
            pane.document().pageCount()
        for _ in range(rounds):
            app.processEvents()


def grab(window: QWidget, pages: Optional[Pages] = None) -> Dict[str, QImage]:
    """Grab every page of `window` (ARGB32, comparable across grabs)."""
    fmt = QImage.Format.Format_ARGB32
    if pages is None:
        settle(window)
        return {"window": window.grab().toImage().convertToFormat(fmt)}
    out: Dict[str, QImage] = {}
    for name, show in list(pages(window)):
        show()
        settle(window)
        out[name] = window.grab().toImage().convertToFormat(fmt)
    return out


def diff_images(a: QImage, b: QImage) -> Tuple[int, Optional[Tuple[int, int, int, int]]]:
    """(differing pixel count, bbox) — (0, None) when identical; (-1, None)
    when the sizes differ. The per-pixel walk runs only on a mismatch."""
    if a.size() != b.size():
        return -1, None
    if a == b:
        return 0, None
    n, x0, y0, x1, y1 = 0, a.width(), a.height(), -1, -1
    for y in range(a.height()):
        for x in range(a.width()):
            if a.pixel(x, y) != b.pixel(x, y):
                n += 1
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    return n, (x0, y0, x1, y1)


def _compare(leg: str, want: Dict[str, QImage], got: Dict[str, QImage]) -> List[Diff]:
    diffs: List[Diff] = []
    for page in sorted(set(want) | set(got)):
        if page not in want or page not in got:
            diffs.append(Diff(leg, page, -1, None))
            continue
        n, bbox = diff_images(want[page], got[page])
        if n:
            diffs.append(Diff(leg, page, n, bbox))
    return diffs


def check_switch(build: Callable[[], QWidget], a: str, b: str, *,
                 mode: str = "auto", pages: Optional[Pages] = None,
                 size: Optional[Tuple[int, int]] = None) -> List[Diff]:
    """Run both legs for systems `a` -> `b` -> `a` and return every differing
    page ([] = the invariant holds). `build` makes a window under the live
    theme; `pages(window)` names its pages (None = the whole window); the
    theme is left on `a`."""
    app = QApplication.instance()
    theme = apply_theme(app, a, mode)

    def launch() -> QWidget:
        w = build()
        if size is not None:
            w.resize(*size)
        w.show()
        settle(w)
        return w

    win = launch()
    start = grab(win, pages)
    theme.set_system(b, mode)
    switched = grab(win, pages)
    focus = app.focusWidget()
    fresh = launch()
    launched = grab(fresh, pages)
    fresh.close()
    # the fresh window took activation: hand it back, or the focus ring differs
    win.activateWindow()
    if focus is not None:
        focus.setFocus()
    theme.set_system(a, mode)
    back = grab(win, pages)
    win.close()
    return _compare("switch-vs-launch", launched, switched) + _compare("round-trip", start, back)
