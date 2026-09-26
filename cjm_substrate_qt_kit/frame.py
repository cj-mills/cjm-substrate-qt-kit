"""The window frame — client-side decorations as a shell surface (ruling
d1e3043e; the app-shell ruling 2bae2cc1's WINDOW FRAME, completed).

The window manager paints server-side decorations from the GTK theme and
its light/dark setting — no stylesheet, palette or token reaches them, so
the one element every window shows first was the one element the design
system could not paint (Classical light matched GNOME light by
coincidence; Netrunner did not). A shell window therefore OWNS its frame:

- the HOST is a frameless, translucent QMainWindow (`FramedWindow`); it
  paints nothing itself — a translucent top-level draws nothing from its
  own stylesheet rule (probed offscreen 2026-09-25), but a child does;
- the FRAME (`ShellFrame`, a QFrame[kitFrame="true"]) is that child: the
  system's stylesheet gives it background, border and radius from the
  tokens (radius_lg under Classical, a hard edge under Netrunner), and the
  corners beyond the radius stay transparent;
- the TITLE BAR (`TitleBar`) rides the frame's top: the title, the window
  verbs minimize / maximize-restore / close as Lucide glyphs inked by the
  system (tokens `chrome.titlebar_ink`, restyled on the ONE change signal),
  drag through QWindow.startSystemMove, double-click maximizes;
- RESIZE rides a GRIP band INSIDE the frame's edge — the frame's own
  padding, painted with it, so nothing of the window is transparent but
  the corners: a press in the band calls QWindow.startSystemResize with
  the edges under the pointer, and the window manager keeps owning
  placement — snapping, Super+drag, Alt+F4 and tiling all still work. (A
  transparent margin AROUND the frame was the first form; a tiled window
  then showed a gap the width of the margin on every edge — user drive
  2026-09-25 — because the frame sat inside the geometry the tile fills.)
- MAXIMIZED / fullscreen drops the radius, the border and the grip (the
  frame's `kitMaximized` property; the stylesheet answers it).

The FALLBACK: `decorations="system"` (prefs / CJM_DECORATIONS) keeps the
window manager's frame — the title bar hides, the frame loses its border,
and the mode is hinted to the platform (`hint_system_scheme`) so the
decorations at least follow light/dark where the platform honours it. It
is the fallback for tiling window managers, accessibility and remote
displays, never the default. Dialogs take the same frame through
`modal.ModalFrame`."""

from typing import Dict, Optional

from PySide6.QtCore import QEvent, QPoint, QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QToolButton,
                               QVBoxLayout, QWidget)

from . import prefs
from .icons import IconSet
from .theme import current, current_theme, on_change
from .widgets import repolish

GRIP = 6            # px of resize band inside the frame's edge (client mode, not maximized)
VERB_ICON = 14      # px, the window verbs' glyph size


def edge_value(edges) -> int:
    """Qt.Edge flags as an int (PySide's flag enums carry .value)."""
    return int(getattr(edges, "value", edges))


_CURSORS: Dict[int, Qt.CursorShape] = {
    edge_value(Qt.Edge.LeftEdge): Qt.CursorShape.SizeHorCursor,
    edge_value(Qt.Edge.RightEdge): Qt.CursorShape.SizeHorCursor,
    edge_value(Qt.Edge.TopEdge): Qt.CursorShape.SizeVerCursor,
    edge_value(Qt.Edge.BottomEdge): Qt.CursorShape.SizeVerCursor,
    edge_value(Qt.Edge.TopEdge | Qt.Edge.LeftEdge): Qt.CursorShape.SizeFDiagCursor,
    edge_value(Qt.Edge.BottomEdge | Qt.Edge.RightEdge): Qt.CursorShape.SizeFDiagCursor,
    edge_value(Qt.Edge.TopEdge | Qt.Edge.RightEdge): Qt.CursorShape.SizeBDiagCursor,
    edge_value(Qt.Edge.BottomEdge | Qt.Edge.LeftEdge): Qt.CursorShape.SizeBDiagCursor,
}


def verb_icon(name: str, size: int = VERB_ICON):
    """A window-verb glyph inked by the live system (`titlebar_ink`): the
    Theme's icon set when one is applied, the kit's own set headless."""
    t = current()
    if t is not None:
        return t.icon(name, "titlebar_ink", size)
    v = current_theme()
    return IconSet().icon(name, v["titlebar_ink"], size, v["disabled_text"])


def verb_button(parent: QWidget, verb: str, tip: str, fn) -> QToolButton:
    """One window verb: a QToolButton[role="window-verb"][verb=<verb>] the
    stylesheet paints (the close verb's hover is the danger role)."""
    btn = QToolButton(parent)
    btn.setProperty("role", "window-verb")
    btn.setProperty("verb", verb)
    btn.setToolTip(tip)
    btn.setAutoRaise(True)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setIconSize(QSize(VERB_ICON, VERB_ICON))
    btn.clicked.connect(lambda _checked=False: fn())
    return btn


