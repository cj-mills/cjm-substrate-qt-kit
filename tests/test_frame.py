"""The window frame contract (ruling d1e3043e): a client-decorated window is
a frameless translucent host around the painted frame — transparent beyond
the frame, the frame's border on its own edge, the title bar carrying the
title and the window verbs; maximized drops the grip and the radius; the
system fallback hands the frame back to the window manager."""

import pytest
from PySide6.QtCore import QPoint, Qt

from cjm_substrate_qt_kit import prefs
from cjm_substrate_qt_kit.frame import GRIP, FramedWindow, TitleBar, edge_value
from cjm_substrate_qt_kit.theme import apply_theme


@pytest.fixture(autouse=True)
def isolated_prefs(tmp_path, monkeypatch):
    monkeypatch.setenv(prefs.PREFS_ENV, str(tmp_path / "theme.json"))
    monkeypatch.delenv(prefs.ENV_VAR, raising=False)
    monkeypatch.delenv(prefs.DECORATIONS_ENV, raising=False)
    yield


def test_client_decorations_are_the_default_and_frameless(app):
    win = FramedWindow()
    assert win.decorations == "client" and win.decorations_source == "default"
    assert win.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert win.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert win.titlebar.isVisibleTo(win)
    # the frame fills the window geometry (no transparent margin — a tiled
    # window showed it as a gap); the grip is the frame's own band
    assert win.contentsMargins().left() == 0
    assert win.frame.band == GRIP + 1
    assert win.frame.layout().contentsMargins().left() == GRIP + 1
    assert win.frame.property("kitFrame") is True
    win.setWindowTitle("the workbench")
    assert win.titlebar.title.text() == "the workbench"


def test_env_and_prefs_pick_the_fallback(app, monkeypatch):
    monkeypatch.setenv(prefs.DECORATIONS_ENV, "system")
    win = FramedWindow()
    assert (win.decorations, win.decorations_source) == ("system", "env")
    assert not (win.windowFlags() & Qt.WindowType.FramelessWindowHint)
    assert not win.titlebar.isVisibleTo(win)
    assert win.frame.band == 0 and win.frame.layout().contentsMargins().left() == 0
    assert win.frame.property("chrome") == "system"
    monkeypatch.delenv(prefs.DECORATIONS_ENV)
    monkeypatch.setenv(prefs.DECORATIONS_ENV, "nonsense")   # a typo never crashes a launch
    assert prefs.decorations() == ("client", "default")
    monkeypatch.delenv(prefs.DECORATIONS_ENV)
    prefs.write_decorations("system")
    assert prefs.decorations() == ("system", "prefs")
    assert prefs.decorations("client") == ("client", "args")
    prefs.write("netrunner", "red")
    assert prefs.read() == {"system": "netrunner", "mode": "red", "decorations": "system"}


def test_toggle_decorations_at_runtime(app):
    win = FramedWindow()
    win.set_decorations("system", persist=True)
    assert prefs.read()["decorations"] == "system"
    assert not (win.windowFlags() & Qt.WindowType.FramelessWindowHint)
    win.set_decorations("client")
    assert win.windowFlags() & Qt.WindowType.FramelessWindowHint
    with pytest.raises(ValueError):
        win.set_decorations("wm")


def test_maximized_drops_grip_border_and_swaps_the_verb(app):
    win = FramedWindow()
    win.resize(400, 300)
    win.show()
    app.processEvents()
    win.titlebar.toggle_maximize()
    app.processEvents()
    assert win.isMaximized()
    assert win.frame.property("kitMaximized") is True
    assert win.titlebar.property("kitMaximized") is True
    assert win.frame.band == 0                             # no border, no padding, no grip
    assert win.titlebar.maximize_btn.toolTip() == "Restore"
    assert edge_value(win.edges_at(QPoint(1, 1))) == 0     # no grip while maximized
    win.titlebar.toggle_maximize()
    app.processEvents()
    assert not win.isMaximized() and win.frame.band == GRIP + 1
    assert win.titlebar.maximize_btn.toolTip() == "Maximize"
    win.close()


def test_grip_edges_and_cursor_map(app):
    win = FramedWindow()
    win.resize(400, 300)
    win.show()                       # the frame takes the geometry on layout
    app.processEvents()
    assert win.frame.width() == 400 and win.frame.height() == 300
    assert win.edges_at(QPoint(1, 1)) == (Qt.Edge.TopEdge | Qt.Edge.LeftEdge)
    assert win.edges_at(QPoint(399, 150)) == Qt.Edge.RightEdge
    assert win.edges_at(QPoint(200, 299)) == Qt.Edge.BottomEdge
    assert edge_value(win.edges_at(QPoint(200, 150))) == 0


def test_title_bar_verbs_and_slots(app):
    win = FramedWindow()
    bar: TitleBar = win.titlebar
    assert bar.property("role") == "titlebar"
    for btn, verb in ((bar.minimize_btn, "minimize"), (bar.maximize_btn, "maximize"),
                      (bar.close_btn, "close")):
        assert btn.property("role") == "window-verb" and btn.property("verb") == verb
        assert not btn.icon().isNull()
    bar.set_verbs(minimize=False)
    assert not bar.minimize_btn.isVisibleTo(bar)
    win.show()
    bar.close_window()
    assert not win.isVisible()


def test_frame_paints_transparent_corners_and_its_own_border(app):
    """The DoD probe: the frame fills the window — its border on the window's
    own edge, the tokens' background inside, only the corners beyond the
    radius transparent (a tiled window sits flush)."""
    t = apply_theme(app, "classical", "light")
    win = FramedWindow()
    win.resize(400, 300)
    win.show()
    app.processEvents()
    img = win.grab().toImage()
    assert img.pixelColor(0, 0).alpha() == 0            # beyond the radius
    assert img.pixelColor(1, 1).alpha() == 0
    edge = img.pixelColor(0, 150)
    band = img.pixelColor(3, 150)
    inside = img.pixelColor(GRIP + 40, 150)
    assert edge.alpha() == 255 and band.alpha() == 255 and inside.alpha() == 255
    assert band.name() == t.vars["bg"] and inside.name() == t.vars["bg"]
    assert edge.name() != t.vars["bg"]           # the border, not the background
    assert img.pixelColor(200, 0).alpha() == 255  # the top edge is painted, edge to edge
    win.close()


def test_netrunner_inks_the_bar_in_fill_text(app):
    t = apply_theme(app, "netrunner", "red")
    assert t.vars["titlebar_ink"] == t.vars["fill_text"]
    win = FramedWindow()
    win.setWindowTitle("x")
    assert not win.titlebar.close_btn.icon().isNull()
    t2 = apply_theme(app, "classical", "light")
    assert t2.vars["titlebar_ink"] == t2.vars["text"]
