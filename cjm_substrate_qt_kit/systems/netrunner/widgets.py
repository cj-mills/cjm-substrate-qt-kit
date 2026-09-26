"""Netrunner's painted widgets: what QSS cannot draw (chamfered header bars,
tracked display type). Colors come from the live theme's vars and repaint on
its change signal."""

from cjm_substrate_qt_kit.theme import current, on_change
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPolygonF
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget


def tracked(s: str, role: str = "display", spacing: float = 125) -> QLabel:
    """Display / section label with letter-spacing (QSS has none)."""
    lb = QLabel(s)
    lb.setProperty("role", role)
    f = lb.font()
    f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, spacing)
    lb.setFont(f)
    return lb


def section_title(s: str) -> QLabel:
    lb = tracked(f"=== {s.upper()} ===", "section", 130)
    lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lb


class ChamferHeader(QWidget):
    """Solid fill bar with the top-left corner cut. Colors come from the live theme."""
    clicked = Signal()

    def __init__(self, text: str, theme=None, height: int = 60, parent=None):
        super().__init__(parent)
        self.text = text
        self.theme = theme if theme is not None else current()
        self.cut = int((self.theme.tokens if self.theme else {}).get("chamfer", 28))
        self.setFixedHeight(height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        on_change(self._on_theme)

    def _on_theme(self, theme) -> None:
        self.theme = theme
        self.cut = int(theme.tokens.get("chamfer", 28))
        self.update()

    def mousePressEvent(self, e):
        self.clicked.emit()

    def paintEvent(self, _e):
        v = self.theme.vars
        w, h, c = self.width(), self.height(), self.cut
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(v.get("fill", v["accent"])))
        p.drawPolygon(QPolygonF([QPointF(c, 0), QPointF(w, 0), QPointF(w, h), QPointF(0, h), QPointF(0, c)]))
        p.setPen(QColor(v.get("fill_text", v["bg"])))
        f = QFont(v["font_body"])
        f.setPixelSize(14)
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 108)
        p.setFont(f)
        p.drawText(QRectF(0, 0, w, h - 4), Qt.AlignmentFlag.AlignCenter, self.text.upper())
        p.end()


class Panel(QWidget):
    """Chamfered header + surface body. Click the header to collapse."""

    def __init__(self, title: str, theme=None, collapsed: bool = False, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.header = ChamferHeader(title, theme)
        self.frame = QFrame()
        self.frame.setProperty("panel", True)
        self.body = QVBoxLayout(self.frame)
        self.body.setContentsMargins(11, 18, 11, 18)
        self.body.setSpacing(14)
        v.addWidget(self.header)
        v.addWidget(self.frame)
        self.header.clicked.connect(lambda: self.frame.setVisible(not self.frame.isVisible()))
        self.frame.setVisible(not collapsed)

    def add(self, w: QWidget) -> QWidget:
        self.body.addWidget(w)
        return w


def para(s: str, role=None) -> QLabel:
    lb = QLabel(s)
    lb.setWordWrap(True)
    lb.setAlignment(Qt.AlignmentFlag.AlignJustify | Qt.AlignmentFlag.AlignTop)
    if role:
        lb.setProperty("role", role)
    return lb


def gallery_page(theme=None) -> QWidget:
    """The system's own gallery tab: the panel + chamfer grammar the shared
    component pages cannot show (the gallery lists this page when a system
    module defines it)."""
    page = QWidget()
    v = QVBoxLayout(page)
    v.setSpacing(18)
    v.addWidget(tracked("NETRUNNER: TERMINAL", "display", 140))
    v.addWidget(section_title("Software"))
    music = Panel("Music", theme)
    music.add(para("Netrunning is at least 15% cool vibes."))
    for m in ("TRACK 01 - SIGNAL", "TRACK 02 - OVERCLOCK", "TRACK 03 - BLACKWALL"):
        music.add(QPushButton(m))
    v.addWidget(music)
    notes = Panel("Notes", theme, collapsed=True)
    notes.add(para("Click a header to collapse its panel."))
    v.addWidget(notes)
    err = QLabel("ERROR:YPD5SSQ :::  USER NOT FOUND")
    err.setProperty("role", "error")
    v.addWidget(err)
    v.addStretch(1)
    return page