class TitleBar(QFrame):
    """The frame's top row: title left, the window verbs right, a leading
    and a trailing slot for an app's own chrome (an icon, a breadcrumb, a
    session chip). Drag moves the window through the window manager."""

    def __init__(self, host: QWidget, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setProperty("role", "titlebar")
        self._host = host
        self._maximized = False
        self.leading = QHBoxLayout()
        self.leading.setContentsMargins(0, 0, 0, 0)
        self.leading.setSpacing(6)
        self.trailing = QHBoxLayout()
        self.trailing.setContentsMargins(0, 0, 0, 0)
        self.trailing.setSpacing(6)
        self.title = QLabel("", self)
        self.title.setProperty("role", "window-title")
        self.title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.minimize_btn = verb_button(self, "minimize", "Minimize", self.minimize)
        self.maximize_btn = verb_button(self, "maximize", "Maximize", self.toggle_maximize)
        self.close_btn = verb_button(self, "close", "Close", self.close_window)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 3, 6, 3)
        lay.setSpacing(4)
        lay.addLayout(self.leading)
        lay.addWidget(self.title, 1)
        lay.addLayout(self.trailing)
        lay.addWidget(self.minimize_btn)
        lay.addWidget(self.maximize_btn)
        lay.addWidget(self.close_btn)
        on_change(self._on_theme)
        self._on_theme(None)

    # -- state --

    def set_title(self, text: str) -> None:
        self.title.setText(text)

    def set_verbs(self, minimize: bool = True, maximize: bool = True,
                  close: bool = True) -> None:
        """Which window verbs the bar offers (a tool window may drop some)."""
        self.minimize_btn.setVisible(minimize)
        self.maximize_btn.setVisible(maximize)
        self.close_btn.setVisible(close)

    def set_maximized(self, flag: bool) -> None:
        """The maximize verb becomes restore (and back); the stylesheet may
        answer the `kitMaximized` property too (`maximized` is QWidget's own
        read-only property — a dynamic property of that name never lands)."""
        self._maximized = bool(flag)
        self.setProperty("kitMaximized", self._maximized)
        self.maximize_btn.setToolTip("Restore" if self._maximized else "Maximize")
        repolish(self)
        self._on_theme(None)

    def _on_theme(self, _theme) -> None:
        self.minimize_btn.setIcon(verb_icon("minus"))
        self.maximize_btn.setIcon(verb_icon("copy" if self._maximized else "square"))
        self.close_btn.setIcon(verb_icon("x"))

    # -- verbs --

    def minimize(self) -> None:
        self._host.showMinimized()

    def toggle_maximize(self) -> None:
        if self._host.isMaximized():
            self._host.showNormal()
        else:
            self._host.showMaximized()

    def close_window(self) -> None:
        self._host.close()

    # -- drag --

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._host.windowHandle()
            if handle is not None:
                handle.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.maximize_btn.isVisible():
            self.toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class ShellFrame(QFrame):
    """The painted frame: title bar, then the chrome slot (menubar, toolbars),
    the body (stretches) and the foot (find bar, job seat, status strip).
    The stylesheet paints it through `kitFrame`; `kitMaximized` and `chrome`
    (client / system) are the properties it answers. Its outer band (the
    1 px border + GRIP px of padding) is the resize grip: the band belongs
    to the frame itself, so the mouse reaches it under any child."""

    def __init__(self, host: QWidget, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setProperty("kitFrame", True)
        self.setProperty("chrome", "client")
        self.setProperty("kitMaximized", False)
        self.setMouseTracking(True)
        self._host = host
        self._band = 1 + GRIP
        self.titlebar = TitleBar(host, self)
        self.chrome = QVBoxLayout()
        self.chrome.setContentsMargins(0, 0, 0, 0)
        self.chrome.setSpacing(0)
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(0)
        self.foot = QVBoxLayout()
        self.foot.setContentsMargins(0, 0, 0, 0)
        self.foot.setSpacing(0)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(self._band, self._band, self._band, self._band)
        self._lay.setSpacing(0)
        self._lay.addWidget(self.titlebar)
        self._lay.addLayout(self.chrome)
        self._lay.addLayout(self.body, 1)
        self._lay.addLayout(self.foot)

    @property
    def band(self) -> int:
        """The current grip band in px (0 when maximized or under the window
        manager's decorations — no border, no padding, no grip)."""
        return self._band

    def set_state(self, maximized: bool, client: bool) -> None:
        changed = (self.property("kitMaximized") != bool(maximized)
                   or self.property("chrome") != ("client" if client else "system"))
        self.setProperty("kitMaximized", bool(maximized))
        self.setProperty("chrome", "client" if client else "system")
        self._band = (1 + GRIP) if (client and not maximized) else 0
        self._lay.setContentsMargins(self._band, self._band, self._band, self._band)
        if changed:
            repolish(self)

    # -- the resize grip --

    def edges_at(self, pos: QPoint):
        """The Qt.Edge flags under `pos` (frame coordinates) when it sits in
        the grip band; 0 inside the content, when maximized, or under the
        window manager's decorations."""
        edges = Qt.Edge(0)
        if not self._band:
            return edges
        r = self.rect()
        if pos.x() < self._band:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= r.width() - self._band:
            edges |= Qt.Edge.RightEdge
        if pos.y() < self._band:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= r.height() - self._band:
            edges |= Qt.Edge.BottomEdge
        return edges

    def mousePressEvent(self, event) -> None:
        edges = self.edges_at(event.position().toPoint())
        if edge_value(edges) and event.button() == Qt.MouseButton.LeftButton:
            handle = self._host.windowHandle()
            if handle is not None:
                handle.startSystemResize(edges)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        shape = _CURSORS.get(edge_value(self.edges_at(event.position().toPoint())))
        if shape is None:
            self.unsetCursor()
        else:
            self.setCursor(shape)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self.unsetCursor()
        super().leaveEvent(event)


def hint_system_scheme(app: QApplication, theme) -> None:
    """The fallback's mode hint: when the window manager paints the frame,
    tell the platform the application's scheme so the decorations follow
    the system's mode where the platform honours it (Qt >= 6.8 exposes
    QStyleHints.setColorScheme; older platforms ignore the call). A theme
    that FOLLOWS the OS ("auto") leaves the platform's own scheme in place —
    overriding it would cut the OS-following loop."""
    hints = app.styleHints()
    if theme is None or getattr(theme, "requested", "auto") == "auto":
        if hasattr(hints, "unsetColorScheme"):
            hints.unsetColorScheme()
        return
    if not hasattr(hints, "setColorScheme"):
        return
    dark = QColor(theme.vars["bg"]).lightnessF() < 0.5
    hints.setColorScheme(Qt.ColorScheme.Dark if dark else Qt.ColorScheme.Light)


class FramedWindow(QMainWindow):
    """The frameless, translucent HOST whose central widget is the painted
    frame. Apps never add QMainWindow menus, toolbars or a status bar to it
    (they would sit outside the frame): the frame's `chrome` / `body` /
    `foot` layouts are the seats, and `setWindowTitle` feeds the title bar."""

    def __init__(self, parent: Optional[QWidget] = None, *,
                 decorations: Optional[str] = None):
        super().__init__(parent)
        self.setProperty("kitShell", True)
        self.frame = ShellFrame(self, self)
        self.titlebar = self.frame.titlebar
        self.setCentralWidget(self.frame)
        self.setContentsMargins(0, 0, 0, 0)      # the frame fills the geometry — no gap when tiled
        self.decorations, self.decorations_source = prefs.decorations(decorations)
        self._apply_decorations()

    # -- decorations --

    @property
    def client_decorations(self) -> bool:
        return self.decorations == "client"

    def set_decorations(self, mode: str, *, persist: bool = False) -> None:
        """Switch between the shell's frame and the window manager's (the
        fallback toggle); a visible window re-shows itself, since a window
        flag change hides it."""
        if mode not in prefs.DECORATIONS:
            raise ValueError(f"decorations: expected one of {prefs.DECORATIONS}, got {mode!r}")
        was_visible = self.isVisible()
        self.decorations = mode
        self._apply_decorations()
        if persist:
            prefs.write_decorations(mode)
        if was_visible:
            self.show()

    def _apply_decorations(self) -> None:
        client = self.client_decorations
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, client)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, client)
        self.titlebar.setVisible(client)
        self._sync_state()
        if not client:
            app = QApplication.instance()
            if app is not None:
                hint_system_scheme(app, current())

    def _sync_state(self) -> None:
        client = self.client_decorations
        maxed = self.isMaximized() or self.isFullScreen()
        self.frame.set_state(maxed, client)
        self.titlebar.set_maximized(maxed)

    def changeEvent(self, event) -> None:
        """The window manager's state changes (a keyboard maximize, a tile)
        arrive here; the title bar's own verbs sync below as well, since a
        platform may report the change late or — offscreen — never."""
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._sync_state()

    def showMaximized(self) -> None:
        super().showMaximized()
        self._sync_state()

    def showNormal(self) -> None:
        super().showNormal()
        self._sync_state()

    def showFullScreen(self) -> None:
        super().showFullScreen()
        self._sync_state()

    def setWindowTitle(self, title: str) -> None:
        super().setWindowTitle(title)
        self.titlebar.set_title(title)

    # -- the resize grip (the frame's band; host coordinates map onto it) --

    def edges_at(self, pos: QPoint):
        """The Qt.Edge flags under `pos` (host coordinates) — the frame's
        band decides (see ShellFrame.edges_at)."""
        return self.frame.edges_at(self.frame.mapFrom(self, pos))
