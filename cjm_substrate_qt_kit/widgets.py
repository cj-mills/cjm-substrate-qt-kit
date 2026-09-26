"""Small helpers that map the design system's component classes onto Qt —
the property vocabulary every app styles through (role / variant / tag /
card / elevated) instead of hex, QSS or fonts (the charter 8b7351e4).

    text("On the shortness of life", "h2")   # QLabel[role="h2"]
    button("Subscribe", "primary")           # QPushButton[variant="primary"]
    tag("Essay") / tag("Archive", "neutral") # QLabel[tag=...]
    Card(kicker, title, body, meta, elevation="md")
    Segmented(["Day", "Week", "Month"], 1)
    hr()                                     # QFrame[role="hr"]

Anything QSS cannot express is done in code here (letter-spacing in
kicker(), drop shadows in elevate()). Change a property after the widget is
shown -> repolish() so the stylesheet re-matches."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QButtonGroup, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

# shadow-sm/md/lg: (y offset, blur, alpha 0-1)
ELEVATION = {"sm": (1, 4, .14), "md": (3, 20, .16), "lg": (12, 48, .22)}


def repolish(w: QWidget) -> None:
    """Call after changing a dynamic property so QSS re-matches."""
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


def text(s: str, role: Optional[str] = None, wrap: bool = True) -> QLabel:
    lb = QLabel(s)
    if role:
        lb.setProperty("role", role)
    lb.setWordWrap(wrap)
    return lb


def kicker(s: str) -> QLabel:
    lb = text(s.upper(), "kicker", False)
    f = lb.font()
    f.setLetterSpacing(f.SpacingType.PercentageSpacing, 110)  # QSS has no letter-spacing
    lb.setFont(f)
    return lb


def tag(s: str, kind: str = "accent") -> QLabel:
    lb = QLabel(s)
    lb.setProperty("tag", kind)
    lb.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return lb


def button(s: str = "", variant: Optional[str] = None, icon=None) -> QPushButton:
    b = QPushButton(s)
    if variant:
        b.setProperty("variant", variant)
    if icon is not None:
        b.setIcon(icon)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def hr() -> QFrame:
    f = QFrame()
    f.setProperty("role", "hr")
    return f


def elevate(w: QWidget, level: str, theme=None) -> None:
    """A drop shadow at the system's strength (shadow + shadow_strength vars).
    `theme` is a Theme (default: the live one); re-call on theme change."""
    from .theme import current
    t = theme if theme is not None else current()
    y, blur, a = ELEVATION[level]
    k = float(t.vars["shadow_strength"]) if t is not None else 1.0
    fx = QGraphicsDropShadowEffect(w)
    fx.setOffset(0, y)
    fx.setBlurRadius(blur)
    c = QColor(t.vars["shadow"] if t is not None else "#000000")
    c.setAlphaF(min(1.0, a * k))
    fx.setColor(c)
    w.setGraphicsEffect(fx)
    w.setProperty("elevated", True)
    repolish(w)


class Card(QFrame):
    """The card class — bordered, unfilled by default. Card(kicker=, title=,
    body=, meta=, elevation='sm'|'md'|'lg'). An elevated card re-shadows on
    theme change by itself (shadow color differs per mode)."""

    def __init__(self, kicker_text: str = "", title: str = "", body: str = "", meta: str = "",
                 elevation: Optional[str] = None, theme=None, parent=None):
        super().__init__(parent)
        self.setProperty("card", True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(9)
        if kicker_text:
            lay.addWidget(kicker(kicker_text))
        if title:
            lay.addWidget(text(title, "title"))
        if body:
            lay.addWidget(text(body), 1)
        if meta:
            lay.addWidget(text(meta, "caption"))
        self.body = lay
        self.elevation = elevation
        if elevation:
            elevate(self, elevation, theme)
            from .theme import on_change
            on_change(self._reshadow)

    def _reshadow(self, theme) -> None:
        if self.elevation:
            elevate(self, self.elevation, theme)


class Segmented(QFrame):
    """The segmented control — exclusive checkable buttons sharing hairlines."""

    def __init__(self, options, current: int = 0, parent=None):
        super().__init__(parent)
        self.setProperty("role", "seg")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.group = QButtonGroup(self)
        for i, o in enumerate(options):
            b = QPushButton(o)
            b.setCheckable(True)
            b.setProperty("variant", "seg")
            b.setProperty("pos", "first" if i == 0 else "last" if i == len(options) - 1 else "mid")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(b, i)
            lay.addWidget(b)
        self.group.button(current).setChecked(True)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
